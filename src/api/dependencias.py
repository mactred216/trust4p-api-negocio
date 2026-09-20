from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.aplicacion.casos_uso.radicar_solicitud import RadicarSolicitud
from src.infraestructura.persistencia.conexion import obtener_base_datos
from src.infraestructura.persistencia.repositorio_mongo_solicitud import \
    RepositorioMongoSolicitud


def obtener_repositorio_solicitud(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSolicitud:
    return RepositorioMongoSolicitud(db)


def obtener_caso_uso_radicar_solicitud(
    repo: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
) -> RadicarSolicitud:
    return RadicarSolicitud(repo)
