from typing import Optional

from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria


class ConsultarAuditoria:
    def __init__(self, repo: RepositorioAuditoria):
        self._auditoria = repo

    async def ejecutar(
        self,
        entidad: Optional[str] = None,
        entidad_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        limite: int = 50,
    ) -> list[RegistroAuditoria]:
        return await self._auditoria.listar(
            entidad=entidad, entidad_id=entidad_id, usuario_id=usuario_id, limite=limite
        )
