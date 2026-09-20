import hashlib
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.puertos.repositorio_token import RepositorioToken


class RepositorioMongoToken(RepositorioToken):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["tokens_verificacion"]

    async def guardar(self, token: TokenVerificacion, codigo: str) -> TokenVerificacion:
        doc = self._a_documento(token, codigo)
        resultado = await self._coleccion.insert_one(doc)
        token.id = str(resultado.inserted_id)
        return token

    async def obtener_por_codigo(self, codigo: str) -> Optional[TokenVerificacion]:
        codigo_hash = self._hash(codigo)
        doc = await self._coleccion.find_one({"codigo_hash": codigo_hash})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def actualizar(self, token: TokenVerificacion) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(token.id)},
            {"$set": {"usado_en": token.usado_en}},
        )

    def _hash(self, codigo: str) -> str:
        return hashlib.sha256(codigo.encode()).hexdigest()

    def _a_entidad(self, doc: dict) -> TokenVerificacion:
        return TokenVerificacion(
            id=str(doc["_id"]),
            tipo=TipoToken(doc["tipo"]),
            correo_destino=doc["correo_destino"],
            solicitud_id=doc.get("solicitud_id"),
            usuario_id=doc.get("usuario_id"),
            expira_en=doc["expira_en"],
            usado_en=doc.get("usado_en"),
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, token: TokenVerificacion, codigo: str) -> dict:
        return {
            "tipo": token.tipo.value,
            "correo_destino": token.correo_destino,
            "codigo_hash": self._hash(codigo),
            "solicitud_id": token.solicitud_id,
            "usuario_id": token.usuario_id,
            "expira_en": token.expira_en,
            "usado_en": token.usado_en,
            "creado_en": token.creado_en,
        }
