from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_rol import RepositorioRol
from src.dominio.puertos.repositorio_sesion import RepositorioSesion
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario

# Hash de una clave aleatoria descartada: se compara contra él cuando el correo
# no existe para que el tiempo de respuesta no delate si la cuenta existe.
HASH_SENUELO = bcrypt.hashpw(b"senuelo-no-es-una-clave-real", bcrypt.gensalt()).decode()


class CredencialesInvalidas(Exception):
    pass


class CuentaBloqueada(Exception):
    pass


class CuentaInactiva(Exception):
    """RF-24: la empresa del usuario fue desactivada."""


class BloqueoCorreosDesconocidos:
    """HU-004 CA-02: el bloqueo temporal debe comportarse igual para un correo
    que no existe que para uno que existe, para no revelar qué cuentas hay.
    Registro en memoria (no persiste el correo) con los mismos umbrales que
    Usuario: 5 intentos fallidos consecutivos y 15 minutos de bloqueo."""

    MAXIMO_INTENTOS = 5
    BLOQUEO_MINUTOS = 15
    MAXIMO_REGISTROS = 10_000

    def __init__(self) -> None:
        self._registros: dict[str, tuple[int, Optional[datetime]]] = {}

    def _depurar(self) -> None:
        if len(self._registros) < self.MAXIMO_REGISTROS:
            return
        ahora = datetime.now(timezone.utc)
        for correo, (_, hasta) in list(self._registros.items()):
            if hasta is None or hasta < ahora:
                del self._registros[correo]

    def esta_bloqueado(self, correo: str) -> bool:
        _, hasta = self._registros.get(correo.lower(), (0, None))
        return hasta is not None and datetime.now(timezone.utc) < hasta

    def registrar_fallo(self, correo: str) -> None:
        self._depurar()
        clave = correo.lower()
        intentos, _ = self._registros.get(clave, (0, None))
        intentos += 1
        hasta = None
        if intentos >= self.MAXIMO_INTENTOS:
            hasta = datetime.now(timezone.utc) + timedelta(minutes=self.BLOQUEO_MINUTOS)
        self._registros[clave] = (intentos, hasta)


class IniciarSesion:
    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_sesion: RepositorioSesion,
        repo_rol: Optional[RepositorioRol] = None,
        repo_empresa: Optional[RepositorioEmpresa] = None,
        bloqueo_desconocidos: Optional[BloqueoCorreosDesconocidos] = None,
        repo_auditoria: Optional[RepositorioAuditoria] = None,
    ):
        self._usuarios = repo_usuario
        self._sesiones = repo_sesion
        self._roles = repo_rol
        self._empresas = repo_empresa
        self._desconocidos = bloqueo_desconocidos or BloqueoCorreosDesconocidos()
        self._auditoria = repo_auditoria

    async def _registrar(
        self, usuario_id: str, resultado: str, ip: Optional[str], **extra
    ) -> None:
        """RNF-22 / HU-004 CA-01: eventos de seguridad en la bitacora (sin
        credenciales ni datos de quien no tiene cuenta)."""
        if self._auditoria is None:
            return
        await self._auditoria.registrar(
            RegistroAuditoria(
                id=None,
                usuario_id=usuario_id,
                entidad="usuarios",
                entidad_id=usuario_id,
                accion="autenticar",
                valores_nuevos={"resultado": resultado, **extra},
                direccion_ip=ip,
            )
        )

    async def ejecutar(self, correo: str, clave: str, ip: Optional[str] = None) -> str:
        usuario = await self._usuarios.obtener_por_correo(correo)
        if usuario is None:
            if self._desconocidos.esta_bloqueado(correo):
                raise CuentaBloqueada()
            bcrypt.checkpw(clave.encode(), HASH_SENUELO.encode())
            self._desconocidos.registrar_fallo(correo)
            raise CredencialesInvalidas()

        if not usuario.puede_intentar_acceso():
            await self._registrar(usuario.id, "intento_con_cuenta_bloqueada", ip)
            raise CuentaBloqueada()

        if not bcrypt.checkpw(clave.encode(), usuario.clave_hash.encode()):
            usuario.registrar_intento_fallido()
            await self._usuarios.actualizar(usuario)
            await self._registrar(
                usuario.id,
                "cuenta_bloqueada" if usuario.bloqueado_hasta else "fallido",
                ip,
                intentos=usuario.intentos_fallidos,
            )
            raise CredencialesInvalidas()

        if usuario.empresa_id and self._empresas is not None:
            empresa = await self._empresas.obtener_por_id(usuario.empresa_id)
            if empresa is not None and not empresa.activo:
                await self._registrar(usuario.id, "empresa_inactiva", ip)
                raise CuentaInactiva()

        usuario.reiniciar_intentos()
        await self._usuarios.actualizar(usuario)

        if self._roles is not None:
            # R-16: los permisos efectivos se resuelven desde el catálogo de
            # roles al crear la sesión (no desde una copia en el usuario).
            rol = await self._roles.obtener_por_codigo(usuario.rol.codigo)
            if rol is not None:
                usuario.rol.permisos = list(rol.permisos)

        token = await self._sesiones.crear(usuario)
        await self._registrar(usuario.id, "exitoso", ip)
        return token
