from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.rol import RolCatalogo
from src.dominio.puertos.repositorio_rol import RepositorioRol


class RepositorioMongoRol(RepositorioRol):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["roles"]

    async def guardar(self, rol: RolCatalogo) -> RolCatalogo:
        doc = self._a_documento(rol)
        resultado = await self._coleccion.insert_one(doc)
        rol.id = str(resultado.inserted_id)
        return rol

    async def obtener_por_codigo(self, codigo: str) -> Optional[RolCatalogo]:
        doc = await self._coleccion.find_one({"codigo": codigo})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def actualizar(self, rol: RolCatalogo) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(rol.id)},
            {"$set": self._a_documento(rol)},
        )

    async def listar_activos(self) -> list[RolCatalogo]:
        cursor = self._coleccion.find({"activo": True})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> RolCatalogo:
        return RolCatalogo(
            id=str(doc["_id"]),
            codigo=doc["codigo"],
            nombre=doc["nombre"],
            descripcion=doc.get("descripcion", ""),
            es_sistema=doc.get("es_sistema", False),
            permisos=doc.get("permisos", []),
            activo=doc.get("activo", True),
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, rol: RolCatalogo) -> dict:
        return {
            "codigo": rol.codigo,
            "nombre": rol.nombre,
            "descripcion": rol.descripcion,
            "es_sistema": rol.es_sistema,
            "permisos": rol.permisos,
            "activo": rol.activo,
            "creado_en": rol.creado_en,
        }
