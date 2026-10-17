from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.diagnostico import Diagnostico


class RepositorioDiagnostico(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-011)."""

    @abstractmethod
    async def guardar(self, diagnostico: Diagnostico) -> Diagnostico: ...

    @abstractmethod
    async def obtener_por_id(self, diagnostico_id: str) -> Optional[Diagnostico]: ...

    @abstractmethod
    async def actualizar(self, diagnostico: Diagnostico) -> None: ...

    @abstractmethod
    async def obtener_en_curso_por_empresa(
        self, empresa_id: str
    ) -> Optional[Diagnostico]:
        """R-05: a lo sumo un diagnóstico sin cerrar por empresa."""
        ...

    @abstractmethod
    async def contar_por_empresa(self, empresa_id: str) -> int:
        """RF-12 (dictionary): base para asignar el siguiente consecutivo."""
        ...

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: str) -> list[Diagnostico]: ...

    @abstractmethod
    async def listar_por_modelo_version(self, modelo_version: str) -> list[Diagnostico]:
        """RF-35: diagnósticos históricos calculados con una versión del modelo."""
        ...
