from dataclasses import dataclass
from typing import Optional

from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


@dataclass
class EntradaBitacora:
    """Un registro de la bitácora con la identidad legible de quien actuó. El
    nombre y el correo se resuelven al consultar (la bitácora solo guarda el id),
    así que reflejan el estado actual del usuario; el correo es único."""

    registro: RegistroAuditoria
    usuario_nombre: Optional[str] = None
    usuario_correo: Optional[str] = None


class ConsultarAuditoria:
    def __init__(
        self,
        repo: RepositorioAuditoria,
        repo_usuario: Optional[RepositorioUsuario] = None,
    ):
        self._auditoria = repo
        self._usuarios = repo_usuario

    async def ejecutar(
        self,
        entidad: Optional[str] = None,
        entidad_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        limite: int = 50,
        usuario: Optional[str] = None,
    ) -> list[EntradaBitacora]:
        """`usuario` es un texto libre (nombre o correo, completo o parcial) para
        filtrar por quien ejecutó la acción; si nadie coincide, no hay registros
        (no se ignora el filtro)."""
        usuario_ids = None
        texto = (usuario or "").strip()
        if texto and self._usuarios is not None:
            coincidencias = await self._usuarios.buscar(texto)
            if not coincidencias:
                return []
            usuario_ids = [u.id for u in coincidencias]

        registros = await self._auditoria.listar(
            entidad=entidad,
            entidad_id=entidad_id,
            usuario_id=usuario_id,
            limite=limite,
            usuario_ids=usuario_ids,
        )

        identidades = {}
        ids = {r.usuario_id for r in registros if r.usuario_id}
        if ids and self._usuarios is not None:
            identidades = {u.id: u for u in await self._usuarios.listar_por_ids(list(ids))}
        return [
            EntradaBitacora(
                registro=r,
                usuario_nombre=(
                    f"{identidades[r.usuario_id].nombres} {identidades[r.usuario_id].apellidos}".strip()
                    if r.usuario_id in identidades
                    else None
                ),
                usuario_correo=(
                    identidades[r.usuario_id].correo if r.usuario_id in identidades else None
                ),
            )
            for r in registros
        ]
