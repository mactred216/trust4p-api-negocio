import bcrypt

from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.puertos.repositorio_sesion import RepositorioSesion
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.puertos.servicio_correo import ServicioCorreo


class TokenInvalido(Exception):
    pass


class SolicitarRestablecimiento:
    """RF-05. Por seguridad, no revela si el correo existe o no (RNF de enumeración de usuarios)."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_token: RepositorioToken,
        servicio_correo: ServicioCorreo,
    ):
        self._usuarios = repo_usuario
        self._tokens = repo_token
        self._correo = servicio_correo

    async def ejecutar(self, correo: str) -> None:
        usuario = await self._usuarios.obtener_por_correo(correo)
        if usuario is None:
            return  # se sale en silencio; el endpoint responde igual en ambos casos

        codigo = TokenVerificacion.generar_codigo()
        token = TokenVerificacion(
            id=None,
            tipo=TipoToken.RESTABLECER_CLAVE,
            correo_destino=usuario.correo,
            usuario_id=usuario.id,
        )
        await self._tokens.guardar(token, codigo)

        await self._correo.enviar(
            destinatario=usuario.correo,
            asunto="Trust 4P - Código para restablecer tu contraseña",
            cuerpo=(
                f"Hola {usuario.nombres},\n\n"
                f"Usa el siguiente código para restablecer tu contraseña: {codigo}\n\n"
                "Si no solicitaste este cambio, puedes ignorar este mensaje."
            ),
        )


class RestablecerContrasena:
    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_token: RepositorioToken,
        repo_sesion: RepositorioSesion,
    ):
        self._usuarios = repo_usuario
        self._tokens = repo_token
        self._sesiones = repo_sesion

    async def ejecutar(self, codigo_token: str, clave_nueva: str) -> None:
        token = await self._tokens.obtener_por_codigo(codigo_token)
        if (
            token is None
            or not token.esta_vigente()
            or token.tipo != TipoToken.RESTABLECER_CLAVE
        ):
            raise TokenInvalido()

        usuario = await self._usuarios.obtener_por_correo(token.correo_destino)
        if usuario is None:
            raise TokenInvalido()

        usuario.clave_hash = bcrypt.hashpw(
            clave_nueva.encode(), bcrypt.gensalt()
        ).decode()
        usuario.reiniciar_intentos()
        await self._usuarios.actualizar(usuario)

        token.marcar_usado()
        await self._tokens.actualizar(token)

        await self._sesiones.revocar_todas_de_usuario(usuario.id)
