from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.aplicacion.casos_uso.reprocesar_diagnostico import (
    ReprocesarDiagnostico, ReprocesarPendientes)
from src.dominio.entidades.diagnostico import Diagnostico, Recomendacion
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario
from src.dominio.puertos.cliente_servicio_agente import ServicioAgenteError
from tests.unitarias.aplicacion.test_evaluar_diagnostico import (
    crear_diagnostico_prueba, crear_mocks_notificacion, crear_modelo_prueba,
    crear_respuesta_agente_valida)


def diagnostico_fallido(empresa_id="emp-1") -> Diagnostico:
    diagnostico = crear_diagnostico_prueba()
    diagnostico.empresa_id = empresa_id
    diagnostico.marcar_fallido("El servicio no respondió")
    return diagnostico


def usuario(rol: str, empresa_asignada: str | None = None) -> Usuario:
    u = Usuario(
        id=f"{rol}-1",
        correo=f"{rol}@trust4p.com",
        clave_hash="hash",
        nombres="N",
        apellidos="A",
        rol=Rol(codigo=rol),
    )
    if empresa_asignada:
        u.asignaciones = [Asignacion(empresa_id=empresa_asignada)]
    return u


# --- entidad -----------------------------------------------------------------


def test_un_diagnostico_fallido_se_reabre_para_reprocesarse():
    diagnostico = diagnostico_fallido()
    diagnostico.reabrir_para_reproceso()
    assert diagnostico.estado == "completado"
    assert diagnostico.motivo_fallo is None


@pytest.mark.parametrize("estado", ["borrador", "completado", "evaluado", "cerrado"])
def test_solo_un_diagnostico_fallido_se_reabre(estado):
    diagnostico = crear_diagnostico_prueba()
    diagnostico.estado = estado
    with pytest.raises(ValueError):
        diagnostico.reabrir_para_reproceso()
    assert diagnostico.estado == estado


@pytest.mark.asyncio
async def test_el_reproceso_conserva_las_recomendaciones_del_consultor():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.marcar_fallido("caído")
    diagnostico.recomendaciones = [
        Recomendacion(
            origen="consultor",
            dimension_codigo=None,
            titulo="Del consultor",
            contenido="Registrada mientras estaba fallido",
            prioridad=1,
            autor_id="consultor-1",
        )
    ]
    diagnostico.reabrir_para_reproceso()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.return_value = crear_respuesta_agente_valida()
    repo_usuario, correo, notificaciones = crear_mocks_notificacion()

    await EvaluarDiagnostico(
        repo_diagnostico, repo_modelo, cliente_agente, repo_usuario, correo, notificaciones
    ).ejecutar("diag-1")

    assert diagnostico.estado == "evaluado"
    assert [r.origen for r in diagnostico.recomendaciones] == ["consultor", "agente"]


# --- reproceso individual --------------------------------------------------


@pytest.mark.asyncio
async def test_el_administrador_reprocesa_el_diagnostico_de_cualquier_empresa():
    diagnostico = diagnostico_fallido()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario("administrador")

    resultado = await ReprocesarDiagnostico(repo_diagnostico, repo_usuario).ejecutar(
        "administrador-1", "diag-1"
    )

    assert resultado.estado == "completado"
    # C7: se guarda solo si en la base sigue 'fallido'
    repo_diagnostico.actualizar_si_estado.assert_called_once_with(diagnostico, "fallido")


@pytest.mark.asyncio
async def test_el_consultor_reprocesa_solo_empresas_asignadas():
    diagnostico = diagnostico_fallido("emp-1")
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()

    repo_usuario.obtener_por_id.return_value = usuario("consultor", "emp-1")
    resultado = await ReprocesarDiagnostico(repo_diagnostico, repo_usuario).ejecutar(
        "consultor-1", "diag-1"
    )
    assert resultado.estado == "completado"

    diagnostico_ajeno = diagnostico_fallido("emp-2")
    repo_diagnostico.obtener_por_id.return_value = diagnostico_ajeno
    with pytest.raises(AccesoNoAutorizado):
        await ReprocesarDiagnostico(repo_diagnostico, repo_usuario).ejecutar(
            "consultor-1", "diag-2"
        )
    assert diagnostico_ajeno.estado == "fallido"


@pytest.mark.asyncio
async def test_no_se_reprocesa_un_diagnostico_que_no_esta_fallido():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario("administrador")

    with pytest.raises(ValueError):
        await ReprocesarDiagnostico(repo_diagnostico, repo_usuario).ejecutar(
            "administrador-1", "diag-1"
        )
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_reprocesar_un_diagnostico_inexistente_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    with pytest.raises(DiagnosticoNoEncontrado):
        await ReprocesarDiagnostico(repo_diagnostico, AsyncMock()).ejecutar("a", "x")


# --- reproceso diferido (todos los pendientes) -------------------------------


@pytest.mark.asyncio
async def test_reprocesar_pendientes_reabre_todos_los_fallidos_en_orden():
    a, b = diagnostico_fallido(), diagnostico_fallido()
    a.id, b.id = "diag-a", "diag-b"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_estado.return_value = [a, b]

    ids = await ReprocesarPendientes(repo_diagnostico).ejecutar()

    assert ids == ["diag-a", "diag-b"]
    repo_diagnostico.listar_por_estado.assert_called_once_with("fallido")
    assert a.estado == b.estado == "completado"
    assert repo_diagnostico.actualizar_si_estado.await_count == 2


@pytest.mark.asyncio
async def test_reprocesar_pendientes_sin_fallidos_no_hace_nada():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_estado.return_value = []
    assert await ReprocesarPendientes(repo_diagnostico).ejecutar() == []
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_evaluar_en_serie_no_notifica_cada_fallo_ni_se_detiene():
    d1, d2 = crear_diagnostico_prueba(), crear_diagnostico_prueba()
    d1.id, d2.id = "diag-1", "diag-2"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.side_effect = lambda i: {"diag-1": d1, "diag-2": d2}[i]
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.side_effect = ServicioAgenteError("cortocircuito abierto")
    repo_usuario, correo, notificaciones = crear_mocks_notificacion()

    caso_uso = EvaluarDiagnostico(
        repo_diagnostico, repo_modelo, cliente_agente, repo_usuario, correo, notificaciones
    )
    await caso_uso.ejecutar_en_serie(["diag-1", "diag-2"])

    assert d1.estado == d2.estado == "fallido"
    assert cliente_agente.evaluar.await_count == 2
    correo.enviar.assert_not_called()


@pytest.mark.asyncio
async def test_evaluar_en_serie_continua_si_una_evaluacion_lanza_una_excepcion():
    d2 = crear_diagnostico_prueba()
    d2.id = "diag-2"
    repo_diagnostico = AsyncMock()

    async def obtener(i):
        if i == "diag-1":
            raise RuntimeError("base de datos")
        return d2

    repo_diagnostico.obtener_por_id.side_effect = obtener
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.return_value = crear_respuesta_agente_valida()
    repo_usuario, correo, notificaciones = crear_mocks_notificacion()

    await EvaluarDiagnostico(
        repo_diagnostico, repo_modelo, cliente_agente, repo_usuario, correo, notificaciones
    ).ejecutar_en_serie(["diag-1", "diag-2"])

    assert d2.estado == "evaluado"


# --- C7: duplicados y evaluaciones interrumpidas ------------------------------


@pytest.mark.asyncio
async def test_si_otra_peticion_ya_lo_reabrio_el_reproceso_se_rechaza():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico_fallido()
    repo_diagnostico.actualizar_si_estado.return_value = False
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario("administrador")

    with pytest.raises(ValueError, match="ya se está reprocesando"):
        await ReprocesarDiagnostico(repo_diagnostico, repo_usuario).ejecutar("a", "d")


@pytest.mark.asyncio
async def test_reprocesar_pendientes_omite_los_que_otro_ya_reabrio():
    a, b = diagnostico_fallido(), diagnostico_fallido()
    a.id, b.id = "diag-a", "diag-b"
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_estado.return_value = [a, b]
    repo_diagnostico.actualizar_si_estado.side_effect = [True, False]

    assert await ReprocesarPendientes(repo_diagnostico).ejecutar() == ["diag-a"]


@pytest.mark.asyncio
async def test_reprocesar_pendientes_recupera_antes_las_interrumpidas():
    orden = []
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_estado.side_effect = lambda e: orden.append("listar") or []
    recuperar = AsyncMock()
    recuperar.ejecutar.side_effect = lambda: orden.append("recuperar") or []

    await ReprocesarPendientes(repo_diagnostico, recuperar).ejecutar()

    assert orden == ["recuperar", "listar"]
