from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

VERSION_POLITICA_TRATAMIENTO_DATOS = "1.0"  # RF-43: versión vigente de la política


@dataclass
class Asignacion:
    empresa_id: str
    asignado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finalizado_en: Optional[datetime] = None

    def esta_vigente(self) -> bool:
        return self.finalizado_en is None


@dataclass
class Rol:
    codigo: str
    permisos: list[str] = field(default_factory=list)


@dataclass
class Usuario:
    id: Optional[str]
    correo: str
    clave_hash: str
    nombres: str
    apellidos: str
    rol: Rol
    empresa_id: Optional[str] = None
    intentos_fallidos: int = 0
    bloqueado_hasta: Optional[datetime] = None
    activo: bool = True
    asignaciones: list[Asignacion] = field(default_factory=list)
    historial_claves: list[str] = field(default_factory=list)
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    acepto_tratamiento_en: Optional[datetime] = None
    version_politica_aceptada: Optional[str] = None

    HISTORIAL_CLAVES_MAXIMO = 5

    def registrar_clave(self, nuevo_hash: str) -> None:
        """RF-48: conserva un historial de las últimas contraseñas para impedir su reúso."""
        self.historial_claves.insert(0, self.clave_hash)
        self.historial_claves = self.historial_claves[
            : self.HISTORIAL_CLAVES_MAXIMO - 1
        ]
        self.clave_hash = nuevo_hash

    def hashes_recientes(self) -> list[str]:
        """Hash vigente + historial, para validar reúso contra las últimas
        HISTORIAL_CLAVES_MAXIMO contraseñas."""
        return [self.clave_hash] + self.historial_claves

    def puede_intentar_acceso(self) -> bool:
        if self.bloqueado_hasta is None:
            return True
        bloqueado_hasta = self.bloqueado_hasta
        if bloqueado_hasta.tzinfo is None:
            bloqueado_hasta = bloqueado_hasta.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > bloqueado_hasta

    def registrar_intento_fallido(self) -> None:
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= 5:
            self.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=15)

    def reiniciar_intentos(self) -> None:
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None

    def desactivar(self) -> None:
        if not self.activo:
            raise ValueError("El usuario ya se encuentra inactivo")
        self.activo = False

    def actualizar_perfil(
        self,
        nombres: Optional[str] = None,
        apellidos: Optional[str] = None,
        cargo: Optional[str] = None,
        telefono: Optional[str] = None,
    ) -> None:
        """RF-06: el propio usuario edita sus datos de perfil."""
        if nombres is not None:
            self.nombres = nombres
        if apellidos is not None:
            self.apellidos = apellidos
        if cargo is not None:
            self.cargo = cargo
        if telefono is not None:
            self.telefono = telefono

    def anonimizar(self) -> None:
        """RF-44: elimina los datos personales identificables y desactiva la
        cuenta. Los resultados numéricos de diagnósticos (fuera del alcance
        de esta entidad) se conservan agregados y anonimizados aparte."""
        self.desactivar()
        self.correo = f"eliminado+{self.id}@anonimo.trust4p.local"
        self.nombres = "Usuario"
        self.apellidos = "eliminado"
        self.cargo = None
        self.telefono = None

    def reactivar(self) -> None:
        if self.activo:
            raise ValueError("El usuario ya se encuentra activo")
        self.activo = True

    def asignar_empresa(self, empresa_id: str) -> None:
        """RF-27. Una empresa puede tener varios consultores; un consultor, varias empresas."""
        if self.rol.codigo != "consultor":
            raise ValueError(
                "Solo los usuarios con rol consultor pueden recibir asignaciones"
            )

        ya_asignada = any(
            a.empresa_id == empresa_id and a.esta_vigente() for a in self.asignaciones
        )
        if ya_asignada:
            raise ValueError("Ya existe una asignación vigente para esta empresa")

        self.asignaciones.append(Asignacion(empresa_id=empresa_id))

    def finalizar_asignacion(self, empresa_id: str) -> None:
        for asignacion in self.asignaciones:
            if asignacion.empresa_id == empresa_id and asignacion.esta_vigente():
                asignacion.finalizado_en = datetime.now(timezone.utc)
                return
        raise ValueError("No existe una asignación vigente para esta empresa")

    def empresas_asignadas_vigentes(self) -> list[str]:
        return [a.empresa_id for a in self.asignaciones if a.esta_vigente()]
