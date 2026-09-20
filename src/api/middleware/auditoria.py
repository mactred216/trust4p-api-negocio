from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria


async def registrar_accion(
    repo_auditoria: RepositorioAuditoria,
    usuario_id: str | None,
    entidad: str,
    entidad_id: str | None,
    accion: str,
    valores_anteriores: dict | None = None,
    valores_nuevos: dict | None = None,
) -> None:
    """
    Punto único de registro de auditoría. Nunca incluir clave_hash, token_hash
    ni codigo_hash en valores_anteriores/valores_nuevos (regla de seguridad).
    """
    registro = RegistroAuditoria(
        id=None,
        usuario_id=usuario_id,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        valores_anteriores=valores_anteriores,
        valores_nuevos=valores_nuevos,
    )
    await repo_auditoria.registrar(registro)
