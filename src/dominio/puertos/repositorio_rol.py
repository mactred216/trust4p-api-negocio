from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.rol import RolCatalogo


class RepositorioRol(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-002)."""

    @abstractmethod
    async def guardar(self, rol: RolCatalogo) -> RolCatalogo: ...

    @abstractmethod
    async def obtener_por_codigo(self, codigo: str) -> Optional[RolCatalogo]: ...

    @abstractmethod
    async def actualizar(self, rol: RolCatalogo) -> None: ...

    @abstractmethod
    async def listar_activos(self) -> list[RolCatalogo]: ...
