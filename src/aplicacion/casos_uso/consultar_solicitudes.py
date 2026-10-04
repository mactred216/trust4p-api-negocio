from typing import Optional

from src.aplicacion.casos_uso.resolver_solicitud import SolicitudNoEncontrada
from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudAcceso)
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud


class ListarSolicitudes:
    """RF-02 paso 1: bandeja del administrador, con filtro opcional por estado."""

    def __init__(self, repo: RepositorioSolicitud):
        self._solicitudes = repo

    async def ejecutar(self, estado: Optional[str] = None) -> list[SolicitudAcceso]:
        if estado is not None and estado not in {e.value for e in EstadoSolicitud}:
            raise ValueError("Estado inválido; use pendiente, aprobada o rechazada")
        return await self._solicitudes.listar(estado)


class ConsultarSolicitud:
    """RF-02 paso 2: detalle completo de lo que envió el visitante."""

    def __init__(self, repo: RepositorioSolicitud):
        self._solicitudes = repo

    async def ejecutar(self, solicitud_id: str) -> SolicitudAcceso:
        solicitud = await self._solicitudes.obtener_por_id(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada()
        return solicitud
