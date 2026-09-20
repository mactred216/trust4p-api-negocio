from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


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
