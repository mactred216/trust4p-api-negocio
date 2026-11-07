from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from src.dominio.entidades.usuario import Rol, Usuario
from src.infraestructura.persistencia.repositorio_mongo_sesion import (
    DURACION_SESION_MINUTOS, RepositorioMongoSesion)


USUARIO_ID = "65f0c0ffee0000000000a001"


async def crear_usuario_prueba(db, usuario_id=USUARIO_ID) -> Usuario:
    """La sesión se revalida contra el usuario guardado: debe existir."""
    await db["usuarios"].insert_one(
        {
            "_id": ObjectId(usuario_id),
            "correo": "sesion@trust4p.com",
            "rol": {"codigo": "representante", "permisos": ["diagnosticos.iniciar"]},
            "empresa_id": None,
            "activo": True,
        }
    )
    return Usuario(
        id=usuario_id,
        correo="sesion@trust4p.com",
        clave_hash="hash",
        nombres="Prueba",
        apellidos="Integración",
        rol=Rol(codigo="representante", permisos=["diagnosticos.iniciar"]),
    )


@pytest.mark.asyncio
async def test_crear_y_obtener_sesion_por_token(db):
    repo = RepositorioMongoSesion(db)
    token = await repo.crear(await crear_usuario_prueba(db))

    sesion = await repo.obtener_sesion_por_token(token)

    assert sesion is not None
    assert sesion["usuario_id"] == USUARIO_ID
    assert sesion["rol_codigo"] == "representante"


@pytest.mark.asyncio
async def test_obtener_usuario_id_por_token(db):
    repo = RepositorioMongoSesion(db)
    token = await repo.crear(await crear_usuario_prueba(db))

    usuario_id = await repo.obtener_usuario_id_por_token(token)

    assert usuario_id == USUARIO_ID


@pytest.mark.asyncio
async def test_sesion_expirada_no_se_recupera(db):
    repo = RepositorioMongoSesion(db)
    token = await repo.crear(await crear_usuario_prueba(db))
    await db["sesiones"].update_one(
        {}, {"$set": {"expira_en": datetime.now(timezone.utc) - timedelta(minutes=1)}}
    )

    assert await repo.obtener_sesion_por_token(token) is None
    assert await repo.obtener_usuario_id_por_token(token) is None


@pytest.mark.asyncio
async def test_verificar_sesion_extiende_la_expiracion(db):
    """RF-47: cada verificación exitosa es una interacción del usuario y debe
    extender la sesión desde ese momento (ventana deslizante), no dejarla
    vencer a los 30 minutos del inicio de sesión sin importar la actividad."""
    repo = RepositorioMongoSesion(db)
    token = await repo.crear(await crear_usuario_prueba(db))
    proxima_a_vencer = datetime.now(timezone.utc) + timedelta(minutes=1)
    await db["sesiones"].update_one({}, {"$set": {"expira_en": proxima_a_vencer}})

    sesion = await repo.obtener_sesion_por_token(token)

    assert sesion is not None
    nueva_expiracion = sesion["expira_en"]
    if nueva_expiracion.tzinfo is None:
        nueva_expiracion = nueva_expiracion.replace(tzinfo=timezone.utc)
    assert nueva_expiracion > proxima_a_vencer + timedelta(
        minutes=DURACION_SESION_MINUTOS - 2
    )


@pytest.mark.asyncio
async def test_revocar_elimina_la_sesion(db):
    repo = RepositorioMongoSesion(db)
    token = await repo.crear(await crear_usuario_prueba(db))

    await repo.revocar(token)

    assert await repo.obtener_sesion_por_token(token) is None


@pytest.mark.asyncio
async def test_revocar_todas_de_usuario(db):
    repo = RepositorioMongoSesion(db)
    usuario = await crear_usuario_prueba(db)
    token_1 = await repo.crear(usuario)
    token_2 = await repo.crear(usuario)

    await repo.revocar_todas_de_usuario(usuario.id)

    assert await repo.obtener_sesion_por_token(token_1) is None
    assert await repo.obtener_sesion_por_token(token_2) is None
