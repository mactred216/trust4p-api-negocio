from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class RegistroAuditoria:
    id: Optional[str]
    usuario_id: Optional[str]  # None para acciones del sistema
    entidad: str  # nombre de la colección afectada
    entidad_id: Optional[str]
    accion: str  # crear | actualizar | eliminar | consultar | autenticar
    valores_anteriores: Optional[dict[str, Any]] = None
    valores_nuevos: Optional[dict[str, Any]] = None
    direccion_ip: Optional[str] = None
    registrado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
