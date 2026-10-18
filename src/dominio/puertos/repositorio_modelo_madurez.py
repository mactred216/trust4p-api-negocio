from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.modelo_madurez import ModeloMadurez


class RepositorioModeloMadurez(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-011)."""

    @abstractmethod
    async def guardar(self, modelo: ModeloMadurez) -> ModeloMadurez: ...

    @abstractmethod
    async def obtener_por_id(self, modelo_id: str) -> Optional[ModeloMadurez]: ...

    @abstractmethod
    async def obtener_por_version(self, version: str) -> Optional[ModeloMadurez]: ...

    @abstractmethod
    async def obtener_vigente(self) -> Optional[ModeloMadurez]:
        """RF-33: la versión publicada más reciente (índice publicado + publicado_en)."""
        ...

    @abstractmethod
    async def actualizar(self, modelo: ModeloMadurez) -> None: ...

    @abstractmethod
    async def listar(self) -> list[ModeloMadurez]: ...
