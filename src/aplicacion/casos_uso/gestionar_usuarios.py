import secrets
from typing import Optional

import bcrypt

from src.aplicacion.servicios.enlaces import enlace_frontend
from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.repositorio_token import RepositorioToken
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.puertos.servicio_correo import ServicioCorreo

ROLES_VALIDOS = {"administrador", "consultor", "representante"}


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


async def _validar_empresa_del_usuario(
    repo_empresa: Optional[RepositorioEmpresa],
    rol_codigo: str,
    empresa_id: Optional[str],
) -> Optional[str]:
    """RF-25: el representante pertenece a una empresa existente y activa; el
    consultor y el administrador no tienen empresa propia (los consultores
    acceden a empresas por asignación, RF-26)."""
    if rol_codigo == "representante":
        if not empresa_id:
            raise ValueError("El representante debe pertenecer a una empresa")
        empresa = (
            await repo_empresa.obtener_por_id(empresa_id) if repo_empresa else None
        )
        if empresa is None:
            raise ValueError("La empresa indicada no existe")
        if not empresa.activo:
            raise ValueError("La empresa indicada está inactiva")
        return empresa_id
    if empresa_id:
        raise ValueError("Solo el representante pertenece a una empresa")
    return None


class CrearUsuario:
    """RF-25 (HU-026): el administrador crea un usuario con rol y, si aplica,
    empresa. La cuenta nace sin clave utilizable: se envía una invitación de un
    solo uso para que la persona defina su contraseña y acepte el tratamiento
    de datos (RF-03, RF-43, RF-48)."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_empresa: RepositorioEmpresa,
        repo_token: RepositorioToken,
        servicio_correo: ServicioCorreo,
        repo_notificacion: RepositorioNotificacion,
    ):
        self._usuarios = repo_usuario
        self._empresas = repo_empresa
        self._tokens = repo_token
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion

    async def ejecutar(
        self,
        correo: str,
        nombres: str,
        apellidos: str,
        rol_codigo: str,
        empresa_id: Optional[str] = None,
    ) -> Usuario:
        if rol_codigo not in ROLES_VALIDOS:
            raise ValueError(
                f"Rol inválido. Debe ser uno de: {', '.join(sorted(ROLES_VALIDOS))}"
            )
        correo = correo.strip().lower()
        if await self._usuarios.obtener_por_correo(correo) is not None:
            raise CorreoYaRegistrado()
        empresa_id = await _validar_empresa_del_usuario(
            self._empresas, rol_codigo, empresa_id
        )

        clave_inutilizable = bcrypt.hashpw(
            secrets.token_urlsafe(32).encode(), bcrypt.gensalt()
        ).decode()
        usuario = await self._usuarios.guardar(
            Usuario(
                id=None,
                correo=correo,
                clave_hash=clave_inutilizable,
                nombres=nombres,
                apellidos=apellidos,
                rol=Rol(codigo=rol_codigo, permisos=[]),
                empresa_id=empresa_id,
                registro_pendiente=True,
            )
        )

        codigo = TokenVerificacion.generar_codigo()
        await self._tokens.guardar(
            TokenVerificacion(
                id=None,
                tipo=TipoToken.INVITACION,
                correo_destino=correo,
                usuario_id=usuario.id,
            ),
            codigo,
        )
        await enviar_notificacion(
            self._correo,
            self._notificaciones,
            usuario_id=usuario.id,
            correo_destino=correo,
            tipo="invitacion",
            asunto="Trust 4P - Invitación para completar tu registro",
            contenido=(
                f"Hola {nombres},\n\n"
                "El administrador creó tu cuenta en Trust 4P. "
                f"Define tu contraseña y completa tu registro en este enlace: {enlace_frontend('/registro', codigo)}\n\n"
                f"Si prefieres ingresarlo manualmente, tu código es: {codigo}"
            ),
        )
        return usuario


class EditarUsuario:
    def __init__(
        self,
        repo: RepositorioUsuario,
        repo_empresa: Optional[RepositorioEmpresa] = None,
    ):
        self._usuarios = repo
        self._empresas = repo_empresa

    async def ejecutar(
        self,
        usuario_id: str,
        nombres: Optional[str] = None,
        apellidos: Optional[str] = None,
        rol_codigo: Optional[str] = None,
        empresa_id: Optional[str] = None,
    ) -> Usuario:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()

        if rol_codigo is not None or empresa_id is not None:
            rol_final = rol_codigo or usuario.rol.codigo
            empresa_final = empresa_id
            if empresa_final is None and rol_final == "representante":
                empresa_final = usuario.empresa_id
            usuario.empresa_id = await _validar_empresa_del_usuario(
                self._empresas, rol_final, empresa_final
            )
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
