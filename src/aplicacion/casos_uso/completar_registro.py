import bcrypt

from src.dominio.entidades.token_verificacion import TipoToken
from src.dominio.entidades.usuario import Rol, Usuario
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class TokenInvalido(Exception):
    pass


class AutorizacionRequerida(Exception):
    """RF-44: sin autorización de tratamiento de datos no se completa el registro."""

    pass


class CompletarRegistro:
    def __init__(
        self,
        repo_token: RepositorioToken,
        repo_usuario: RepositorioUsuario,
        repo_solicitud: RepositorioSolicitud,
    ):
        self._tokens = repo_token
        self._usuarios = repo_usuario
        self._solicitudes = repo_solicitud

    async def ejecutar(
        self,
        codigo_token: str,
        clave: str,
        nombres: str,
        apellidos: str,
        acepto_tratamiento: bool,
    ) -> Usuario:
        if not acepto_tratamiento:
            raise AutorizacionRequerida()

        token = await self._tokens.obtener_por_codigo(codigo_token)
        if token is None or not token.esta_vigente():
            raise TokenInvalido()

        solicitud = await self._solicitudes.obtener_por_id(token.solicitud_id)
        if solicitud is None:
            raise TokenInvalido()

        clave_hash = bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()

        usuario = Usuario(
            id=None,
            correo=solicitud.correo_solicitante,
            clave_hash=clave_hash,
            nombres=nombres,
            apellidos=apellidos,
            rol=Rol(codigo="representante", permisos=[]),
            empresa_id=solicitud.empresa_id,
        )
        usuario = await self._usuarios.guardar(usuario)

        token.marcar_usado()
        await self._tokens.actualizar(token)

        return usuario
