from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa


class RepositorioMongoEmpresa(RepositorioEmpresa):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["empresas"]
        self._coleccion_sectores = db["sectores"]

    async def guardar(self, empresa: Empresa) -> Empresa:
        doc = self._a_documento(empresa)
        resultado = await self._coleccion.insert_one(doc)
        empresa.id = str(resultado.inserted_id)
        return empresa

    async def obtener_por_id(self, empresa_id: str) -> Optional[Empresa]:
        doc = await self._coleccion.find_one({"_id": ObjectId(empresa_id)})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def actualizar(self, empresa: Empresa) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(empresa.id)},
            {"$set": self._a_documento(empresa)},
        )

    async def listar_activas(self) -> list[Empresa]:
        cursor = self._coleccion.find({"activo": True})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> Empresa:
        return Empresa(
            id=str(doc["_id"]),
            nombre=doc["nombre"],
            sector=Sector(
                id=doc["sector"]["id"],
                codigo=doc["sector"]["codigo"],
                nombre=doc["sector"]["nombre"],
            ),
            nit=doc.get("nit"),
            numero_empleados=doc.get("numero_empleados"),
            ciudad=doc.get("ciudad"),
            activo=doc.get("activo", True),
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, empresa: Empresa) -> dict:
        return {
            "nombre": empresa.nombre,
            "sector": {
                "id": empresa.sector.id,
                "codigo": empresa.sector.codigo,
                "nombre": empresa.sector.nombre,
            },
            "nit": empresa.nit,
            "numero_empleados": empresa.numero_empleados,
            "ciudad": empresa.ciudad,
            "activo": empresa.activo,
            "creado_en": empresa.creado_en,
        }

    async def listar_todas(self) -> list[Empresa]:
        cursor = self._coleccion.find({})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]
