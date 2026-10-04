from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudYaResuelta)
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.dominio.puertos.servicio_correo import ServicioCorreo


class SolicitudNoEncontrada(Exception):
    pass


class ResolverSolicitud:
    def __init__(
        self,
        repo_solicitud: RepositorioSolicitud,
        repo_empresa: RepositorioEmpresa,
        repo_token: RepositorioToken,
        servicio_correo: ServicioCorreo,
        repo_notificacion: RepositorioNotificacion,
    ):
        self._solicitudes = repo_solicitud
        self._empresas = repo_empresa
        self._tokens = repo_token
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion

    async def aprobar(self, solicitud_id: str, sector: Sector) -> tuple[Empresa, str]:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()

        if solicitud.estado != EstadoSolicitud.PENDIENTE:
            # antes de crear nada: una solicitud resuelta no deja una empresa huerfana
            raise SolicitudYaResuelta("La solicitud ya fue resuelta")

        empresa = Empresa(id=None, nombre=solicitud.nombre_empresa, sector=sector)
        empresa = await self._empresas.guardar(empresa)

        solicitud.aprobar(empresa_id=empresa.id)
        await self._solicitudes.actualizar(solicitud)

        codigo = TokenVerificacion.generar_codigo()
        token = TokenVerificacion(
            id=None,
            tipo=TipoToken.INVITACION,
            correo_destino=solicitud.correo_solicitante,
            solicitud_id=solicitud.id,
        )
        await self._tokens.guardar(token, codigo)

        await enviar_notificacion(
            self._correo,
            self._notificaciones,
            usuario_id=None,
            correo_destino=solicitud.correo_solicitante,
            tipo="invitacion",
            asunto="Trust 4P - Invitación para completar tu registro",
            contenido=(
                f"Hola {solicitud.nombre_solicitante},\n\n"
                f"Tu solicitud de acceso para {empresa.nombre} fue aprobada. "
                f"Usa el siguiente código para completar tu registro: {codigo}"
            ),
        )

        return (
            empresa,
            codigo,
        )  # el código en claro se devuelve UNA SOLA VEZ, para trazabilidad del llamador

    async def rechazar(self, solicitud_id: str, motivo: str) -> None:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()
        solicitud.rechazar(motivo=motivo)
        await self._solicitudes.actualizar(solicitud)

        await enviar_notificacion(
            self._correo,
            self._notificaciones,
            usuario_id=None,
            correo_destino=solicitud.correo_solicitante,
            tipo="solicitud_rechazada",
            asunto="Trust 4P - Respuesta a tu solicitud de acceso",
            contenido=(
                f"Hola {solicitud.nombre_solicitante},\n\n"
                f"Tu solicitud de acceso para {solicitud.nombre_empresa} no fue aprobada.\n"
                f"Motivo: {motivo}"
            ),
        )
