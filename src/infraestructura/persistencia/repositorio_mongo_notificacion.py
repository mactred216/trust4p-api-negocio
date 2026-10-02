from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.notificacion import Notificacion
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion


class RepositorioMongoNotificacion(RepositorioNotificacion):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["notificaciones"]

    async def registrar(self, notificacion: Notificacion) -> Notificacion:
        doc = {
            "usuario_id": notificacion.usuario_id,
            "correo_destino": notificacion.correo_destino,
            "tipo": notificacion.tipo,
            "asunto": notificacion.asunto,
            "contenido": notificacion.contenido,
            "enviada_en": notificacion.enviada_en,
            "intentos": notificacion.intentos,
            "error": notificacion.error,
            "creado_en": notificacion.creado_en,
        }
        resultado = await self._coleccion.insert_one(doc)
        notificacion.id = str(resultado.inserted_id)
        return notificacion
