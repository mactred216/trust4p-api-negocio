import bcrypt

from src.dominio.puertos.repositorio_sesion import RepositorioSesion
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class CredencialesInvalidas(Exception):
    pass


class CuentaBloqueada(Exception):
    pass


class IniciarSesion:
    def __init__(
        self, repo_usuario: RepositorioUsuario, repo_sesion: RepositorioSesion
    ):
        self._usuarios = repo_usuario
        self._sesiones = repo_sesion

    async def ejecutar(self, correo: str, clave: str) -> str:
        usuario = await self._usuarios.obtener_por_correo(correo)
        if usuario is None:
            raise CredencialesInvalidas()

        if not usuario.puede_intentar_acceso():
            raise CuentaBloqueada()

        if not bcrypt.checkpw(clave.encode(), usuario.clave_hash.encode()):
            usuario.registrar_intento_fallido()
            await self._usuarios.actualizar(usuario)
            raise CredencialesInvalidas()

        usuario.reiniciar_intentos()
        await self._usuarios.actualizar(usuario)

        token = await self._sesiones.crear(usuario)
        return token
