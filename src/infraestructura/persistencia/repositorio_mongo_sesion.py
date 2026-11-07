import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from src.dominio.entidades.usuario import Usuario
from src.dominio.puertos.repositorio_sesion import RepositorioSesion
from src.dominio.servicios.vigencia_sesion import (EstadoAcceso,
                                                   motivo_invalidez)

registro = logging.getLogger("trust4p.sesiones")

DURACION_SESION_MINUTOS = 30  # RF-47: cierre de sesión por inactividad


class RepositorioMongoSesion(RepositorioSesion):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["sesiones"]
        self._usuarios = db["usuarios"]
        self._roles = db["roles"]
        self._empresas = db["empresas"]

    async def crear(self, usuario: Usuario) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = self._hash(token)

        await self._coleccion.insert_one(
            {
                "usuario_id": usuario.id,
                "token_hash": token_hash,
                "rol_codigo": usuario.rol.codigo,
                "empresa_id": usuario.empresa_id,
                "permisos": usuario.rol.permisos,
                "expira_en": datetime.now(timezone.utc)
                + timedelta(minutes=DURACION_SESION_MINUTOS),
                "creado_en": datetime.now(timezone.utc),
            }
        )
        return token  # el token en claro solo existe aquí; nunca se persiste

    async def obtener_usuario_id_por_token(self, token: str) -> Optional[str]:
        doc = await self._renovar_y_obtener(token)
        if doc is None:
            return None
        return doc["usuario_id"]

    async def obtener_sesion_por_token(self, token: str) -> Optional[dict]:
        return await self._renovar_y_obtener(token)

    async def _renovar_y_obtener(self, token: str) -> Optional[dict]:
        """RF-47: cada verificación exitosa es una interacción del usuario y
        extiende la sesión desde ese momento (ventana deslizante), no desde
        el inicio de sesión. Antes de extenderla se revalida contra el estado
        actual del usuario, su rol y su empresa (R-16, R-17): si cambió, la
        sesión se elimina y no se acepta, aunque la revocación explícita no
        se haya hecho o haya fallado."""
        token_hash = self._hash(token)
        ahora = datetime.now(timezone.utc)
        sesion = await self._coleccion.find_one(
            {"token_hash": token_hash, "expira_en": {"$gt": ahora}}
        )
        if sesion is None:
            return None

        motivo = motivo_invalidez(sesion, await self._estado_acceso(sesion))
        if motivo is not None:
            await self._coleccion.delete_one({"_id": sesion["_id"]})
            registro.warning(
                "Sesión del usuario %s descartada al revalidarla: %s",
                sesion.get("usuario_id"),
                motivo,
            )
            return None

        return await self._coleccion.find_one_and_update(
            {"_id": sesion["_id"], "expira_en": {"$gt": ahora}},
            {
                "$set": {
                    "expira_en": datetime.now(timezone.utc)
                    + timedelta(minutes=DURACION_SESION_MINUTOS)
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def _estado_acceso(self, sesion: dict) -> Optional[EstadoAcceso]:
        try:
            usuario = await self._usuarios.find_one(
                {"_id": ObjectId(sesion.get("usuario_id"))}
            )
        except (InvalidId, TypeError):
            return None
        if usuario is None:
            return None
        rol_usuario = usuario.get("rol") or {}
        rol_codigo = rol_usuario.get("codigo")
        # R-16: los permisos efectivos salen del catálogo de roles; si el rol
        # no está en el catálogo, de la copia del usuario (igual que al iniciar
        # sesión).
        rol = await self._roles.find_one({"codigo": rol_codigo})
        permisos = (
            rol.get("permisos", []) if rol is not None else rol_usuario.get("permisos", [])
        )
        empresa_id = usuario.get("empresa_id")
        empresa_activa = True
        if empresa_id:
            try:
                empresa = await self._empresas.find_one({"_id": ObjectId(empresa_id)})
            except (InvalidId, TypeError):
                empresa = None
            empresa_activa = empresa is not None and empresa.get("activo", True)
        return EstadoAcceso(
            activo=usuario.get("activo", True),
            registro_pendiente=usuario.get("registro_pendiente", False),
            rol_codigo=rol_codigo,
            empresa_id=empresa_id,
            permisos_vigentes=list(permisos),
            empresa_activa=empresa_activa,
        )

    async def revocar(self, token: str) -> None:
        token_hash = self._hash(token)
        await self._coleccion.delete_one({"token_hash": token_hash})

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def revocar_todas_de_usuario(self, usuario_id: str) -> None:
        await self._coleccion.delete_many({"usuario_id": usuario_id})
