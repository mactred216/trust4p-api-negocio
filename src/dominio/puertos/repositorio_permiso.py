from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.permiso import Permiso


class RepositorioPermiso(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-011)."""

    @abstractmethod
    async def guardar(self, permiso: Permiso) -> Permiso: ...

    @abstractmethod
    async def obtener_por_codigo(self, codigo: str) -> Optional[Permiso]: ...

    @abstractmethod
    async def listar_activos(self) -> list[Permiso]: ...
