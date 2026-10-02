from abc import ABC, abstractmethod

from src.dominio.entidades.notificacion import Notificacion


class RepositorioNotificacion(ABC):
    """Puerto del dominio (ADR-002). Colección de solo anexado: no expone
    actualización ni eliminación."""

    @abstractmethod
    async def registrar(self, notificacion: Notificacion) -> Notificacion: ...
