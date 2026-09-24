from decimal import Decimal

import pytest

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, ModeloMadurez,
                                                  OpcionPregunta, Pregunta)
from src.infraestructura.persistencia.repositorio_mongo_modelo_madurez import \
    RepositorioMongoModeloMadurez


def crear_modelo_prueba() -> ModeloMadurez:
    return ModeloMadurez(
        id=None,
        version="v-integracion-1",
        nombre="Modelo de prueba de integración",
        dimensiones=[
            Dimension(
                codigo="innovacion", nombre="Innovación", peso=Decimal("0.5"), orden=1
            ),
            Dimension(codigo="cultura", nombre="Cultura", peso=Decimal("0.5"), orden=2),
        ],
        preguntas=[
            Pregunta(
                codigo="p1",
                dimension_codigo="innovacion",
                enunciado="¿Su empresa invierte en I+D?",
                tipo="escala",
                obligatoria=True,
                peso=Decimal("1"),
                en_demo=False,
                orden=1,
                opciones=[
                    OpcionPregunta(codigo="alta", etiqueta="Alta", valor=Decimal("3")),
                    OpcionPregunta(codigo="baja", etiqueta="Baja", valor=Decimal("1")),
                ],
            ),
            Pregunta(
                codigo="p2",
                dimension_codigo="cultura",
                enunciado="¿Fomenta la experimentación?",
                tipo="seleccion_unica",
                obligatoria=True,
                peso=Decimal("1"),
                en_demo=False,
                orden=1,
                condicion=CondicionActivacion(
                    pregunta_codigo="p1", operador="igual", valor="alta"
                ),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_guardar_y_obtener_por_id_conserva_precision_decimal(db):
    repo = RepositorioMongoModeloMadurez(db)
    modelo = await repo.guardar(crear_modelo_prueba())

    recuperado = await repo.obtener_por_id(modelo.id)

    assert recuperado is not None
    assert recuperado.version == "v-integracion-1"
    assert len(recuperado.dimensiones) == 2
    assert recuperado.dimensiones[0].peso == Decimal("0.5")
    assert recuperado.preguntas[0].opciones[0].valor == Decimal("3")
    assert recuperado.preguntas[1].condicion.pregunta_codigo == "p1"


@pytest.mark.asyncio
async def test_obtener_por_version(db):
    repo = RepositorioMongoModeloMadurez(db)
    await repo.guardar(crear_modelo_prueba())

    recuperado = await repo.obtener_por_version("v-integracion-1")

    assert recuperado is not None
    assert recuperado.nombre == "Modelo de prueba de integración"


@pytest.mark.asyncio
async def test_obtener_por_version_inexistente_devuelve_none(db):
    repo = RepositorioMongoModeloMadurez(db)

    assert await repo.obtener_por_version("no-existe") is None


@pytest.mark.asyncio
async def test_actualizar_persiste_cambios(db):
    repo = RepositorioMongoModeloMadurez(db)
    modelo = await repo.guardar(crear_modelo_prueba())

    modelo.publicado = True
    await repo.actualizar(modelo)

    recuperado = await repo.obtener_por_id(modelo.id)
    assert recuperado.publicado is True


@pytest.mark.asyncio
async def test_listar_incluye_modelos_guardados(db):
    repo = RepositorioMongoModeloMadurez(db)
    await repo.guardar(crear_modelo_prueba())

    modelos = await repo.listar()

    assert any(m.version == "v-integracion-1" for m in modelos)


@pytest.mark.asyncio
async def test_obtener_por_id_con_formato_invalido_devuelve_none(db):
    """RNF-07: un id con formato inválido no debe propagar bson.errors.InvalidId."""
    repo = RepositorioMongoModeloMadurez(db)

    assert await repo.obtener_por_id("esto-no-es-un-object-id") is None


@pytest.mark.asyncio
async def test_obtener_por_id_inexistente_pero_valido_devuelve_none(db):
    repo = RepositorioMongoModeloMadurez(db)

    assert await repo.obtener_por_id("64b64b64b64b64b64b64b64b") is None
