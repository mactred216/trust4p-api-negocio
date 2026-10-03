from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_modelo_madurez import \
    ModeloNoEncontrado
from src.aplicacion.casos_uso.simular_pesos import (SimularPesosModelo,
                                                    SinDiagnosticosParaSimular)
from tests.unitarias.dominio.test_simulacion_pesos import (crear_diagnostico,
                                                           crear_modelo)

PESOS = {"A": Decimal("0.9"), "B": Decimal("0.1")}


def armar(diagnosticos, modelo="por_defecto"):
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_id.return_value = (
        crear_modelo() if modelo == "por_defecto" else modelo
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_modelo_version.return_value = diagnosticos
    return SimularPesosModelo(repo_modelo, repo_diagnostico), repo_diagnostico


def diagnostico_n(n, estado="evaluado"):
    d = crear_diagnostico()
    d.id = f"d-{n}"
    d.consecutivo = n
    d.estado = estado
    return d


@pytest.mark.asyncio
async def test_simula_todos_los_historicos_de_la_version():
    caso_uso, repo = armar([diagnostico_n(1), diagnostico_n(2, "cerrado")])

    resultado = await caso_uso.ejecutar("m-1", PESOS)

    repo.listar_por_modelo_version.assert_called_once_with("1")
    assert resultado.total == 2
    assert resultado.con_cambio_de_nivel == 2
    assert resultado.variacion_promedio == Decimal("2.40")


@pytest.mark.asyncio
async def test_no_escribe_en_ningun_repositorio():
    """HU-035 CA-01: los resultados almacenados permanecen sin cambios."""
    diagnostico = diagnostico_n(1)
    caso_uso, repo = armar([diagnostico])

    await caso_uso.ejecutar("m-1", PESOS)

    repo.actualizar.assert_not_called()
    repo.guardar.assert_not_called()
    assert diagnostico.resultado.indice_global == Decimal("5")


@pytest.mark.asyncio
async def test_ignora_diagnosticos_sin_resultado_o_en_borrador():
    borrador = diagnostico_n(2, "borrador")
    borrador.resultado = None
    caso_uso, _ = armar([diagnostico_n(1), borrador])

    assert (await caso_uso.ejecutar("m-1", PESOS)).total == 1


@pytest.mark.asyncio
async def test_sin_historicos_falla():
    caso_uso, _ = armar([])

    with pytest.raises(SinDiagnosticosParaSimular):
        await caso_uso.ejecutar("m-1", PESOS)


@pytest.mark.asyncio
async def test_modelo_inexistente():
    caso_uso, _ = armar([diagnostico_n(1)], modelo=None)

    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar("m-x", PESOS)


@pytest.mark.asyncio
async def test_pesos_invalidos_se_rechazan_antes_de_leer_diagnosticos():
    caso_uso, repo = armar([diagnostico_n(1)])

    with pytest.raises(ValueError):
        await caso_uso.ejecutar("m-1", {"A": Decimal("0.7"), "B": Decimal("0.7")})
    repo.listar_por_modelo_version.assert_not_called()


@pytest.mark.asyncio
async def test_seleccion_de_diagnosticos_por_id():
    caso_uso, _ = armar([diagnostico_n(1), diagnostico_n(2)])

    resultado = await caso_uso.ejecutar("m-1", PESOS, diagnostico_ids=["d-2"])

    assert [c.diagnostico_id for c in resultado.comparaciones] == ["d-2"]


@pytest.mark.asyncio
async def test_id_ajeno_a_la_version_se_rechaza():
    caso_uso, _ = armar([diagnostico_n(1)])

    with pytest.raises(ValueError, match="d-otro"):
        await caso_uso.ejecutar("m-1", PESOS, diagnostico_ids=["d-1", "d-otro"])


@pytest.mark.asyncio
async def test_diagnostico_fuera_de_rubrica_queda_como_no_simulable():
    fuera = diagnostico_n(2)
    fuera.respuestas[0].valor = Decimal("50000")
    caso_uso, _ = armar([diagnostico_n(1), fuera])

    resultado = await caso_uso.ejecutar("m-1", PESOS)

    assert resultado.total == 1
    assert [n.diagnostico_id for n in resultado.no_simulables] == ["d-2"]
