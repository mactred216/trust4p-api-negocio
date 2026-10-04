from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudAcceso)
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud


class RepositorioMongoSolicitud(RepositorioSolicitud):
    """Adaptador de salida. Implementa el puerto sobre MongoDB (patrón Repositorio)."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["solicitudes_acceso"]

    async def guardar(self, solicitud: SolicitudAcceso) -> SolicitudAcceso:
        doc = self._a_documento(solicitud)
        resultado = await self._coleccion.insert_one(doc)
        solicitud.id = str(resultado.inserted_id)
        return solicitud

    async def obtener_por_id(self, solicitud_id: str) -> Optional[SolicitudAcceso]:
        try:
            id_valido = ObjectId(solicitud_id)
        except InvalidId:
            return None
        doc = await self._coleccion.find_one({"_id": id_valido})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def existe_pendiente_con_correo(self, correo: str) -> bool:
        doc = await self._coleccion.find_one(
            {
                "correo_solicitante": correo,
                "estado": EstadoSolicitud.PENDIENTE.value,
            }
        )
        return doc is not None

    async def existe_pendiente_con_nit(self, nit: str) -> bool:
        doc = await self._coleccion.find_one(
            {"nit": nit, "estado": EstadoSolicitud.PENDIENTE.value}
        )
        return doc is not None

    async def actualizar(self, solicitud: SolicitudAcceso) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(solicitud.id)}, {"$set": self._a_documento(solicitud)}
        )

    async def listar_pendientes(self) -> list[SolicitudAcceso]:
        return await self.listar(EstadoSolicitud.PENDIENTE.value)

    async def listar(self, estado: Optional[str] = None) -> list[SolicitudAcceso]:
        filtro = {"estado": estado} if estado else {}
        cursor = self._coleccion.find(filtro).sort("creado_en", -1)
        return [self._a_entidad(d) for d in await cursor.to_list(length=None)]

    def _a_entidad(self, doc: dict) -> SolicitudAcceso:
        return SolicitudAcceso(
            id=str(doc["_id"]),
            nombre_empresa=doc["nombre_empresa"],
            correo_solicitante=doc["correo_solicitante"],
            nombre_solicitante=doc["nombre_solicitante"],
            estado=EstadoSolicitud(doc["estado"]),
            empresa_id=doc.get("empresa_id"),
            motivo_rechazo=doc.get("motivo_rechazo"),
            creado_en=doc["creado_en"],
            resuelto_en=doc.get("resuelto_en"),
            nit=doc.get("nit"),
            sector_codigo=doc.get("sector_codigo"),
            sector_nombre=doc.get("sector_nombre"),
            numero_empleados=doc.get("numero_empleados"),
            ciudad=doc.get("ciudad"),
            cargo=doc.get("cargo"),
            telefono=doc.get("telefono"),
            acepto_tratamiento_en=doc.get("acepto_tratamiento_en"),
            version_politica_aceptada=doc.get("version_politica_aceptada"),
        )

    def _a_documento(self, solicitud: SolicitudAcceso) -> dict:
        return {
            "nombre_empresa": solicitud.nombre_empresa,
            "correo_solicitante": solicitud.correo_solicitante,
            "nombre_solicitante": solicitud.nombre_solicitante,
            "estado": solicitud.estado.value,
            "empresa_id": solicitud.empresa_id,
            "motivo_rechazo": solicitud.motivo_rechazo,
            "creado_en": solicitud.creado_en,
            "resuelto_en": solicitud.resuelto_en,
            "nit": solicitud.nit,
            "sector_codigo": solicitud.sector_codigo,
            "sector_nombre": solicitud.sector_nombre,
            "numero_empleados": solicitud.numero_empleados,
            "ciudad": solicitud.ciudad,
            "cargo": solicitud.cargo,
            "telefono": solicitud.telefono,
            "acepto_tratamiento_en": solicitud.acepto_tratamiento_en,
            "version_politica_aceptada": solicitud.version_politica_aceptada,
        }
