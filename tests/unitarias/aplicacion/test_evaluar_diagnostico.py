from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.dominio.entidades.diagnostico import (Diagnostico, Recomendacion,
                                               Respuesta)
from src.dominio.entidades.modelo_madurez import (Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)
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
                dimension_codigo="innovacion",
                titulo="Título",
                contenido="Contenido",
                prioridad=1,
            )
        ],
    )


@pytest.mark.asyncio
async def test_evaluar_diagnostico_exitoso_marca_evaluado_y_persiste_resultado():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.return_value = crear_respuesta_agente_valida()

    caso_uso = EvaluarDiagnostico(repo_diagnostico, repo_modelo, cliente_agente)
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "evaluado"
    assert diagnostico.evaluado_en is not None
    assert diagnostico.resultado is not None
    assert diagnostico.resultado.sintesis == "Síntesis"
    assert diagnostico.resultado.indice_global == Decimal("8")
    assert len(diagnostico.recomendaciones) == 1
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)


@pytest.mark.asyncio
async def test_evaluar_diagnostico_falla_del_agente_marca_fallido():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
    cliente_agente = AsyncMock()
    cliente_agente.evaluar.side_effect = ServicioAgenteError(
        "El servicio del agente respondió 502"
    )

    caso_uso = EvaluarDiagnostico(repo_diagnostico, repo_modelo, cliente_agente)
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "fallido"
    assert "502" in diagnostico.motivo_fallo
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)


@pytest.mark.asyncio
async def test_evaluar_diagnostico_sin_version_de_modelo_marca_fallido():
    diagnostico = crear_diagnostico_prueba()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = None
    cliente_agente = AsyncMock()

    caso_uso = EvaluarDiagnostico(repo_diagnostico, repo_modelo, cliente_agente)
    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "fallido"
    cliente_agente.evaluar.assert_not_called()
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)


@pytest.mark.asyncio
async def test_evaluar_diagnostico_inexistente_no_hace_nada():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None
    repo_modelo = AsyncMock()
    cliente_agente = AsyncMock()

    caso_uso = EvaluarDiagnostico(repo_diagnostico, repo_modelo, cliente_agente)
    await caso_uso.ejecutar("diag-inexistente")

    repo_modelo.obtener_por_version.assert_not_called()
    repo_diagnostico.actualizar.assert_not_called()
