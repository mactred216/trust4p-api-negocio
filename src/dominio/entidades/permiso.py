from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Permiso:
    id: Optional[str]
    codigo: str  # formato recurso.accion, ej: "empresas.editar"
    modulo: str
    descripcion: str
    activo: bool = True
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
