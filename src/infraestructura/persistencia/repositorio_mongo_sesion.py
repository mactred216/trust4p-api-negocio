import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.usuario import Usuario
from src.dominio.puertos.repositorio_sesion import RepositorioSesion

DURACION_SESION_MINUTOS = 30  # RF-49: cierre por inactividad


class RepositorioMongoSesion(RepositorioSesion):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["sesiones"]

    async def crear(self, usuario: Usuario) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = self._hash(token)

        await self._coleccion.insert_one(
            {
                "usuario_id": usuario.id,
                "token_hash": token_hash,
                "rol_codigo": usuario.rol.codigo,
                "permisos": usuario.rol.permisos,
                "expira_en": datetime.now(timezone.utc)
                + timedelta(minutes=DURACION_SESION_MINUTOS),
                "creado_en": datetime.now(timezone.utc),
            }
        )
        return token  # el token en claro solo existe aquí; nunca se persiste

    async def obtener_usuario_id_por_token(self, token: str) -> Optional[str]:
        token_hash = self._hash(token)
        doc = await self._coleccion.find_one(
            {
                "token_hash": token_hash,
                "expira_en": {"$gt": datetime.now(timezone.utc)},
            }
        )
        if doc is None:
            return None
        return doc["usuario_id"]

    async def obtener_sesion_por_token(self, token: str) -> Optional[dict]:
        token_hash = self._hash(token)
        doc = await self._coleccion.find_one(
            {
                "token_hash": token_hash,
                "expira_en": {"$gt": datetime.now(timezone.utc)},
            }
        )
        return doc

    async def revocar(self, token: str) -> None:
        token_hash = self._hash(token)
        await self._coleccion.delete_one({"token_hash": token_hash})

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def revocar_todas_de_usuario(self, usuario_id: str) -> None:
        await self._coleccion.delete_many({"usuario_id": usuario_id})
