from fastapi import Depends, HTTPException, Request

from src.api.dependencias import obtener_repositorio_sesion
from src.infraestructura.persistencia.repositorio_mongo_sesion import \
    RepositorioMongoSesion


async def obtener_usuario_autenticado(
    request: Request,
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> str:
    """Verifica la cookie de sesión y devuelve el ID del usuario autenticado."""
    token = request.cookies.get("sesion")
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado")

    usuario_id = await repo_sesion.obtener_usuario_id_por_token(token)
    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    return usuario_id


def requiere_rol(rol_esperado: str):
    """Fábrica de dependencias: exige un rol específico para el endpoint."""

    async def verificar(
        request: Request,
        repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
    ) -> str:
        token = request.cookies.get("sesion")
        if token is None:
            raise HTTPException(status_code=401, detail="No autenticado")

        sesion = await repo_sesion.obtener_sesion_por_token(token)
        if sesion is None:
            raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

        if sesion["rol_codigo"] != rol_esperado:
            raise HTTPException(
                status_code=403, detail="No autorizado para esta operación"
            )

        return sesion["usuario_id"]

    return verificar
