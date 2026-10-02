import pytest

from src.dominio.entidades.notificacion import Notificacion
from src.infraestructura.persistencia.repositorio_mongo_notificacion import \
    RepositorioMongoNotificacion


@pytest.mark.asyncio
async def test_registrar_asigna_id_y_persiste_los_datos(db):
    repo = RepositorioMongoNotificacion(db)
    notificacion = Notificacion(
        id=None,
        usuario_id="user-1",
        correo_destino="ana@innovatech.com",
        tipo="diagnostico_evaluado",
        asunto="Asunto de prueba",
        contenido="Contenido de prueba",
    )

    resultado = await repo.registrar(notificacion)

    assert resultado.id is not None
    doc = await db["notificaciones"].find_one({"correo_destino": "ana@innovatech.com"})
    assert doc is not None
    assert doc["tipo"] == "diagnostico_evaluado"
    assert doc["intentos"] == 1
    assert doc["error"] is None


@pytest.mark.asyncio
async def test_registrar_notificacion_con_error_de_envio(db):
    repo = RepositorioMongoNotificacion(db)
    notificacion = Notificacion(
        id=None,
        usuario_id=None,
        correo_destino="admin@trust4p.com",
        tipo="diagnostico_fallido",
        asunto="Asunto",
        contenido="Contenido",
        enviada_en=None,
        error="SMTP no disponible",
    )

    await repo.registrar(notificacion)

    doc = await db["notificaciones"].find_one({"correo_destino": "admin@trust4p.com"})
    assert doc["enviada_en"] is None
    assert doc["error"] == "SMTP no disponible"
