from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_consultoria import (
    AvanzarNivel, EditarTarea, RegistrarRecomendacion, TareaNoEncontrada)
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               Recomendacion,
                                               ResultadoDiagnostico)
from src.dominio.entidades.modelo_madurez import ModeloMadurez, Nivel
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario

# El consultor asignado gestiona las tareas del plan de mejora de la empresa.


def consultor(empresas=("emp-1",)):
    return Usuario(
        id="c-1",
        correo="julia@x.com",
        clave_hash="h",
        nombres="Julia",
        apellidos="Herrera",
        rol=Rol(codigo="consultor"),
        asignaciones=[Asignacion(empresa_id=e) for e in empresas],
    )


def representante():
    return Usuario(
        id="u-1", correo="ana@innovatech.com", clave_hash="h", nombres="Ana",
        apellidos="Pérez", rol=Rol(codigo="representante"), empresa_id="emp-1",
    )


def modelo(niveles=10):
    m = ModeloMadurez(id="m", version="2026.2", nombre="M", escala_min=0, escala_max=100)
    m.niveles = [
        Nivel(nivel=i, nombre=f"Nivel {i}", descripcion="d", umbral_min=Decimal(i * 10 - 10), umbral_max=Decimal(i * 10))
        for i in range(1, niveles + 1)
    ]
    return m


def diagnostico(recomendaciones, nivel=3, estado="evaluado"):
    d = Diagnostico(
        id="d-1", empresa_id="emp-1", empresa_nombre="InnovaTech", usuario_id="u-1",
        modelo_version="2026.2", consecutivo=1, estado=estado,
    )
    d.resultado = ResultadoDiagnostico(
        indice_global=Decimal(nivel * 10 - 5), nivel=nivel, nivel_descripcion="x",
        dimensiones=[DimensionResultado(codigo="proposito", puntaje=Decimal("30"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    d.recomendaciones = recomendaciones
    return d


def tarea(titulo="T", estado="pendiente", nivel_objetivo=4):
    return Recomendacion(origen="consultor", titulo=titulo, contenido="c", estado=estado, nivel_objetivo=nivel_objetivo)


def entorno(d, usuario=None):
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.side_effect = lambda id_: {"c-1": usuario or consultor(), "u-1": representante()}.get(id_)
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = d
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo()
    return repo_usuario, repo_diagnostico, repo_modelo


# ---------- editar tarea ----------


@pytest.mark.asyncio
async def test_el_consultor_asignado_cambia_el_estado_y_se_guarda():
    t = tarea()
    d = diagnostico([t])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)

    cambio = await EditarTarea(repo_usuario, repo_diagnostico, repo_modelo).ejecutar(
        "c-1", "d-1", t.id, {"estado": "en_curso"}
    )

    assert t.estado == "en_curso"
    repo_diagnostico.actualizar.assert_awaited_once_with(d)
    assert cambio.antes["estado"] == "pendiente" and cambio.despues["estado"] == "en_curso"


@pytest.mark.asyncio
async def test_el_resumen_para_la_bitacora_incluye_fecha_y_nivel():
    t = tarea()
    d = diagnostico([t])
    cambio = await EditarTarea(*entorno(d)).ejecutar("c-1", "d-1", t.id, {"fecha_limite": date(2026, 12, 1), "nivel_objetivo": 6})

    assert cambio.antes["fecha_limite"] is None and cambio.despues["fecha_limite"] == "2026-12-01"
    assert cambio.antes["nivel_objetivo"] == 4 and cambio.despues["nivel_objetivo"] == 6


@pytest.mark.asyncio
async def test_valida_el_nivel_contra_la_rubrica_del_modelo_con_que_se_evaluo():
    t = tarea()
    d = diagnostico([t])

    with pytest.raises(ValueError, match="nivel máximo"):
        await EditarTarea(*entorno(d)).ejecutar("c-1", "d-1", t.id, {"nivel_objetivo": 11})


@pytest.mark.asyncio
async def test_un_consultor_sin_asignacion_vigente_no_puede():
    t = tarea()
    d = diagnostico([t])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d, consultor(empresas=("otra",)))

    with pytest.raises(AccesoNoAutorizado):
        await EditarTarea(repo_usuario, repo_diagnostico, repo_modelo).ejecutar("c-1", "d-1", t.id, {"estado": "completada"})

    assert t.estado == "pendiente"
    repo_diagnostico.actualizar.assert_not_awaited()


@pytest.mark.asyncio
async def test_si_la_asignacion_ya_finalizo_tampoco():
    t = tarea()
    d = diagnostico([t])
    c = consultor()
    c.finalizar_asignacion("emp-1")

    with pytest.raises(AccesoNoAutorizado):
        await EditarTarea(*entorno(d, c)).ejecutar("c-1", "d-1", t.id, {"estado": "completada"})


@pytest.mark.asyncio
async def test_diagnostico_o_tarea_inexistentes():
    d = diagnostico([tarea()])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)

    with pytest.raises(TareaNoEncontrada):
        await EditarTarea(repo_usuario, repo_diagnostico, repo_modelo).ejecutar("c-1", "d-1", "no-existe", {})

    repo_diagnostico.obtener_por_id.return_value = None
    with pytest.raises(DiagnosticoNoEncontrado):
        await EditarTarea(repo_usuario, repo_diagnostico, repo_modelo).ejecutar("c-1", "x", "y", {})


@pytest.mark.asyncio
async def test_si_la_edicion_es_invalida_no_se_guarda_nada():
    t = tarea()
    d = diagnostico([t])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)

    with pytest.raises(ValueError):
        await EditarTarea(repo_usuario, repo_diagnostico, repo_modelo).ejecutar("c-1", "d-1", t.id, {"estado": "inventado"})

    repo_diagnostico.actualizar.assert_not_awaited()


# ---------- registrar tarea nueva ----------


@pytest.mark.asyncio
async def test_registrar_una_tarea_con_fecha_y_nivel_valida_contra_la_rubrica():
    d = diagnostico([])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)
    caso = RegistrarRecomendacion(repo_usuario, repo_diagnostico, AsyncMock(), AsyncMock(), repo_modelo)

    r = await caso.ejecutar("c-1", "d-1", "Capacitar", "Detalle", fecha_limite=date(2026, 12, 1), nivel_objetivo=5)

    assert (r.fecha_limite, r.nivel_objetivo, r.estado) == (date(2026, 12, 1), 5, "pendiente")

    with pytest.raises(ValueError, match="nivel máximo"):
        await caso.ejecutar("c-1", "d-1", "T", "c", nivel_objetivo=11)


@pytest.mark.asyncio
async def test_una_tarea_nueva_sin_nivel_apunta_al_siguiente_de_la_empresa():
    d = diagnostico([], nivel=3)
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)
    caso = RegistrarRecomendacion(repo_usuario, repo_diagnostico, AsyncMock(), AsyncMock(), repo_modelo)

    r = await caso.ejecutar("c-1", "d-1", "T", "c")

    assert r.nivel_objetivo == 4


# ---------- avanzar de nivel ----------


@pytest.mark.asyncio
async def test_confirmar_el_nivel_guarda_el_avance_y_avisa_al_representante():
    d = diagnostico([tarea("A", "completada", 4)])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)
    correo, repo_notificacion = AsyncMock(), AsyncMock()

    diagnostico_resultante, avance, nivel_anterior = await AvanzarNivel(
        repo_usuario, repo_diagnostico, repo_modelo, correo, repo_notificacion
    ).ejecutar("c-1", "d-1")

    assert (nivel_anterior, avance.nivel, diagnostico_resultante.nivel_alcanzado) == (3, 4, 4)
    repo_diagnostico.actualizar.assert_awaited_once_with(d)
    correo.enviar.assert_awaited_once()
    enviado = correo.enviar.await_args.kwargs
    assert enviado["destinatario"] == "ana@innovatech.com"
    assert "nivel 4 (Nivel 4)" in enviado["cuerpo"]
    assert "Julia Herrera" in enviado["cuerpo"]
    assert repo_notificacion.registrar.await_args[0][0].tipo == "nivel_alcanzado"


@pytest.mark.asyncio
async def test_el_aviso_recomienda_un_nuevo_diagnostico_tras_dos_niveles():
    d = diagnostico([tarea("A", "completada", 4), tarea("B", "completada", 5)])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)
    correo = AsyncMock()
    caso = AvanzarNivel(repo_usuario, repo_diagnostico, repo_modelo, correo, AsyncMock())

    await caso.ejecutar("c-1", "d-1")
    assert "nuevo diagnóstico" not in correo.enviar.await_args.kwargs["cuerpo"]
    await caso.ejecutar("c-1", "d-1")

    assert "nuevo diagnóstico" in correo.enviar.await_args.kwargs["cuerpo"]


@pytest.mark.asyncio
async def test_si_faltan_tareas_no_avanza_ni_avisa():
    d = diagnostico([tarea("A", "en_curso", 4)])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)
    correo = AsyncMock()

    with pytest.raises(ValueError, match="Faltan 1 de 1"):
        await AvanzarNivel(repo_usuario, repo_diagnostico, repo_modelo, correo, AsyncMock()).ejecutar("c-1", "d-1")

    repo_diagnostico.actualizar.assert_not_awaited()
    correo.enviar.assert_not_awaited()
    assert d.nivel_alcanzado is None


@pytest.mark.asyncio
async def test_avanzar_exige_la_asignacion_vigente():
    d = diagnostico([tarea("A", "completada", 4)])
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d, consultor(empresas=("otra",)))

    with pytest.raises(AccesoNoAutorizado):
        await AvanzarNivel(repo_usuario, repo_diagnostico, repo_modelo, AsyncMock(), AsyncMock()).ejecutar("c-1", "d-1")


@pytest.mark.asyncio
async def test_no_pasa_del_nivel_maximo_de_la_rubrica_con_que_se_evaluo():
    d = diagnostico([tarea("A", "completada", 4)], nivel=3)
    repo_usuario, repo_diagnostico, repo_modelo = entorno(d)
    repo_modelo.obtener_por_version.return_value = modelo(niveles=3)

    with pytest.raises(ValueError, match="nivel máximo"):
        await AvanzarNivel(repo_usuario, repo_diagnostico, repo_modelo, AsyncMock(), AsyncMock()).ejecutar("c-1", "d-1")
