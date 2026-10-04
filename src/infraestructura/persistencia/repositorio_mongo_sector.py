from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.empresa import Sector
from src.dominio.puertos.repositorio_sector import RepositorioSector


class RepositorioMongoSector(RepositorioSector):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["sectores"]

    async def obtener_por_codigo(self, codigo: str) -> Optional[Sector]:
        doc = await self._coleccion.find_one({"codigo": codigo, "activo": True})
        return self._a_entidad(doc) if doc else None

    async def listar_activos(self) -> list[Sector]:
        cursor = self._coleccion.find({"activo": True}).sort("nombre", 1)
        return [self._a_entidad(d) for d in await cursor.to_list(length=None)]

    @staticmethod
    def _a_entidad(doc: dict) -> Sector:
        return Sector(id=str(doc["_id"]), codigo=doc["codigo"], nombre=doc["nombre"])
