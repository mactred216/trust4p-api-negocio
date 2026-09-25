from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)
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
        niveles=[
            Nivel(
                nivel=1,
                nombre="Inicial",
                descripcion="Sin proceso formal",
                umbral_min=Decimal("1"),
                umbral_max=Decimal("5.5"),
            ),
            Nivel(
                nivel=2,
                nombre="Avanzado",
                descripcion="Proceso establecido",
                umbral_min=Decimal("5.5"),
                umbral_max=Decimal("10"),
            ),
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
                opciones=[
                    OpcionPregunta(codigo="si", etiqueta="Sí", valor=Decimal("1")),
                    OpcionPregunta(codigo="no", etiqueta="No", valor=Decimal("0")),
                ],
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
    assert len(recuperado.niveles) == 2
    assert recuperado.niveles[0].umbral_max == Decimal("5.5")


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


@pytest.mark.asyncio
async def test_obtener_vigente_devuelve_la_publicada_mas_reciente(db):
    """HU-034: obtener_vigente usa find_one(..., sort=...) — no probado antes
    de esta prueba contra Mongo real, solo contra mocks."""
    repo = RepositorioMongoModeloMadurez(db)

    antigua = crear_modelo_prueba()
    antigua.version = "v-vigente-1"
    antigua.publicar("admin-1")
    antigua.publicado_en = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await repo.guardar(antigua)

    reciente = crear_modelo_prueba()
    reciente.version = "v-vigente-2"
    reciente.publicar("admin-1")
    reciente.publicado_en = datetime(2026, 6, 1, tzinfo=timezone.utc)
    await repo.guardar(reciente)

    borrador = crear_modelo_prueba()
    borrador.version = "v-vigente-3-borrador"
    await repo.guardar(borrador)

    vigente = await repo.obtener_vigente()

    assert vigente is not None
    assert vigente.version == "v-vigente-2"
    assert vigente.publicado is True


@pytest.mark.asyncio
async def test_obtener_vigente_sin_ninguna_publicada_devuelve_none(db):
    repo = RepositorioMongoModeloMadurez(db)
    borrador = crear_modelo_prueba()
    await repo.guardar(borrador)

    assert await repo.obtener_vigente() is None


@pytest.mark.asyncio
async def test_desactivar_pregunta_persiste_y_se_recupera(db):
    """HU-029: activo es un campo nuevo en Pregunta; confirma que el
    round-trip contra Mongo real lo conserva."""
    repo = RepositorioMongoModeloMadurez(db)
    modelo = await repo.guardar(crear_modelo_prueba())

    # p2 depende de la condición de p1, así que se desactiva p2 (no p1)
    modelo.desactivar_pregunta("p2")
    await repo.actualizar(modelo)

    recuperado = await repo.obtener_por_id(modelo.id)
    preguntas_por_codigo = {p.codigo: p for p in recuperado.preguntas}
    assert preguntas_por_codigo["p2"].activo is False
    assert preguntas_por_codigo["p1"].activo is True
