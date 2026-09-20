from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.solicitud_acceso import SolicitudAcceso


class RepositorioSolicitud(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-002)."""

    @abstractmethod
    async def guardar(self, solicitud: SolicitudAcceso) -> SolicitudAcceso: ...

    @abstractmethod
    async def obtener_por_id(self, solicitud_id: str) -> Optional[SolicitudAcceso]: ...

    @abstractmethod
    async def existe_pendiente_con_correo(self, correo: str) -> bool:
        """Regla de negocio: evita solicitudes duplicadas del mismo correo."""
        ...

    @abstractmethod
    async def actualizar(self, solicitud: SolicitudAcceso) -> None: ...

    @abstractmethod
    async def listar_pendientes(self) -> list[SolicitudAcceso]: ...
