from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarDimension, ConsultarModelo, CrearModeloMadurez, EditarDimension,
    ListarModelos, ModeloNoEncontrado, QuitarDimension, VersionDuplicada)
from src.dominio.entidades.modelo_madurez import Dimension, ModeloMadurez


def crear_modelo_prueba() -> ModeloMadurez:
    return ModeloMadurez(id="modelo-1", version="v1", nombre="Modelo inicial")


@pytest.mark.asyncio
async def test_crear_modelo_madurez():
    repo = AsyncMock()
    repo.obtener_por_version.return_value = None
    repo.guardar.side_effect = lambda m: m

    caso_uso = CrearModeloMadurez(repo)
    modelo = await caso_uso.ejecutar(version="v1", nombre="Modelo inicial")

    assert modelo.version == "v1"
    repo.guardar.assert_called_once()


@pytest.mark.asyncio
async def test_crear_modelo_con_version_duplicada_falla():
    repo = AsyncMock()
    repo.obtener_por_version.return_value = crear_modelo_prueba()

    caso_uso = CrearModeloMadurez(repo)
    with pytest.raises(VersionDuplicada):
        await caso_uso.ejecutar(version="v1", nombre="Modelo inicial")
    repo.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_listar_modelos():
    repo = AsyncMock()
    repo.listar.return_value = [crear_modelo_prueba()]

    caso_uso = ListarModelos(repo)
    modelos = await caso_uso.ejecutar()

    assert len(modelos) == 1


@pytest.mark.asyncio
async def test_consultar_modelo_existente():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_prueba()

    caso_uso = ConsultarModelo(repo)
    modelo = await caso_uso.ejecutar("modelo-1")

    assert modelo.id == "modelo-1"


@pytest.mark.asyncio
async def test_consultar_modelo_inexistente_lanza_excepcion():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = ConsultarModelo(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar("no-existe")


@pytest.mark.asyncio
async def test_agregar_dimension():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_prueba()

    caso_uso = AgregarDimension(repo)
    modelo = await caso_uso.ejecutar(
        "modelo-1", codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1
    )

    assert len(modelo.dimensiones) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_dimension_a_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = AgregarDimension(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar(
            "no-existe",
            codigo="innovacion",
            nombre="Innovación",
            peso=Decimal("1"),
            orden=1,
        )


@pytest.mark.asyncio
async def test_editar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(
        Dimension(
            codigo="innovacion", nombre="Innovación", peso=Decimal("0.5"), orden=1
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = EditarDimension(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "innovacion", peso=Decimal("0.8"))

    assert resultado.dimensiones[0].peso == Decimal("0.8")
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_quitar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(
        Dimension(codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1)
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = QuitarDimension(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "innovacion")

    assert resultado.dimensiones == []
    repo.actualizar.assert_called_once()
