from typing import Optional

from src.aplicacion.servicios.enlaces import enlace_frontend
from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudYaResuelta)
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.repositorio_sector import RepositorioSector
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
        repo_sector: Optional[RepositorioSector] = None,
    ):
        self._sectores = repo_sector
        self._solicitudes = repo_solicitud
        self._empresas = repo_empresa
        self._tokens = repo_token
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion

    async def aprobar(
        self, solicitud_id: str, sector: Optional[Sector] = None
    ) -> tuple[Empresa, str]:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()

        if solicitud.estado != EstadoSolicitud.PENDIENTE:
            # antes de crear nada: una solicitud resuelta no deja una empresa huerfana
            raise SolicitudYaResuelta("La solicitud ya fue resuelta")

        if sector is None:
            sector = await self._sector_de(solicitud)

        empresa = Empresa(
            id=None,
            nombre=solicitud.nombre_empresa,
            sector=sector,
            nit=solicitud.nit,
            numero_empleados=solicitud.numero_empleados,
            ciudad=solicitud.ciudad,
        )
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
                f"Completa tu registro en este enlace: {enlace_frontend('/registro', codigo)}\n\n"
                f"Si prefieres ingresarlo manualmente, tu código es: {codigo}"
            ),
        )

        return (
            empresa,
            codigo,
        )  # el código en claro se devuelve UNA SOLA VEZ, para trazabilidad del llamador

    async def _sector_de(self, solicitud) -> Sector:
        """RF-02: el sector sale de lo que declaro el solicitante (catalogo)."""
        if self._sectores is None or not solicitud.sector_codigo:
            raise ValueError(
                "La solicitud no declara un sector; indiquelo al aprobarla"
            )
        sector = await self._sectores.obtener_por_codigo(solicitud.sector_codigo)
        if sector is None:
            raise ValueError("El sector de la solicitud ya no existe en el catalogo")
        return sector

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
