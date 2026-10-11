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


async def obtener_sesion_actual(
    request: Request,
    repo_sesion: RepositorioMongoSesion = Depends(obtener_repositorio_sesion),
) -> dict:
    """Documento de la sesion vigente (rol y permisos efectivos, R-16)."""
    token = request.cookies.get("sesion")
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    sesion = await repo_sesion.obtener_sesion_por_token(token)
    if sesion is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return sesion


def requiere_rol(rol_esperado: str, permiso: str | None = None):
    """Fábrica de dependencias: exige un rol específico para el endpoint y,
    si se indica, un permiso (RF-27, HU-028). Los permisos efectivos se
    resuelven al crear la sesión (R-16); al cambiar los de un rol se revocan
    las sesiones activas (R-17), por lo que retirar un permiso se aplica de
    inmediato."""

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
        if permiso is not None and permiso not in sesion.get("permisos", []):
            raise HTTPException(
                status_code=403, detail="No autorizado para esta operación"
            )

        return sesion["usuario_id"]

    return verificar


def requiere_algun_rol(permiso_por_rol: dict[str, str | None]):
    """Como requiere_rol, para endpoints que atienden a varios roles con alcance
    distinto (p. ej. el administrador ve todas las empresas y el consultor solo
    las suyas). Cada rol permitido puede exigir su propio permiso. Devuelve el
    id del usuario; el alcance lo decide el caso de uso según su rol."""

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

        rol = sesion["rol_codigo"]
        if rol not in permiso_por_rol:
            raise HTTPException(
                status_code=403, detail="No autorizado para esta operación"
            )
        permiso = permiso_por_rol[rol]
        if permiso is not None and permiso not in sesion.get("permisos", []):
            raise HTTPException(
                status_code=403, detail="No autorizado para esta operación"
            )

        return sesion["usuario_id"]

    return verificar
