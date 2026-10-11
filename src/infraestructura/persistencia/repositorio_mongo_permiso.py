from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.permiso import Permiso
from src.dominio.puertos.repositorio_permiso import RepositorioPermiso


class RepositorioMongoPermiso(RepositorioPermiso):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["permisos"]

    async def guardar(self, permiso: Permiso) -> Permiso:
        doc = self._a_documento(permiso)
        resultado = await self._coleccion.insert_one(doc)
        permiso.id = str(resultado.inserted_id)
        return permiso

    async def obtener_por_codigo(self, codigo: str) -> Optional[Permiso]:
        doc = await self._coleccion.find_one({"codigo": codigo})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def listar_activos(self) -> list[Permiso]:
        cursor = self._coleccion.find({"activo": True})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> Permiso:
        return Permiso(
            id=str(doc["_id"]),
            codigo=doc["codigo"],
            modulo=doc["modulo"],
            descripcion=doc["descripcion"],
            activo=doc.get("activo", True),
            nombre=doc.get("nombre"),
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, permiso: Permiso) -> dict:
        return {
            "codigo": permiso.codigo,
            "modulo": permiso.modulo,
            "descripcion": permiso.descripcion,
            "nombre": permiso.nombre,
            "activo": permiso.activo,
            "creado_en": permiso.creado_en,
        }
