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
                                                         DesbloquearUsuario,
                                                         EditarUsuario,
                                                         ListarUsuarios,
                                                         ReactivarUsuario)
from src.aplicacion.casos_uso.iniciar_sesion import (
    BloqueoCorreosDesconocidos, IniciarSesion)
from src.aplicacion.casos_uso.radicar_solicitud import RadicarSolicitud
from src.aplicacion.casos_uso.resolver_solicitud import ResolverSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.infraestructura.clientes.cliente_correo_smtp import ClienteCorreoSMTP
from src.infraestructura.persistencia.conexion import obtener_base_datos
from src.infraestructura.persistencia.repositorio_mongo_empresa import \
    RepositorioMongoEmpresa
from src.infraestructura.persistencia.repositorio_mongo_notificacion import \
    RepositorioMongoNotificacion
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

# Estado en memoria compartido entre peticiones (HU-004 CA-02).
BLOQUEO_CORREOS_DESCONOCIDOS = BloqueoCorreosDesconocidos()


def obtener_repositorio_solicitud(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSolicitud:
    return RepositorioMongoSolicitud(db)


def obtener_servicio_correo() -> ClienteCorreoSMTP:
    return ClienteCorreoSMTP()


def obtener_repositorio_notificacion(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoNotificacion:
    return RepositorioMongoNotificacion(db)


def obtener_repositorio_usuario(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoUsuario:
    return RepositorioMongoUsuario(db)


def obtener_repositorio_sesion(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSesion:
    return RepositorioMongoSesion(db)


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
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> EditarUsuario:
    return EditarUsuario(repo, repo_empresa)


def obtener_caso_uso_desactivar_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> DesactivarUsuario:
    return DesactivarUsuario(repo)


def obtener_caso_uso_reactivar_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ReactivarUsuario:
    return ReactivarUsuario(repo)


def obtener_caso_uso_desbloquear_usuario(
    repo: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> DesbloquearUsuario:
    return DesbloquearUsuario(repo)


from src.aplicacion.casos_uso.gestionar_perfil import (ActualizarPerfil,
                                                       CambiarContrasena,
                                                       CerrarSesion,
                                                       EliminarDatosPersonales)


def obtener_caso_uso_cerrar_sesion(
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> CerrarSesion:
    return CerrarSesion(repo_sesion)


def obtener_caso_uso_actualizar_perfil(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ActualizarPerfil:
    return ActualizarPerfil(repo_usuario)


def obtener_caso_uso_cambiar_contrasena(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> CambiarContrasena:
    return CambiarContrasena(repo_usuario, repo_sesion)


def obtener_caso_uso_eliminar_datos_personales(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
) -> EliminarDatosPersonales:
    return EliminarDatosPersonales(repo_usuario, repo_sesion, servicio_correo)


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
    AgregarDimension, AgregarEjePerfilCultural, AgregarNivel, AgregarPregunta,
    ConsultarModelo, CrearModeloMadurez, CrearNuevaVersion, DesactivarPregunta,
    EditarDimension, EditarEjePerfilCultural, EditarNivel, EditarPregunta,
    ListarModelos, ObtenerVersionVigente, Publicar, QuitarDimension,
    QuitarEjePerfilCultural, QuitarNivel, ReactivarPregunta)
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


def obtener_caso_uso_desactivar_pregunta(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> DesactivarPregunta:
    return DesactivarPregunta(repo)


def obtener_caso_uso_reactivar_pregunta(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> ReactivarPregunta:
    return ReactivarPregunta(repo)


def obtener_caso_uso_agregar_nivel(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> AgregarNivel:
    return AgregarNivel(repo)


def obtener_caso_uso_editar_nivel(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> EditarNivel:
    return EditarNivel(repo)


def obtener_caso_uso_quitar_nivel(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> QuitarNivel:
    return QuitarNivel(repo)


def obtener_caso_uso_agregar_eje_perfil_cultural(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> AgregarEjePerfilCultural:
    return AgregarEjePerfilCultural(repo)


def obtener_caso_uso_editar_eje_perfil_cultural(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> EditarEjePerfilCultural:
    return EditarEjePerfilCultural(repo)


def obtener_caso_uso_quitar_eje_perfil_cultural(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> QuitarEjePerfilCultural:
    return QuitarEjePerfilCultural(repo)


def obtener_caso_uso_publicar_modelo(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> Publicar:
    return Publicar(repo)


def obtener_caso_uso_crear_nueva_version(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> CrearNuevaVersion:
    return CrearNuevaVersion(repo)


def obtener_caso_uso_obtener_version_vigente(
    repo: RepositorioMongoModeloMadurez = Depends(obtener_repositorio_modelo_madurez),
) -> ObtenerVersionVigente:
    return ObtenerVersionVigente(repo)


from src.aplicacion.casos_uso.gestionar_diagnostico import (
    CerrarDiagnostico, CompletarDiagnostico, ConsultarDiagnostico,
    GuardarRespuesta, IniciarDiagnostico, ListarDiagnosticosDeEmpresa,
    ObtenerCuestionario, ObtenerDiagnosticoEnCurso)
from src.infraestructura.persistencia.repositorio_mongo_diagnostico import \
    RepositorioMongoDiagnostico


def obtener_repositorio_diagnostico(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoDiagnostico:
    return RepositorioMongoDiagnostico(db)


def obtener_caso_uso_iniciar_diagnostico(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_modelo_madurez: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> IniciarDiagnostico:
    return IniciarDiagnostico(
        repo_diagnostico, repo_usuario, repo_empresa, repo_modelo_madurez
    )


def obtener_caso_uso_guardar_respuesta(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_modelo_madurez: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> GuardarRespuesta:
    return GuardarRespuesta(repo_diagnostico, repo_usuario, repo_modelo_madurez)


def obtener_caso_uso_diagnostico_en_curso(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ObtenerDiagnosticoEnCurso:
    return ObtenerDiagnosticoEnCurso(repo_diagnostico, repo_usuario)


def obtener_caso_uso_consultar_diagnostico(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ConsultarDiagnostico:
    return ConsultarDiagnostico(repo_diagnostico, repo_usuario)


def obtener_caso_uso_obtener_cuestionario(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_modelo_madurez: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> ObtenerCuestionario:
    return ObtenerCuestionario(repo_diagnostico, repo_usuario, repo_modelo_madurez)


def obtener_caso_uso_completar_diagnostico(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_modelo: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> CompletarDiagnostico:
    return CompletarDiagnostico(repo_diagnostico, repo_usuario, repo_modelo)


def obtener_caso_uso_listar_diagnosticos_empresa(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ListarDiagnosticosDeEmpresa:
    return ListarDiagnosticosDeEmpresa(repo_diagnostico, repo_usuario)


def obtener_caso_uso_cerrar_diagnostico(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> CerrarDiagnostico:
    return CerrarDiagnostico(repo_diagnostico, repo_usuario)


from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.infraestructura.clientes.cliente_servicio_agente_http import \
    ClienteServicioAgenteHTTP


def obtener_cliente_servicio_agente() -> ClienteServicioAgenteHTTP:
    return ClienteServicioAgenteHTTP()


def obtener_caso_uso_evaluar_diagnostico(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_modelo_madurez: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
    cliente_agente: ClienteServicioAgenteHTTP = Depends(
        obtener_cliente_servicio_agente
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
    repo_notificacion: RepositorioMongoNotificacion = Depends(
        obtener_repositorio_notificacion
    ),
) -> EvaluarDiagnostico:
    return EvaluarDiagnostico(
        repo_diagnostico,
        repo_modelo_madurez,
        cliente_agente,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
    )


from src.aplicacion.casos_uso.consultar_evolucion import \
    ConsultarEvolucionDiagnosticos
from src.aplicacion.casos_uso.generar_informe import GenerarInformeDiagnostico


def obtener_caso_uso_generar_informe(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> GenerarInformeDiagnostico:
    return GenerarInformeDiagnostico(repo_diagnostico, repo_usuario)


def obtener_caso_uso_consultar_evolucion(
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
) -> ConsultarEvolucionDiagnosticos:
    return ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)


from src.aplicacion.casos_uso.gestionar_consultoria import (
    ConsultarDiagnosticoAsignado, ListarDiagnosticosDeEmpresaAsignada,
    ListarEmpresasAsignadas, RegistrarRecomendacion)


def obtener_caso_uso_listar_empresas_asignadas(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> ListarEmpresasAsignadas:
    return ListarEmpresasAsignadas(repo_usuario, repo_empresa, repo_diagnostico)


def obtener_caso_uso_listar_diagnosticos_empresa_asignada(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> ListarDiagnosticosDeEmpresaAsignada:
    return ListarDiagnosticosDeEmpresaAsignada(repo_usuario, repo_diagnostico)


def obtener_caso_uso_consultar_diagnostico_asignado(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> ConsultarDiagnosticoAsignado:
    return ConsultarDiagnosticoAsignado(repo_usuario, repo_diagnostico)


def obtener_caso_uso_registrar_recomendacion(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
    repo_notificacion: RepositorioMongoNotificacion = Depends(
        obtener_repositorio_notificacion
    ),
) -> RegistrarRecomendacion:
    return RegistrarRecomendacion(
        repo_usuario, repo_diagnostico, servicio_correo, repo_notificacion
    )


from src.aplicacion.casos_uso.gestionar_indicadores import (  # noqa: E402
    ConsultarIndicadoresAgregados, ExportarDatosAgregados)


def obtener_caso_uso_consultar_indicadores(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> ConsultarIndicadoresAgregados:
    return ConsultarIndicadoresAgregados(repo_usuario, repo_empresa, repo_diagnostico)


def obtener_caso_uso_exportar_datos_agregados(
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> ExportarDatosAgregados:
    return ExportarDatosAgregados(repo_empresa, repo_diagnostico)


from src.aplicacion.casos_uso.simular_pesos import \
    SimularPesosModelo  # noqa: E402


def obtener_caso_uso_simular_pesos(
    repo_modelo: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> SimularPesosModelo:
    return SimularPesosModelo(repo_modelo, repo_diagnostico)


from src.aplicacion.casos_uso.diagnostico_demo import (  # noqa: E402
    CalcularResultadoDemo, ObtenerPreguntasDemo)


def obtener_caso_uso_obtener_preguntas_demo(
    repo_modelo: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> ObtenerPreguntasDemo:
    return ObtenerPreguntasDemo(repo_modelo)


def obtener_caso_uso_calcular_resultado_demo(
    repo_modelo: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> CalcularResultadoDemo:
    return CalcularResultadoDemo(repo_modelo)


def obtener_caso_uso_iniciar_sesion(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
    repo_rol: RepositorioMongoRol = Depends(obtener_repositorio_rol),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
) -> IniciarSesion:
    return IniciarSesion(
        repo_usuario,
        repo_sesion,
        repo_rol,
        repo_empresa,
        BLOQUEO_CORREOS_DESCONOCIDOS,
        repo_auditoria,
    )


from src.aplicacion.casos_uso.gestionar_empresas import \
    CrearEmpresa  # noqa: E402
from src.aplicacion.casos_uso.gestionar_usuarios import \
    CrearUsuario  # noqa: E402


def obtener_caso_uso_crear_empresa(
    repo: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> CrearEmpresa:
    return CrearEmpresa(repo)


def obtener_caso_uso_crear_usuario(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
    repo_notificacion: RepositorioMongoNotificacion = Depends(
        obtener_repositorio_notificacion
    ),
) -> CrearUsuario:
    return CrearUsuario(
        repo_usuario, repo_empresa, repo_token, servicio_correo, repo_notificacion
    )


def obtener_caso_uso_restablecer_contrasena(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
) -> RestablecerContrasena:
    return RestablecerContrasena(repo_usuario, repo_token, repo_sesion, repo_auditoria)


from src.aplicacion.casos_uso.consultar_solicitudes import (  # noqa: E402
    ConsultarSolicitud, ListarSolicitudes)
from src.infraestructura.persistencia.repositorio_mongo_sector import \
    RepositorioMongoSector  # noqa: E402


def obtener_repositorio_sector(
    db: AsyncIOMotorDatabase = Depends(obtener_base_datos),
) -> RepositorioMongoSector:
    return RepositorioMongoSector(db)


def obtener_caso_uso_radicar_solicitud(
    repo: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
    repo_notificacion: RepositorioMongoNotificacion = Depends(
        obtener_repositorio_notificacion
    ),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_sector: RepositorioMongoSector = Depends(obtener_repositorio_sector),
) -> RadicarSolicitud:
    return RadicarSolicitud(
        repo,
        repo_usuario,
        servicio_correo,
        repo_notificacion,
        repo_empresa,
        repo_sector,
    )


def obtener_caso_uso_resolver_solicitud(
    repo_solicitud: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    servicio_correo: ClienteCorreoSMTP = Depends(obtener_servicio_correo),
    repo_notificacion: RepositorioMongoNotificacion = Depends(
        obtener_repositorio_notificacion
    ),
    repo_sector: RepositorioMongoSector = Depends(obtener_repositorio_sector),
) -> ResolverSolicitud:
    return ResolverSolicitud(
        repo_solicitud,
        repo_empresa,
        repo_token,
        servicio_correo,
        repo_notificacion,
        repo_sector,
    )


def obtener_caso_uso_listar_solicitudes(
    repo: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
) -> ListarSolicitudes:
    return ListarSolicitudes(repo)


def obtener_caso_uso_consultar_solicitud(
    repo: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
) -> ConsultarSolicitud:
    return ConsultarSolicitud(repo)


from src.aplicacion.casos_uso.completar_registro import \
    ConsultarInvitacion  # noqa: E402


def obtener_caso_uso_consultar_invitacion(
    repo_token: RepositorioMongoToken = Depends(obtener_repositorio_token),
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_solicitud: RepositorioMongoSolicitud = Depends(obtener_repositorio_solicitud),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
) -> ConsultarInvitacion:
    return ConsultarInvitacion(repo_token, repo_usuario, repo_solicitud, repo_empresa)


from src.aplicacion.casos_uso.gestionar_consultoria import \
    ObtenerCuestionarioAsignado  # noqa: E402


def obtener_caso_uso_obtener_cuestionario_asignado(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
    repo_modelo_madurez: RepositorioMongoModeloMadurez = Depends(
        obtener_repositorio_modelo_madurez
    ),
) -> ObtenerCuestionarioAsignado:
    return ObtenerCuestionarioAsignado(
        repo_usuario, repo_diagnostico, repo_modelo_madurez
    )


from src.aplicacion.casos_uso.gestionar_reportes import (  # noqa: E402
    GenerarInformeDeEmpresa, ListarEmpresasParaReporte)


def obtener_caso_uso_listar_empresas_para_reporte(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_empresa: RepositorioMongoEmpresa = Depends(obtener_repositorio_empresa),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> ListarEmpresasParaReporte:
    return ListarEmpresasParaReporte(repo_usuario, repo_empresa, repo_diagnostico)


def obtener_caso_uso_generar_informe_de_empresa(
    repo_usuario: RepositorioMongoUsuario = Depends(obtener_repositorio_usuario),
    repo_diagnostico: RepositorioMongoDiagnostico = Depends(
        obtener_repositorio_diagnostico
    ),
) -> GenerarInformeDeEmpresa:
    return GenerarInformeDeEmpresa(repo_usuario, repo_diagnostico)
