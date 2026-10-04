from datetime import datetime, timezone
from typing import Optional

from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.solicitud_acceso import SolicitudAcceso
from src.dominio.entidades.usuario import VERSION_POLITICA_TRATAMIENTO_DATOS
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.repositorio_sector import RepositorioSector
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.puertos.servicio_correo import ServicioCorreo


class SolicitudDuplicada(Exception):
    """RF-01: el visitante ya tiene una solicitud pendiente, una cuenta o su
    empresa ya está registrada (mismo correo o mismo NIT)."""

    pass


class SectorInvalido(ValueError):
    pass


class RadicarSolicitud:
    def __init__(
        self,
        repositorio: RepositorioSolicitud,
        repo_usuario: Optional[RepositorioUsuario] = None,
        servicio_correo: Optional[ServicioCorreo] = None,
        repo_notificacion: Optional[RepositorioNotificacion] = None,
        repo_empresa: Optional[RepositorioEmpresa] = None,
        repo_sector: Optional[RepositorioSector] = None,
    ):
        self._solicitudes = repositorio
        self._usuarios = repo_usuario
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion
        self._empresas = repo_empresa
        self._sectores = repo_sector

    async def ejecutar(
        self,
        nombre_empresa: str,
        correo_solicitante: str,
        nombre_solicitante: str,
        nit: Optional[str] = None,
        sector_codigo: Optional[str] = None,
        numero_empleados: Optional[int] = None,
        ciudad: Optional[str] = None,
        cargo: Optional[str] = None,
        telefono: Optional[str] = None,
        acepto_tratamiento: bool = False,
    ) -> SolicitudAcceso:
        await self._verificar_duplicidad(correo_solicitante, nit)

        sector_nombre = None
        if sector_codigo is not None and self._sectores is not None:
            sector = await self._sectores.obtener_por_codigo(sector_codigo)
            if sector is None:
                raise SectorInvalido("El sector indicado no existe")
            sector_nombre = sector.nombre

        solicitud = SolicitudAcceso(
            id=None,
            nombre_empresa=nombre_empresa,
            correo_solicitante=correo_solicitante,
            nombre_solicitante=nombre_solicitante,
            nit=nit,
            sector_codigo=sector_codigo,
            sector_nombre=sector_nombre,
            numero_empleados=numero_empleados,
            ciudad=ciudad,
            cargo=cargo,
            telefono=telefono,
            acepto_tratamiento_en=(
                datetime.now(timezone.utc) if acepto_tratamiento else None
            ),
            version_politica_aceptada=(
                VERSION_POLITICA_TRATAMIENTO_DATOS if acepto_tratamiento else None
            ),
        )
        solicitud = await self._solicitudes.guardar(solicitud)
        await self._notificar_administradores(solicitud)
        return solicitud

    async def _verificar_duplicidad(self, correo: str, nit: Optional[str]) -> None:
        if await self._solicitudes.existe_pendiente_con_correo(correo):
            raise SolicitudDuplicada()
        if self._usuarios is not None:
            if await self._usuarios.obtener_por_correo(correo) is not None:
                raise SolicitudDuplicada()
        if nit is not None:
            if await self._solicitudes.existe_pendiente_con_nit(nit):
                raise SolicitudDuplicada()
            if self._empresas is not None:
                if await self._empresas.obtener_por_nit(nit) is not None:
                    raise SolicitudDuplicada()

    async def _notificar_administradores(self, solicitud: SolicitudAcceso) -> None:
        """RF-01 paso 5 / RF-46: avisa a los administradores activos de la nueva
        solicitud. Un fallo de correo no impide radicarla (enviar_notificacion
        no propaga el error y lo deja en la bitacora de notificaciones)."""
        if (
            self._usuarios is None
            or self._correo is None
            or self._notificaciones is None
        ):
            return
        for administrador in await self._usuarios.listar_por_rol("administrador"):
            if not administrador.activo or administrador.registro_pendiente:
                continue
            await enviar_notificacion(
                self._correo,
                self._notificaciones,
                usuario_id=administrador.id,
                correo_destino=administrador.correo,
                tipo="solicitud_nueva",
                asunto="Trust 4P - Nueva solicitud de acceso",
                contenido=(
                    f"Hola {administrador.nombres},\n\n"
                    f"{solicitud.nombre_solicitante} radico una solicitud de acceso para "
                    f"{solicitud.nombre_empresa}. Ingrese a la plataforma para revisarla."
                ),
            )
