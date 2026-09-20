from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.usuario import Usuario


class RepositorioSesion(ABC):
    """Puerto del dominio. Sesión con estado, no JWT (ADR de seguridad, RNF revocación)."""

    @abstractmethod
    async def crear(self, usuario: Usuario) -> str:
        """Crea la sesión y devuelve el token que se entrega al cliente."""
        ...

    @abstractmethod
    async def obtener_usuario_id_por_token(self, token: str) -> Optional[str]: ...

    @abstractmethod
    async def obtener_sesion_por_token(self, token: str) -> Optional[dict]:
        """Devuelve la sesión completa (incluye rol_codigo) para verificación de autorización."""
        ...

    @abstractmethod
    async def revocar(self, token: str) -> None: ...

    @abstractmethod
    async def revocar_todas_de_usuario(self, usuario_id: str) -> None: ...
