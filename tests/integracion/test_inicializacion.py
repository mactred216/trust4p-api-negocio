import pytest

from src.dominio.catalogo_permisos import PERMISOS_POR_ROL, PERMISOS_SISTEMA
from src.infraestructura.persistencia.inicializacion import sembrar_permisos


@pytest.mark.asyncio
async def test_siembra_catalogo_y_roles_de_sistema(db):
    await sembrar_permisos(db)

    codigos = {p["codigo"] async for p in db["permisos"].find({})}
    assert codigos == {c for c, _, _ in PERMISOS_SISTEMA}
    for rol, esperados in PERMISOS_POR_ROL.items():
        doc = await db["roles"].find_one({"codigo": rol})
        assert set(doc["permisos"]) == set(esperados)
        assert doc["es_sistema"] is True


@pytest.mark.asyncio
async def test_es_idempotente(db):
    await sembrar_permisos(db)
    await sembrar_permisos(db)

    assert await db["permisos"].count_documents({}) == len(PERMISOS_SISTEMA)
    assert await db["roles"].count_documents({}) == len(PERMISOS_POR_ROL)
    doc = await db["roles"].find_one({"codigo": "consultor"})
    assert len(doc["permisos"]) == len(set(doc["permisos"]))


@pytest.mark.asyncio
async def test_no_vuelve_a_conceder_un_permiso_retirado(db):
    """HU-028: lo que el administrador retira no se restituye al reiniciar."""
    await sembrar_permisos(db)
    await db["roles"].update_one(
        {"codigo": "consultor"}, {"$pull": {"permisos": "diagnosticos.consultar"}}
    )

    await sembrar_permisos(db)

    doc = await db["roles"].find_one({"codigo": "consultor"})
    assert "diagnosticos.consultar" not in doc["permisos"]


@pytest.mark.asyncio
async def test_respeta_los_permisos_existentes_y_agrega_los_nuevos(db):
    await db["roles"].insert_one(
        {
            "codigo": "administrador",
            "nombre": "Administrador",
            "es_sistema": True,
            "permisos": ["roles.gestionar", "empresas.gestionar"],
            "activo": True,
        }
    )

    await sembrar_permisos(db)

    doc = await db["roles"].find_one({"codigo": "administrador"})
    assert set(doc["permisos"]) == set(PERMISOS_POR_ROL["administrador"])


@pytest.mark.asyncio
async def test_revoca_las_sesiones_del_rol_al_sembrar_permisos_nuevos(db):
    await db["sesiones"].insert_many(
        [
            {"usuario_id": "1", "rol_codigo": "consultor", "permisos": []},
            {"usuario_id": "2", "rol_codigo": "otro", "permisos": []},
        ]
    )

    await sembrar_permisos(db)

    assert await db["sesiones"].count_documents({"rol_codigo": "consultor"}) == 0
    assert await db["sesiones"].count_documents({"rol_codigo": "otro"}) == 1
