from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import bcrypt

from src.dominio.entidades.token_verificacion import TipoToken
from src.dominio.entidades.usuario import (VERSION_POLITICA_TRATAMIENTO_DATOS,
                                           Rol, Usuario)
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_solicitud import RepositorioSolicitud
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


class TokenInvalido(Exception):
    pass


class AutorizacionRequerida(Exception):
    """RF-43: sin autorización de tratamiento de datos no se completa el registro."""

    pass


class CompletarRegistro:
    """RF-03: consume una invitación de un solo uso. La invitación nace de una
    solicitud aprobada (RF-02: se crea el usuario representante) o de un
    usuario creado por el administrador (RF-25: se completa la cuenta
    pendiente)."""

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
        if (
            token is None
            or token.tipo != TipoToken.INVITACION
            or not token.esta_vigente()
        ):
            raise TokenInvalido()

        clave_hash = bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()
        ahora = datetime.now(timezone.utc)

        if token.usuario_id:
            usuario = await self._usuarios.obtener_por_id(token.usuario_id)
            if usuario is None or not usuario.registro_pendiente:
                raise TokenInvalido()
            usuario.clave_hash = clave_hash
            usuario.nombres = nombres
            usuario.apellidos = apellidos
            usuario.acepto_tratamiento_en = ahora
            usuario.version_politica_aceptada = VERSION_POLITICA_TRATAMIENTO_DATOS
            usuario.registro_pendiente = False
            await self._usuarios.actualizar(usuario)
        else:
            solicitud = (
                await self._solicitudes.obtener_por_id(token.solicitud_id)
                if token.solicitud_id
                else None
            )
            if solicitud is None:
                raise TokenInvalido()
            usuario = await self._usuarios.guardar(
                Usuario(
                    id=None,
                    correo=solicitud.correo_solicitante,
                    clave_hash=clave_hash,
                    nombres=nombres,
                    apellidos=apellidos,
                    rol=Rol(codigo="representante", permisos=[]),
                    empresa_id=solicitud.empresa_id,
                    acepto_tratamiento_en=ahora,
                    version_politica_aceptada=VERSION_POLITICA_TRATAMIENTO_DATOS,
                )
            )

        token.marcar_usado()
        await self._tokens.actualizar(token)
        return usuario


@dataclass
class DatosInvitacion:
    correo: str
    nombre: str
    rol_codigo: str
    empresa_nombre: Optional[str]
    empresa_nit: Optional[str]
    expira_en: datetime


class ConsultarInvitacion:
    """RF-03: antes de definir la clave, la pantalla de registro muestra a
    quien corresponde la invitacion (empresa, correo, nombre). El codigo es el
    secreto: quien lo tiene ya conoce estos datos por el correo recibido."""

    def __init__(
        self,
        repo_token: RepositorioToken,
        repo_usuario: RepositorioUsuario,
        repo_solicitud: RepositorioSolicitud,
        repo_empresa: RepositorioEmpresa,
    ):
        self._tokens = repo_token
        self._usuarios = repo_usuario
        self._solicitudes = repo_solicitud
        self._empresas = repo_empresa

    async def ejecutar(self, codigo_token: str) -> DatosInvitacion:
        token = await self._tokens.obtener_por_codigo(codigo_token)
        if (
            token is None
            or token.tipo != TipoToken.INVITACION
            or not token.esta_vigente()
        ):
            raise TokenInvalido()

        if token.usuario_id:
            usuario = await self._usuarios.obtener_por_id(token.usuario_id)
            if usuario is None or not usuario.registro_pendiente:
                raise TokenInvalido()
            empresa = (
                await self._empresas.obtener_por_id(usuario.empresa_id)
                if usuario.empresa_id
                else None
            )
            return DatosInvitacion(
                correo=usuario.correo,
                nombre=f"{usuario.nombres} {usuario.apellidos}".strip(),
                rol_codigo=usuario.rol.codigo,
                empresa_nombre=empresa.nombre if empresa else None,
                empresa_nit=empresa.nit if empresa else None,
                expira_en=token.expira_en,
            )

        solicitud = (
            await self._solicitudes.obtener_por_id(token.solicitud_id)
            if token.solicitud_id
            else None
        )
        if solicitud is None:
            raise TokenInvalido()
        return DatosInvitacion(
            correo=solicitud.correo_solicitante,
            nombre=solicitud.nombre_solicitante,
            rol_codigo="representante",
            empresa_nombre=solicitud.nombre_empresa,
            empresa_nit=solicitud.nit,
            expira_en=token.expira_en,
        )
