from abc import ABC, abstractmethod

from src.dominio.entidades.registro_auditoria import RegistroAuditoria


class RepositorioAuditoria(ABC):
    """Puerto del dominio. Colección de solo anexado (ADR): nunca se actualiza ni elimina."""

    @abstractmethod
    async def registrar(self, registro: RegistroAuditoria) -> None: ...

    @abstractmethod
    async def listar(
        self,
        entidad: str = None,
        entidad_id: str = None,
        usuario_id: str = None,
        limite: int = 50,
        usuario_ids: list[str] | None = None,
    ) -> list[RegistroAuditoria]: ...
