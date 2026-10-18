from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.empresa import Empresa


class RepositorioEmpresa(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-011)."""

    @abstractmethod
    async def guardar(self, empresa: Empresa) -> Empresa: ...

    @abstractmethod
    async def obtener_por_id(self, empresa_id: str) -> Optional[Empresa]: ...

    @abstractmethod
    async def actualizar(self, empresa: Empresa) -> None: ...

    @abstractmethod
    async def listar_activas(self) -> list[Empresa]: ...

    @abstractmethod
    async def listar_todas(self) -> list[Empresa]: ...

    @abstractmethod
    async def obtener_por_nit(self, nit: str) -> Optional[Empresa]: ...
