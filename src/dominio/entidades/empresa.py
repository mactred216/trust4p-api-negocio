from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Sector:
    id: str
    codigo: str
    nombre: str


@dataclass
class Empresa:
    id: Optional[str]
    nombre: str
    sector: Sector
    nit: Optional[str] = None
    numero_empleados: Optional[int] = None
    ciudad: Optional[str] = None
    activo: bool = True
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def desactivar(self) -> None:
        """Baja lógica. Los diagnósticos asociados se conservan (regla R-06)."""
        self.activo = False

    def reactivar(self) -> None:
        self.activo = True
