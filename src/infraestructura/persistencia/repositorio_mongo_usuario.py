from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.usuario import Asignacion, Rol, Usuario
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class RepositorioMongoUsuario(RepositorioUsuario):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["usuarios"]

    async def obtener_por_correo(self, correo: str) -> Optional[Usuario]:
        doc = await self._coleccion.find_one({"correo": correo, "activo": True})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def obtener_por_id(self, usuario_id: str) -> Optional[Usuario]:
        try:
            id_valido = ObjectId(usuario_id)
        except InvalidId:
            return None
        doc = await self._coleccion.find_one({"_id": id_valido})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def guardar(self, usuario: Usuario) -> Usuario:
        doc = self._a_documento(usuario)
        resultado = await self._coleccion.insert_one(doc)
        usuario.id = str(resultado.inserted_id)
        return usuario

    async def actualizar(self, usuario: Usuario) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(usuario.id)},
            {"$set": self._a_documento(usuario)},
        )

    async def listar_por_empresa(self, empresa_id: str) -> list[Usuario]:
        cursor = self._coleccion.find({"empresa_id": empresa_id, "activo": True})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    async def listar_todos(self) -> list[Usuario]:
        cursor = self._coleccion.find({})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    async def listar_por_rol(self, codigo_rol: str) -> list[Usuario]:
        cursor = self._coleccion.find({"rol.codigo": codigo_rol})
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> Usuario:
        asignaciones = [
            Asignacion(
                empresa_id=a["empresa_id"],
                asignado_en=a["asignado_en"],
                finalizado_en=a.get("finalizado_en"),
            )
            for a in doc.get("asignaciones", [])
        ]
        return Usuario(
            id=str(doc["_id"]),
            correo=doc["correo"],
            clave_hash=doc["clave_hash"],
            nombres=doc["nombres"],
            apellidos=doc["apellidos"],
            rol=Rol(codigo=doc["rol"]["codigo"], permisos=doc["rol"]["permisos"]),
            empresa_id=doc.get("empresa_id"),
            intentos_fallidos=doc.get("intentos_fallidos", 0),
            bloqueado_hasta=doc.get("bloqueado_hasta"),
            activo=doc.get("activo", True),
            asignaciones=asignaciones,
            historial_claves=doc.get("historial_claves", []),
        )

    def _a_documento(self, usuario: Usuario) -> dict:
        return {
            "correo": usuario.correo,
            "clave_hash": usuario.clave_hash,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "rol": {"codigo": usuario.rol.codigo, "permisos": usuario.rol.permisos},
            "empresa_id": usuario.empresa_id,
            "intentos_fallidos": usuario.intentos_fallidos,
            "bloqueado_hasta": usuario.bloqueado_hasta,
            "activo": usuario.activo,
            "historial_claves": usuario.historial_claves,
            "asignaciones": [
                {
                    "empresa_id": a.empresa_id,
                    "asignado_en": a.asignado_en,
                    "finalizado_en": a.finalizado_en,
                }
                for a in usuario.asignaciones
            ],
        }
