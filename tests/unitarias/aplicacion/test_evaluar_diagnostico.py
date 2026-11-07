from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.dominio.entidades.diagnostico import (Diagnostico, Recomendacion,
                                               Respuesta)
from src.dominio.entidades.modelo_madurez import (Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)
from src.dominio.entidades.usuario import Rol, Usuario
from src.dominio.puertos.cliente_servicio_agente import (RespuestaAgente,
                                                         ServicioAgenteError)


def crear_modelo_prueba() -> ModeloMadurez:
    modelo = ModeloMadurez(
        id="m1", version="1", nombre="Modelo", escala_min=1, escala_max=10
    )
    modelo.dimensiones = [
        Dimension(codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1)
    ]
    modelo.preguntas = [
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Qué tanto invierte su empresa en innovación?",
            tipo="seleccion_unica",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
            opciones=[
                OpcionPregunta(codigo="alta", etiqueta="Alta", valor=Decimal("8"))
            ],
        )
    ]
    modelo.niveles = [
        Nivel(
            nivel=1,
            nombre="Único",
            descripcion="Cubre toda la escala",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("10"),
        )
    ]
    return modelo


def crear_diagnostico_prueba() -> Diagnostico:
    return Diagnostico(
        id="diag-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=1,
        estado="completado",
        respuestas=[
            Respuesta(
                pregunta_codigo="p1",
                dimension_codigo="innovacion",
                opciones_codigo=["alta"],
            )
        ],
    )


def crear_respuesta_agente_valida() -> RespuestaAgente:
    return RespuestaAgente(
        perfil_cultura_descripcion="Descripción del perfil",
        dimensiones_observaciones={"innovacion": "Observación"},
        lienzo_negocio={"segmentos_clientes": "..."},
        sintesis="Síntesis",
        recomendaciones=[
            Recomendacion(
                origen="agente",
                dimension_codigo="innovacion",
                titulo="Título",
                contenido="Contenido",
                prioridad=1,
            )
        ],
    )


def crear_mocks_notificacion():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id="emp-1",
    )
    repo_usuario.listar_por_rol.return_value = [
        Usuario(
            id="admin-1",
            correo="admin@trust4p.com",
            clave_hash="hash",
            nombres="Admin",
            apellidos="Trust4P",
            rol=Rol(codigo="administrador"),
        )
    ]
    servicio_correo = AsyncMock()
    repo_notificacion = AsyncMock()
    return repo_usuario, servicio_correo, repo_notificacion


@pytest.mark.asyncio
async def test_evaluar_diagnostico_exitoso_marca_evaluado_y_persiste_resultado():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.return_value = crear_respuesta_agente_valida()
    repo_usuario, servicio_correo, repo_notificacion = crear_mocks_notificacion()

    caso_uso = EvaluarDiagnostico(
        repo_diagnostico,
        repo_modelo,
        cliente_agente,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
    )
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "evaluado"
    assert diagnostico.evaluado_en is not None
    assert diagnostico.resultado is not None
    assert diagnostico.resultado.sintesis == "Síntesis"
    assert diagnostico.resultado.indice_global == Decimal("8")
    assert len(diagnostico.recomendaciones) == 1
    # ASR-02: se persiste dos veces — resultado determinístico primero,
    # luego el resultado evaluado con el contenido narrativo.
    assert repo_diagnostico.actualizar.call_count == 2
    # RF-45: se notifica al representante de que ya hay resultado.
    servicio_correo.enviar.assert_called_once()
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"] == "ana@innovatech.com"
    )
    notificacion = repo_notificacion.registrar.call_args[0][0]
    assert notificacion.tipo == "diagnostico_evaluado"


@pytest.mark.asyncio
async def test_evaluar_diagnostico_falla_del_agente_marca_fallido_pero_conserva_resultado():
    """ASR-02: aunque el agente falle, el índice ya calculado debe quedar
    persistido y consultable — solo falta la interpretación narrativa."""
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.side_effect = ServicioAgenteError(
        "El servicio del agente respondió 502"
    )
    repo_usuario, servicio_correo, repo_notificacion = crear_mocks_notificacion()

    caso_uso = EvaluarDiagnostico(
        repo_diagnostico,
        repo_modelo,
        cliente_agente,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
    )
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "fallido"
    assert "502" in diagnostico.motivo_fallo
    assert diagnostico.resultado is not None
    assert diagnostico.resultado.indice_global == Decimal("8")
    assert diagnostico.resultado.sintesis is None
    assert repo_diagnostico.actualizar.call_count == 2
    # RF-38: se notifica al administrador, no al representante.
    repo_usuario.listar_por_rol.assert_called_once_with("administrador")
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"] == "admin@trust4p.com"
    )


@pytest.mark.asyncio
async def test_evaluar_diagnostico_con_indice_fuera_de_rubrica_marca_fallido():
    """Hallazgo en prueba manual end-to-end: una rúbrica que no cubre el
    índice calculado (por configuración incompleta del modelo, o por una
    respuesta numérica fuera de la escala) no debe colgar el diagnóstico en
    'completado' para siempre — debe quedar 'fallido' con el motivo."""
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    modelo = crear_modelo_prueba()
    modelo.niveles = [
        Nivel(
            nivel=1,
            nombre="Único",
            descripcion="No cubre el índice resultante",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("4"),
        )
    ]
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo
    cliente_agente = AsyncMock()
    repo_usuario, servicio_correo, repo_notificacion = crear_mocks_notificacion()

    caso_uso = EvaluarDiagnostico(
        repo_diagnostico,
        repo_modelo,
        cliente_agente,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
    )
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "fallido"
    assert "índice calculado" in diagnostico.motivo_fallo
    assert diagnostico.resultado is None
    cliente_agente.evaluar.assert_not_called()
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)
    servicio_correo.enviar.assert_called_once()


@pytest.mark.asyncio
async def test_evaluar_diagnostico_sin_version_de_modelo_marca_fallido():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = None
    cliente_agente = AsyncMock()
    repo_usuario, servicio_correo, repo_notificacion = crear_mocks_notificacion()

    caso_uso = EvaluarDiagnostico(
        repo_diagnostico,
        repo_modelo,
        cliente_agente,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
    )
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "fallido"
    cliente_agente.evaluar.assert_not_called()
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)
    servicio_correo.enviar.assert_called_once()


@pytest.mark.asyncio
async def test_evaluar_diagnostico_inexistente_no_hace_nada():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    repo_modelo = AsyncMock()
    cliente_agente = AsyncMock()
    repo_usuario, servicio_correo, repo_notificacion = crear_mocks_notificacion()

    caso_uso = EvaluarDiagnostico(
        repo_diagnostico,
        repo_modelo,
        cliente_agente,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
    )
    await caso_uso.ejecutar("diag-inexistente")

    repo_modelo.obtener_por_version.assert_not_called()
    repo_diagnostico.actualizar.assert_not_called()
    servicio_correo.enviar.assert_not_called()


# --- C7: una sola evaluación a la vez y recuperación tras interrupción --------


def _caso_uso(repo_diagnostico, cliente_agente=None):
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    if cliente_agente is None:
        cliente_agente = AsyncMock()
        cliente_agente.evaluar.return_value = crear_respuesta_agente_valida()
    repo_usuario, servicio_correo, repo_notificacion = crear_mocks_notificacion()
    return EvaluarDiagnostico(
        repo_diagnostico, repo_modelo, cliente_agente, repo_usuario, servicio_correo, repo_notificacion
    )


@pytest.mark.asyncio
async def test_si_otra_evaluacion_lo_tiene_reclamado_no_se_evalua_de_nuevo():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.reclamar_evaluacion.return_value = False
    cliente_agente = AsyncMock()

    await _caso_uso(repo_diagnostico, cliente_agente).ejecutar("diag-1")

    cliente_agente.evaluar.assert_not_called()
    repo_diagnostico.actualizar.assert_not_called()
    repo_diagnostico.liberar_evaluacion.assert_not_called()


@pytest.mark.asyncio
async def test_la_marca_de_evaluacion_se_libera_aunque_la_evaluacion_falle():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.reclamar_evaluacion.return_value = True
    repo_diagnostico.obtener_por_id.side_effect = RuntimeError("caída de la base")

    with pytest.raises(RuntimeError):
        await _caso_uso(repo_diagnostico).ejecutar("diag-1")

    token = repo_diagnostico.reclamar_evaluacion.call_args.args[1]
    repo_diagnostico.liberar_evaluacion.assert_awaited_once_with("diag-1", token)


@pytest.mark.asyncio
async def test_recuperar_interrumpidas_usa_el_plazo_y_el_motivo():
    from datetime import datetime, timedelta, timezone

    from src.aplicacion.casos_uso.evaluar_diagnostico import (
        MOTIVO_INTERRUMPIDA, RecuperarEvaluacionesInterrumpidas)

    repo_diagnostico = AsyncMock()
    repo_diagnostico.marcar_evaluaciones_interrumpidas.return_value = ["diag-9"]

    ids = await RecuperarEvaluacionesInterrumpidas(
        repo_diagnostico, timedelta(minutes=10)
    ).ejecutar()

    assert ids == ["diag-9"]
    limite, motivo = repo_diagnostico.marcar_evaluaciones_interrumpidas.call_args.args
    esperado = datetime.now(timezone.utc) - timedelta(minutes=10)
    assert abs((limite - esperado).total_seconds()) < 5
    assert motivo == MOTIVO_INTERRUMPIDA
