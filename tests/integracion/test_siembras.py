from decimal import Decimal

import pytest

from src.dominio.catalogo_permisos import (SECTORES_INICIALES,
                                           SECTORES_RETIRADOS)
from src.dominio.servicios.motor_calculo import calcular_nivel
from src.infraestructura.persistencia.inicializacion import sembrar_sectores
from src.infraestructura.persistencia.repositorio_mongo_modelo_madurez import \
    RepositorioMongoModeloMadurez
from src.infraestructura.persistencia.repositorio_mongo_sector import \
    RepositorioMongoSector
from src.infraestructura.persistencia.sembrado_modelo_4p import (
    VERSION_MODELO_4P, construir_modelo_4p, sembrar_modelo_4p)


@pytest.mark.asyncio
async def test_siembra_los_sectores_y_es_idempotente(db):
    await sembrar_sectores(db)
    await sembrar_sectores(db)

    sectores = await RepositorioMongoSector(db).listar_activos()
    assert {s.codigo for s in sectores} == {c for c, _ in SECTORES_INICIALES}
    assert await db["sectores"].count_documents({}) == len(SECTORES_INICIALES)


@pytest.mark.asyncio
async def test_no_pisa_un_sector_renombrado_ni_reactiva_uno_desactivado(db):
    await sembrar_sectores(db)
    await db["sectores"].update_one(
        {"codigo": "fintech"}, {"$set": {"nombre": "Finanzas"}}
    )
    await db["sectores"].update_one(
        {"codigo": "otros_servicios"}, {"$set": {"activo": False}}
    )

    await sembrar_sectores(db)

    repo = RepositorioMongoSector(db)
    assert (await repo.obtener_por_codigo("fintech")).nombre == "Finanzas"
    assert await repo.obtener_por_codigo("otros_servicios") is None


@pytest.mark.asyncio
async def test_sector_inexistente_devuelve_none(db):
    assert await RepositorioMongoSector(db).obtener_por_codigo("no-existe") is None


def test_el_modelo_4p_es_publicable_y_tiene_la_estructura_del_frontend():
    modelo = construir_modelo_4p()
    modelo.publicar("prueba")

    assert [d.codigo for d in modelo.dimensiones] == [
        "proposito",
        "procesos",
        "personas",
        "plataforma",
    ]
    assert all(d.peso == Decimal("0.25") for d in modelo.dimensiones)
    assert len(modelo.preguntas) == 16
    assert all(
        len(p.opciones) == 4 and p.tipo == "seleccion_unica" for p in modelo.preguntas
    )
    assert [o.valor for o in modelo.preguntas[0].opciones] == [25, 50, 75, 100]
    assert (modelo.escala_min, modelo.escala_max) == (0, 100)
    assert {p.dimension_codigo for p in modelo.preguntas if p.en_demo} == {
        d.codigo for d in modelo.dimensiones
    }


@pytest.mark.parametrize(
    "indice,nivel",
    [(0, 1), (10, 1), (10.5, 2), (25, 3), (50, 5), (55, 6), (75, 8), (90, 9), (95, 10), (100, 10)],
)
def test_la_rubrica_inicial_de_10_niveles_cubre_toda_la_escala(indice, nivel):
    assert (
        calcular_nivel(Decimal(str(indice)), construir_modelo_4p().niveles).nivel
        == nivel
    )


@pytest.mark.asyncio
async def test_siembra_el_modelo_4p_una_sola_vez(db):
    assert await sembrar_modelo_4p(db) is True
    assert await sembrar_modelo_4p(db) is False

    repo = RepositorioMongoModeloMadurez(db)
    vigente = await repo.obtener_vigente()
    assert vigente.version == VERSION_MODELO_4P and vigente.publicado
    assert len(vigente.preguntas) == 16


@pytest.mark.asyncio
async def test_retira_una_sola_vez_los_sectores_que_no_son_servicios(db):
    # Catalogo anterior: sectores fuera de servicios ya existentes y activos.
    for codigo in SECTORES_RETIRADOS:
        await db["sectores"].insert_one(
            {"codigo": codigo, "nombre": codigo, "activo": True}
        )

    await sembrar_sectores(db)

    repo = RepositorioMongoSector(db)
    activos = {s.codigo for s in await repo.listar_activos()}
    assert activos == {c for c, _ in SECTORES_INICIALES}
    assert not activos & set(SECTORES_RETIRADOS)

    # Si el administrador reactiva uno, el arranque siguiente no lo vuelve a retirar.
    await db["sectores"].update_one({"codigo": "alimentos"}, {"$set": {"activo": True}})
    await sembrar_sectores(db)
    assert await repo.obtener_por_codigo("alimentos") is not None
