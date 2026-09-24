from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarDimension, AgregarNivel, AgregarPregunta, ConsultarModelo,
    CrearModeloMadurez, EditarDimension, EditarNivel, EditarPregunta,
    ListarModelos, ModeloNoEncontrado, QuitarDimension, QuitarNivel,
    QuitarPregunta, VersionDuplicada)
from src.dominio.entidades.modelo_madurez import (Dimension, ModeloMadurez,
                                                  Nivel, Pregunta)


def crear_modelo_prueba() -> ModeloMadurez:
    return ModeloMadurez(id="modelo-1", version="v1", nombre="Modelo inicial")


def crear_modelo_con_dimension() -> ModeloMadurez:
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(
        Dimension(codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1)
    )
    return modelo


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


@pytest.mark.asyncio
async def test_agregar_pregunta():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_con_dimension()

    caso_uso = AgregarPregunta(repo)
    modelo = await caso_uso.ejecutar(
        "modelo-1",
        codigo="p1",
        dimension_codigo="innovacion",
        enunciado="¿Invierte en I+D?",
        tipo="escala",
        obligatoria=True,
        peso=Decimal("1"),
        en_demo=False,
        orden=1,
    )

    assert len(modelo.preguntas) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_pregunta_a_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = AgregarPregunta(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar(
            "no-existe",
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )


@pytest.mark.asyncio
async def test_editar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = EditarPregunta(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "p1", peso=Decimal("0.5"))

    assert resultado.preguntas[0].peso == Decimal("0.5")
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_quitar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = QuitarPregunta(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "p1")

    assert resultado.preguntas == []
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_nivel():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_prueba()

    caso_uso = AgregarNivel(repo)
    modelo = await caso_uso.ejecutar(
        "modelo-1",
        nivel=1,
        nombre="Inicial",
        descripcion="Sin proceso formal",
        umbral_min=Decimal("1"),
        umbral_max=Decimal("5"),
    )

    assert len(modelo.niveles) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_nivel_a_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = AgregarNivel(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar(
            "no-existe",
            nivel=1,
            nombre="Inicial",
            descripcion="Sin proceso formal",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("5"),
        )


@pytest.mark.asyncio
async def test_editar_nivel():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(
        Nivel(
            nivel=1,
            nombre="Inicial",
            descripcion="Sin proceso formal",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("5"),
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = EditarNivel(repo)
    resultado = await caso_uso.ejecutar("modelo-1", 1, umbral_max=Decimal("6"))

    assert resultado.niveles[0].umbral_max == Decimal("6")
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_quitar_nivel():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(
        Nivel(
            nivel=1,
            nombre="Inicial",
            descripcion="Sin proceso formal",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("5"),
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = QuitarNivel(repo)
    resultado = await caso_uso.ejecutar("modelo-1", 1)

    assert resultado.niveles == []
    repo.actualizar.assert_called_once()
