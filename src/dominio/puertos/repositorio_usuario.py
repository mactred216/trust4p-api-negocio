from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.usuario import Usuario


class RepositorioUsuario(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-002)."""

    @abstractmethod
    async def obtener_por_correo(self, correo: str) -> Optional[Usuario]: ...

    @abstractmethod
    async def guardar(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    async def actualizar(self, usuario: Usuario) -> None: ...

    @abstractmethod
    async def obtener_por_id(self, usuario_id: str) -> Optional[Usuario]: ...

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: str) -> list[Usuario]: ...

    @abstractmethod
    async def listar_todos(self) -> list[Usuario]: ...

    @abstractmethod
    async def listar_por_rol(self, codigo_rol: str) -> list[Usuario]: ...

    @abstractmethod
    async def listar_por_ids(self, ids: list[str]) -> list[Usuario]:
        """Los usuarios con esos ids, activos o no (para rotular la bitácora)."""

    @abstractmethod
    async def buscar(self, texto: str, limite: int = 200) -> list[Usuario]:
        """Usuarios, activos o no, cuyo nombre, apellido o correo contienen
        cada palabra del texto (sin distinguir mayúsculas)."""
