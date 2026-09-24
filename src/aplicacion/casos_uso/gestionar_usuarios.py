from typing import Optional

from src.dominio.entidades.usuario import Rol, Usuario
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class UsuarioNoEncontrado(Exception):
    pass


class CorreoYaRegistrado(Exception):
    pass


class ListarUsuarios:
    def __init__(self, repo: RepositorioUsuario):
        self._usuarios = repo

    async def ejecutar(self, empresa_id: Optional[str] = None) -> list[Usuario]:
        if empresa_id is not None:
            return await self._usuarios.listar_por_empresa(empresa_id)
        return await self._usuarios.listar_todos()


class ConsultarUsuario:
    def __init__(self, repo: RepositorioUsuario):
        self._usuarios = repo

    async def ejecutar(self, usuario_id: str) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()
        return usuario


class EditarUsuario:
    def __init__(self, repo: RepositorioUsuario):
        self._usuarios = repo

    async def ejecutar(
        self,
        usuario_id: str,
        nombres: Optional[str] = None,
        apellidos: Optional[str] = None,
        rol_codigo: Optional[str] = None,
    ) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        if nombres is not None:
            usuario.nombres = nombres
        if apellidos is not None:
            usuario.apellidos = apellidos
        if rol_codigo is not None:
            usuario.rol = Rol(codigo=rol_codigo, permisos=usuario.rol.permisos)

        await self._usuarios.actualizar(usuario)
        return usuario


class DesactivarUsuario:
    """RF-26: baja lógica. No elimina el historial de diagnósticos asociados."""

    def __init__(self, repo: RepositorioUsuario):
        self._usuarios = repo

    async def ejecutar(self, usuario_id: str) -> None:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        usuario.desactivar()
        await self._usuarios.actualizar(usuario)


class ReactivarUsuario:
    def __init__(self, repo: RepositorioUsuario):
        self._usuarios = repo

    async def ejecutar(self, usuario_id: str) -> None:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        usuario.reactivar()
        await self._usuarios.actualizar(usuario)


class DesbloquearUsuario:
    """Pendiente #5: hoy el desbloqueo tras 5 intentos fallidos (RF-04) solo se
    revertía editando Atlas a mano. Permite al administrador reiniciar el
    contador de intentos y levantar el bloqueo manualmente."""

    def __init__(self, repo: RepositorioUsuario):
        self._usuarios = repo

    async def ejecutar(self, usuario_id: str) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        if usuario.bloqueado_hasta is None:
            raise ValueError("El usuario no se encuentra bloqueado")

        usuario.reiniciar_intentos()
        await self._usuarios.actualizar(usuario)
        return usuario
