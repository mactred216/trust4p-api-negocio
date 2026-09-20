from src.dominio.entidades.rol import RolCatalogo
from src.dominio.puertos.repositorio_permiso import RepositorioPermiso
from src.dominio.puertos.repositorio_rol import RepositorioRol


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


class AgregarPermisoARol:
    def __init__(self, repo_rol: RepositorioRol, repo_permiso: RepositorioPermiso):
        self._roles = repo_rol
        self._permisos = repo_permiso

    async def ejecutar(self, codigo_rol: str, codigo_permiso: str) -> RolCatalogo:
        permiso = await self._permisos.obtener_por_codigo(codigo_permiso)
        if permiso is None:
            raise PermisoNoExiste()

        rol = await self._roles.obtener_por_codigo(codigo_rol)
        if rol is None:
            raise RolNoEncontrado()

        rol.agregar_permiso(codigo_permiso)
        await self._roles.actualizar(rol)
        return rol


class QuitarPermisoDeRol:
    def __init__(self, repo_rol: RepositorioRol):
        self._roles = repo_rol

    async def ejecutar(self, codigo_rol: str, codigo_permiso: str) -> RolCatalogo:
        rol = await self._roles.obtener_por_codigo(codigo_rol)
        if rol is None:
            raise RolNoEncontrado()

        rol.quitar_permiso(
            codigo_permiso
        )  # puede lanzar ValueError si es admin + roles.gestionar
        await self._roles.actualizar(rol)
        return rol
