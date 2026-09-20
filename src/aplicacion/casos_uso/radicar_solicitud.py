from src.dominio.entidades.solicitud_acceso import SolicitudAcceso
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud


class SolicitudDuplicada(Exception):
    """Ya existe una solicitud pendiente con este correo (RF-01)."""

    pass


class RadicarSolicitud:
    def __init__(self, repositorio: RepositorioSolicitud):
        self._solicitudes = repositorio

    async def ejecutar(
        self,
        nombre_empresa: str,
        correo_solicitante: str,
        nombre_solicitante: str,
    ) -> SolicitudAcceso:
        ya_existe = await self._solicitudes.existe_pendiente_con_correo(
            correo_solicitante
        )
        if ya_existe:
            raise SolicitudDuplicada()

        solicitud = SolicitudAcceso(
            id=None,
            nombre_empresa=nombre_empresa,
            correo_solicitante=correo_solicitante,
            nombre_solicitante=nombre_solicitante,
        )

        return await self._solicitudes.guardar(solicitud)
