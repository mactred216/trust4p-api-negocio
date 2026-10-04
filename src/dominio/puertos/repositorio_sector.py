from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.empresa import Sector


class RepositorioSector(ABC):
    """Puerto del dominio: catálogo sectorial (Diccionario de Datos, colección
    sectores)."""

    @abstractmethod
    async def obtener_por_codigo(self, codigo: str) -> Optional[Sector]: ...

    @abstractmethod
    async def listar_activos(self) -> list[Sector]: ...
