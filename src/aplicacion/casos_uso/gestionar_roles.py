from src.dominio.entidades.rol import RolCatalogo
from src.dominio.puertos.repositorio_permiso import RepositorioPermiso
from src.dominio.puertos.repositorio_rol import RepositorioRol
from src.dominio.puertos.repositorio_sesion import RepositorioSesion
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class RolNoEncontrado(Exception):
    pass


class PermisoNoExiste(Exception):
    pass


class ListarRoles:
    def __init__(self, repo: RepositorioRol):
        self._roles = repo

    async def ejecutar(self) -> list[RolCatalogo]:
        return await self._roles.listar_activos()


class ListarPermisos:
    def __init__(self, repo: RepositorioPermiso):
        self._permisos = repo

    async def ejecutar(self) -> list:
        return await self._permisos.listar_activos()


async def _sincronizar_usuarios_y_revocar_sesiones(
    repo_usuario: RepositorioUsuario,
    repo_sesion: RepositorioSesion,
    rol: RolCatalogo,
) -> None:
    """R-17: cambiar los permisos de un rol revoca las sesiones activas de sus
    usuarios (motivo cambio_permisos) y actualiza la copia embebida de permisos
    en cada usuario, para que ambas dejen de estar desactualizadas (R-16)."""
    usuarios_afectados = await repo_usuario.listar_por_rol(rol.codigo)
    for usuario in usuarios_afectados:
        usuario.rol.permisos = list(rol.permisos)
        await repo_usuario.actualizar(usuario)
        await repo_sesion.revocar_todas_de_usuario(usuario.id)


class AgregarPermisoARol:
    def __init__(
        self,
        repo_rol: RepositorioRol,
        repo_permiso: RepositorioPermiso,
        repo_usuario: RepositorioUsuario,
        repo_sesion: RepositorioSesion,
    ):
        self._roles = repo_rol
        self._permisos = repo_permiso
        self._usuarios = repo_usuario
        self._sesiones = repo_sesion

    async def ejecutar(self, codigo_rol: str, codigo_permiso: str) -> RolCatalogo:
        permiso = await self._permisos.obtener_por_codigo(codigo_permiso)
        if permiso is None:
            raise PermisoNoExiste()

        rol = await self._roles.obtener_por_codigo(codigo_rol)
        if rol is None:
            raise RolNoEncontrado()

        rol.agregar_permiso(codigo_permiso)
        await self._roles.actualizar(rol)
        await _sincronizar_usuarios_y_revocar_sesiones(
            self._usuarios, self._sesiones, rol
        )
        return rol


class QuitarPermisoDeRol:
    def __init__(
        self,
        repo_rol: RepositorioRol,
        repo_usuario: RepositorioUsuario,
        repo_sesion: RepositorioSesion,
    ):
        self._roles = repo_rol
        self._usuarios = repo_usuario
        self._sesiones = repo_sesion

    async def ejecutar(self, codigo_rol: str, codigo_permiso: str) -> RolCatalogo:
        rol = await self._roles.obtener_por_codigo(codigo_rol)
        if rol is None:
            raise RolNoEncontrado()

        rol.quitar_permiso(
            codigo_permiso
        )  # puede lanzar ValueError si es admin + roles.gestionar
        await self._roles.actualizar(rol)
        await _sincronizar_usuarios_y_revocar_sesiones(
            self._usuarios, self._sesiones, rol
        )
        return rol
