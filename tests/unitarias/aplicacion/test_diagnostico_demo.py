from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.diagnostico_demo import (
    CalcularResultadoDemo, DemostracionNoDisponible, ObtenerPreguntasDemo)
from src.aplicacion.casos_uso.gestionar_diagnostico import NoHayVersionVigente
from src.dominio.servicios.diagnostico_demo import RespuestaDemo
from tests.unitarias.dominio.test_diagnostico_demo import crear_modelo


def repo(modelo):
    mock = AsyncMock()
    mock.obtener_vigente.return_value = modelo
    return mock


@pytest.mark.asyncio
async def test_obtiene_preguntas_del_modelo_vigente():
    version, preguntas = await ObtenerPreguntasDemo(repo(crear_modelo())).ejecutar()

    assert version == "1"
    assert [p.codigo for p in preguntas] == ["pa", "pb", "pd"]


@pytest.mark.asyncio
async def test_sin_modelo_vigente():
    with pytest.raises(NoHayVersionVigente):
        await ObtenerPreguntasDemo(repo(None)).ejecutar()
    with pytest.raises(NoHayVersionVigente):
        await CalcularResultadoDemo(repo(None)).ejecutar([])


@pytest.mark.asyncio
async def test_sin_preguntas_marcadas_en_demo():
    modelo = crear_modelo()
    for p in modelo.preguntas:
        p.en_demo = False

    with pytest.raises(DemostracionNoDisponible):
        await ObtenerPreguntasDemo(repo(modelo)).ejecutar()
    with pytest.raises(DemostracionNoDisponible):
        await CalcularResultadoDemo(repo(modelo)).ejecutar([])


@pytest.mark.asyncio
async def test_calcula_sin_escribir_en_el_repositorio():
    """HU-007 CA-02: el caso de uso solo lee el modelo; no persiste nada."""
    mock = repo(crear_modelo())

    resultado = await CalcularResultadoDemo(mock).ejecutar(
        [
            RespuestaDemo("pa", [], valor=Decimal("8")),
            RespuestaDemo("pb", ["baja"]),
        ]
    )

    assert resultado.nivel == 2
    assert {m[0] for m in mock.method_calls} == {"obtener_vigente"}
