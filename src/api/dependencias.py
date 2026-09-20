from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.aplicacion.casos_uso.iniciar_sesion import IniciarSesion
from src.aplicacion.casos_uso.radicar_solicitud import RadicarSolicitud
from src.aplicacion.casos_uso.resolver_solicitud import ResolverSolicitud
from src.infraestructura.persistencia.conexion import obtener_base_datos
from src.infraestructura.persistencia.repositorio_mongo_empresa import \
    RepositorioMongoEmpresa
from src.infraestructura.persistencia.repositorio_mongo_sesion import \
    RepositorioMongoSesion
from src.infraestructura.persistencia.repositorio_mongo_solicitud import \
    RepositorioMongoSolicitud
from src.infraestructura.persistencia.repositorio_mongo_usuario import \
    RepositorioMongoUsuario


def obtener_repositorio_solicitud(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSolicitud:
    return RepositorioMongoSolicitud(db)


def obtener_caso_uso_radicar_solicitud(
    repo: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
) -> RadicarSolicitud:
    return RadicarSolicitud(repo)


def obtener_repositorio_usuario(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoUsuario:
    return RepositorioMongoUsuario(db)


def obtener_repositorio_sesion(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSesion:
    return RepositorioMongoSesion(db)


def obtener_caso_uso_iniciar_sesion(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> IniciarSesion:
    return IniciarSesion(repo_usuario, repo_sesion)


def obtener_repositorio_empresa(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoEmpresa:
    return RepositorioMongoEmpresa(db)


def obtener_caso_uso_resolver_solicitud(
    repo_solicitud: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> ResolverSolicitud:
    return ResolverSolicitud(repo_solicitud, repo_empresa)


from src.aplicacion.casos_uso.gestionar_empresas import (ConsultarEmpresa,
                                                         DesactivarEmpresa,
                                                         EditarEmpresa,
                                                         ListarEmpresas,
                                                         ReactivarEmpresa)


def obtener_caso_uso_listar_empresas(
    repo: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> ListarEmpresas:
    return ListarEmpresas(repo)


def obtener_caso_uso_consultar_empresa(
    repo: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> ConsultarEmpresa:
    return ConsultarEmpresa(repo)


def obtener_caso_uso_editar_empresa(
    repo: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> EditarEmpresa:
    return EditarEmpresa(repo)


def obtener_caso_uso_desactivar_empresa(
    repo: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> DesactivarEmpresa:
    return DesactivarEmpresa(repo)


def obtener_caso_uso_reactivar_empresa(
    repo: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> ReactivarEmpresa:
    return ReactivarEmpresa(repo)
