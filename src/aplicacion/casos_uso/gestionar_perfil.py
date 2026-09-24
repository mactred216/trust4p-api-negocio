from typing import Optional

import bcrypt

from src.dominio.entidades.usuario import Usuario
from src.dominio.puertos.repositorio_sesion import RepositorioSesion
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.puertos.servicio_correo import ServicioCorreo


class UsuarioNoEncontrado(Exception):
    pass


class ClaveActualIncorrecta(Exception):
    """RF-06/HU-006 CA-01: rechaza el cambio sin modificar la credencial."""

    pass


class ClaveReutilizada(Exception):
    """RF-48: la nueva contraseña coincide con una de las últimas empleadas."""

    pass


class CerrarSesion:
    def __init__(self, repo_sesion: RepositorioSesion):
        self._sesiones = repo_sesion

    async def ejecutar(self, token: str) -> None:
        await self._sesiones.revocar(token)


class ActualizarPerfil:
    def __init__(self, repo_usuario: RepositorioUsuario):
        self._usuarios = repo_usuario

    async def ejecutar(
        self,
        usuario_id: str,
        nombres: Optional[str] = None,
        apellidos: Optional[str] = None,
        cargo: Optional[str] = None,
        telefono: Optional[str] = None,
    ) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        usuario.actualizar_perfil(
            nombres=nombres, apellidos=apellidos, cargo=cargo, telefono=telefono
        )
        await self._usuarios.actualizar(usuario)
        return usuario


class CambiarContrasena:
    """RF-06 paso 2 + RF-48: cambio de contraseña con clave actual, distinto
    del restablecimiento por token (recuperar_contrasena.py)."""

    def __init__(
        self, repo_usuario: RepositorioUsuario, repo_sesion: RepositorioSesion
    ):
        self._usuarios = repo_usuario
        self._sesiones = repo_sesion

    async def ejecutar(
        self, usuario_id: str, clave_actual: str, clave_nueva: str
    ) -> None:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        if not bcrypt.checkpw(clave_actual.encode(), usuario.clave_hash.encode()):
            raise ClaveActualIncorrecta()

        if any(
            bcrypt.checkpw(clave_nueva.encode(), h.encode())
            for h in usuario.hashes_recientes()
        ):
            raise ClaveReutilizada()

        nuevo_hash = bcrypt.hashpw(clave_nueva.encode(), bcrypt.gensalt()).decode()
        usuario.registrar_clave(nuevo_hash)
        await self._usuarios.actualizar(usuario)

        # Revoca todas las sesiones (igual que el restablecimiento por token);
        # el usuario debe volver a iniciar sesión en todos sus dispositivos.
        await self._sesiones.revocar_todas_de_usuario(usuario.id)


class EliminarDatosPersonales:
    """RF-44: solicitud de eliminación de datos personales por el propio usuario."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_sesion: RepositorioSesion,
        servicio_correo: ServicioCorreo,
    ):
        self._usuarios = repo_usuario
        self._sesiones = repo_sesion
        self._correo = servicio_correo

    async def ejecutar(self, usuario_id: str) -> None:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()
        if not usuario.activo:
            raise ValueError("La cuenta ya se encuentra inactiva")

        correo_original = usuario.correo
        nombres_originales = usuario.nombres

        # RF-44 paso 3: notificar antes de completar la eliminación del correo.
        await self._correo.enviar(
            destinatario=correo_original,
            asunto="Trust 4P - Confirmación de eliminación de tus datos",
            cuerpo=(
                f"Hola {nombres_originales},\n\n"
                "Confirmamos que tu solicitud de eliminación de datos personales "
                "fue procesada. Tu cuenta ha sido desactivada y tus datos "
                "identificables (nombre, correo, teléfono) fueron eliminados. "
                "Los resultados de tus diagnósticos se conservan de forma "
                "agregada y anonimizada con fines estadísticos."
            ),
        )

        usuario.anonimizar()
        await self._usuarios.actualizar(usuario)
        await self._sesiones.revocar_todas_de_usuario(usuario.id)
