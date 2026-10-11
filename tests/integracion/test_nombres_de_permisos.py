from datetime import datetime, timezone

import pytest

from src.dominio.catalogo_permisos import PERMISOS_SISTEMA
from src.infraestructura.persistencia.inicializacion import sembrar_permisos


@pytest.mark.asyncio
async def test_la_siembra_guarda_el_nombre_para_mostrar(db):
    await sembrar_permisos(db)

    nombres = {p["codigo"]: p["nombre"] async for p in db["permisos"].find({})}
    assert nombres == {codigo: nombre for codigo, _, nombre, _ in PERMISOS_SISTEMA}


@pytest.mark.asyncio
async def test_un_permiso_que_ya_existia_sin_nombre_lo_recibe_sin_perder_nada_mas(db):
    await db["permisos"].insert_one(
        {
            "codigo": "roles.gestionar",
            "modulo": "administracion",
            "descripcion": "Descripción que el sistema ya tenía",
            "activo": False,
            "creado_en": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    )

    await sembrar_permisos(db)
    await sembrar_permisos(db)

    doc = await db["permisos"].find_one({"codigo": "roles.gestionar"})
    assert doc["nombre"] == "Gestionar roles y permisos"
    assert doc["descripcion"] == "Descripción que el sistema ya tenía"
    assert doc["activo"] is False
    assert await db["permisos"].count_documents({"codigo": "roles.gestionar"}) == 1
