from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.aplicacion.casos_uso.asignar_consultor import AsignarConsultor
from src.aplicacion.casos_uso.completar_registro import CompletarRegistro
from src.aplicacion.casos_uso.gestionar_roles import (AgregarPermisoARol,
                                                      ListarPermisos,
                                                      ListarRoles,
                                                      QuitarPermisoDeRol)
from src.aplicacion.casos_uso.gestionar_usuarios import (ConsultarUsuario,
                                                         DesactivarUsuario,
                                                         EditarUsuario,
                                                         ListarUsuarios,
                                                         ReactivarUsuario)
from src.aplicacion.casos_uso.iniciar_sesion import IniciarSesion
from src.aplicacion.casos_uso.radicar_solicitud import RadicarSolicitud
from src.aplicacion.casos_uso.resolver_solicitud import ResolverSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.infraestructura.clientes.cliente_correo_smtp import ClienteCorreoSMTP
from src.infraestructura.persistencia.conexion import obtener_base_datos
from src.infraestructura.persistencia.repositorio_mongo_empresa import \
    RepositorioMongoEmpresa
from src.infraestructura.persistencia.repositorio_mongo_permiso import \
    RepositorioMongoPermiso
from src.infraestructura.persistencia.repositorio_mongo_rol import \
    RepositorioMongoRol
from src.infraestructura.persistencia.repositorio_mongo_sesion import \
    RepositorioMongoSesion
from src.infraestructura.persistencia.repositorio_mongo_solicitud import \
    RepositorioMongoSolicitud
from src.infraestructura.persistencia.repositorio_mongo_token import \
    RepositorioMongoToken
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


def obtener_servicio_correo() -> ClienteCorreoSMTP:
    return ClienteCorreoSMTP()


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


from src.aplicacion.casos_uso.consultar_auditoria import ConsultarAuditoria
from src.aplicacion.casos_uso.gestionar_empresas import (ConsultarEmpresa,
                                                         DesactivarEmpresa,
                                                         EditarEmpresa,
                                                         ListarEmpresas,
                                                         ReactivarEmpresa)
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria
from src.infraestructura.persistencia.repositorio_mongo_auditoria import \
    RepositorioMongoAuditoria


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


def obtener_repositorio_token(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoToken:
    return RepositorioMongoToken(db)


def obtener_caso_uso_resolver_solicitud(
    repo_solicitud: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
) -> ResolverSolicitud:
    return ResolverSolicitud(repo_solicitud, repo_empresa, repo_token, servicio_correo)


def obtener_caso_uso_completar_registro(
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_solicitud: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
) -> CompletarRegistro:
    return CompletarRegistro(repo_token, repo_usuario, repo_solicitud)


from src.aplicacion.casos_uso.recuperar_contrasena import (
    RestablecerContrasena, SolicitarRestablecimiento)


def obtener_caso_uso_solicitar_restablecimiento(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
) -> SolicitarRestablecimiento:
    return SolicitarRestablecimiento(repo_usuario, repo_token, servicio_correo)


def obtener_caso_uso_restablecer_contrasena(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> RestablecerContrasena:
    return RestablecerContrasena(repo_usuario, repo_token, repo_sesion)


def obtener_caso_uso_listar_usuarios(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ListarUsuarios:
    return ListarUsuarios(repo)


def obtener_caso_uso_consultar_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ConsultarUsuario:
    return ConsultarUsuario(repo)


def obtener_caso_uso_editar_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> EditarUsuario:
    return EditarUsuario(repo)


def obtener_caso_uso_desactivar_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> DesactivarUsuario:
    return DesactivarUsuario(repo)


def obtener_caso_uso_reactivar_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ReactivarUsuario:
    return ReactivarUsuario(repo)


def obtener_caso_uso_asignar_consultor(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> AsignarConsultor:
    return AsignarConsultor(repo_usuario, repo_empresa)


def obtener_repositorio_rol(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoRol:
    return RepositorioMongoRol(db)


def obtener_repositorio_permiso(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoPermiso:
    return RepositorioMongoPermiso(db)


def obtener_caso_uso_listar_roles(
    repo: RepositorioMongoRol = Depends(obtener_repositorio_rol),
) -> ListarRoles:
    return ListarRoles(repo)


def obtener_caso_uso_listar_permisos(
    repo: RepositorioMongoPermiso = Depends(obtener_repositorio_permiso),
) -> ListarPermisos:
    return ListarPermisos(repo)


def obtener_caso_uso_agregar_permiso(
    repo_rol: RepositorioMongoRol = Depends(obtener_repositorio_rol),
    repo_permiso: RepositorioMongoPermiso = Depends(obtener_repositorio_permiso),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> AgregarPermisoARol:
    return AgregarPermisoARol(repo_rol, repo_permiso, repo_usuario, repo_sesion)


def obtener_caso_uso_quitar_permiso(
    repo_rol: RepositorioMongoRol = Depends(obtener_repositorio_rol),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> QuitarPermisoDeRol:
    return QuitarPermisoDeRol(repo_rol, repo_usuario, repo_sesion)


def obtener_repositorio_auditoria(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoAuditoria:
    return RepositorioMongoAuditoria(db)


def obtener_caso_uso_consultar_auditoria(
    repo: RepositorioMongoAuditoria = Depends(obtener_repositorio_auditoria),
) -> ConsultarAuditoria:
    return ConsultarAuditoria(repo)


from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarDimension, AgregarPregunta, ConsultarModelo, CrearModeloMadurez,
    EditarDimension, EditarPregunta, ListarModelos, QuitarDimension,
    QuitarPregunta)
from src.infraestructura.persistencia.repositorio_mongo_modelo_madurez import \
    RepositorioMongoModeloMadurez


def obtener_repositorio_modelo_madurez(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoModeloMadurez:
    return RepositorioMongoModeloMadurez(db)


def obtener_caso_uso_crear_modelo_madurez(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> CrearModeloMadurez:
    return CrearModeloMadurez(repo)


def obtener_caso_uso_listar_modelos(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> ListarModelos:
    return ListarModelos(repo)


def obtener_caso_uso_consultar_modelo(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> ConsultarModelo:
    return ConsultarModelo(repo)


def obtener_caso_uso_agregar_dimension(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> AgregarDimension:
    return AgregarDimension(repo)


def obtener_caso_uso_editar_dimension(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> EditarDimension:
    return EditarDimension(repo)


def obtener_caso_uso_quitar_dimension(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> QuitarDimension:
    return QuitarDimension(repo)


def obtener_caso_uso_agregar_pregunta(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> AgregarPregunta:
    return AgregarPregunta(repo)


def obtener_caso_uso_editar_pregunta(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> EditarPregunta:
    return EditarPregunta(repo)


def obtener_caso_uso_quitar_pregunta(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> QuitarPregunta:
    return QuitarPregunta(repo)
