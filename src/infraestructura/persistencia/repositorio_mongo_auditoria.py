from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria


class RepositorioMongoAuditoria(RepositorioAuditoria):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["auditoria"]

    async def registrar(self, registro: RegistroAuditoria) -> None:
        # Solo insert_one. Nunca update ni delete en esta colección (R-11).
        await self._coleccion.insert_one(self._a_documento(registro))

    async def listar(
        self,
        entidad: Optional[str] = None,
        entidad_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        limite: int = 50,
        usuario_ids: Optional[list[str]] = None,
    ) -> list[RegistroAuditoria]:
        filtro = {}
        if entidad:
            filtro["entidad"] = entidad
        if entidad_id:
            filtro["entidad_id"] = entidad_id
        if usuario_id:
            filtro["usuario_id"] = usuario_id
        if usuario_ids is not None:
            filtro["usuario_id"] = (
                {"$in": usuario_ids}
                if not usuario_id
                else {"$in": [i for i in usuario_ids if i == usuario_id]}
            )

        cursor = self._coleccion.find(filtro).sort("registrado_en", -1).limit(limite)
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> RegistroAuditoria:
        return RegistroAuditoria(
            id=str(doc["_id"]),
            usuario_id=doc.get("usuario_id"),
            entidad=doc["entidad"],
            entidad_id=doc.get("entidad_id"),
            accion=doc["accion"],
            valores_anteriores=doc.get("valores_anteriores"),
            valores_nuevos=doc.get("valores_nuevos"),
            direccion_ip=doc.get("direccion_ip"),
            registrado_en=doc["registrado_en"],
        )

    def _a_documento(self, registro: RegistroAuditoria) -> dict:
        return {
            "usuario_id": registro.usuario_id,
            "entidad": registro.entidad,
            "entidad_id": registro.entidad_id,
            "accion": registro.accion,
            "valores_anteriores": registro.valores_anteriores,
            "valores_nuevos": registro.valores_nuevos,
            "direccion_ip": registro.direccion_ip,
            "registrado_en": registro.registrado_en,
        }
