from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


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
