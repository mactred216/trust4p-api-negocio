from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.token_verificacion import TokenVerificacion


class RepositorioToken(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-002)."""

    @abstractmethod
    async def guardar(
        self, token: TokenVerificacion, codigo: str
    ) -> TokenVerificacion: ...

    @abstractmethod
    async def obtener_por_codigo(self, codigo: str) -> Optional[TokenVerificacion]: ...

    @abstractmethod
    async def actualizar(self, token: TokenVerificacion) -> None: ...
