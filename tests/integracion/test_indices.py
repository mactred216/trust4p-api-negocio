import pytest
from pymongo.errors import DuplicateKeyError

from src.infraestructura.persistencia.inicializacion import (INDICES,
                                                             crear_indices)


@pytest.mark.asyncio
async def test_crea_todos_los_indices_y_es_idempotente(db):
    assert await crear_indices(db) == []
    assert await crear_indices(db) == []

    total = 0
    for coleccion in {c for c, _, _ in INDICES}:
        informacion = await db[coleccion].index_information()
        total += len(informacion) - 1  # sin _id_
    assert total == len(INDICES)


@pytest.mark.asyncio
async def test_correo_de_usuario_unico(db):
    await crear_indices(db)
    await db["usuarios"].insert_one({"correo": "a@x.com"})

    with pytest.raises(DuplicateKeyError):
        await db["usuarios"].insert_one({"correo": "a@x.com"})


@pytest.mark.asyncio
async def test_consecutivo_de_diagnostico_unico_por_empresa(db):
    await crear_indices(db)
    await db["diagnosticos"].insert_one({"empresa_id": "e1", "consecutivo": 1})
    await db["diagnosticos"].insert_one({"empresa_id": "e2", "consecutivo": 1})

    with pytest.raises(DuplicateKeyError):
        await db["diagnosticos"].insert_one({"empresa_id": "e1", "consecutivo": 1})


@pytest.mark.asyncio
async def test_nit_unico_solo_entre_empresas_que_lo_tienen(db):
    await crear_indices(db)
    await db["empresas"].insert_many(
        [{"nombre": "A", "nit": None}, {"nombre": "B", "nit": None}, {"nombre": "C"}]
    )
    await db["empresas"].insert_one({"nombre": "D", "nit": "900123456"})

    with pytest.raises(DuplicateKeyError):
        await db["empresas"].insert_one({"nombre": "E", "nit": "900123456"})


@pytest.mark.asyncio
async def test_sesiones_y_tokens_vencidos_se_eliminan_solos(db):
    await crear_indices(db)

    for coleccion in ("sesiones", "tokens_verificacion"):
        indice = (await db[coleccion].index_information())["expira_en_1"]
        assert indice["expireAfterSeconds"] == 0


@pytest.mark.asyncio
async def test_un_unico_imposible_se_reporta_y_no_impide_los_demas(db):
    await db["usuarios"].insert_many([{"correo": "dup@x.com"}, {"correo": "dup@x.com"}])

    problemas = await crear_indices(db)

    assert len(problemas) == 1 and "usuarios['correo']" in problemas[0]
    assert "token_hash_1" in await db["sesiones"].index_information()
