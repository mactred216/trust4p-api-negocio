from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class EstadoSolicitud(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass
class SolicitudAcceso:
    id: Optional[str]
    nombre_empresa: str
    correo_solicitante: str
    nombre_solicitante: str
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
    empresa_id: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resuelto_en: Optional[datetime] = None

    def aprobar(self, empresa_id: str) -> None:
        """RF-02: solo se puede resolver una vez (evita doble aprobación)."""
        if self.estado != EstadoSolicitud.PENDIENTE:
            raise ValueError("Solo se pueden aprobar solicitudes pendientes")
        self.estado = EstadoSolicitud.APROBADA
        self.empresa_id = empresa_id
        self.resuelto_en = datetime.now(timezone.utc)

    def rechazar(self, motivo: str) -> None:
        """RF-02: el rechazo exige motivo explícito, no queda ambiguo."""
        if self.estado != EstadoSolicitud.PENDIENTE:
            raise ValueError("Solo se pueden rechazar solicitudes pendientes")
        if not motivo or not motivo.strip():
            raise ValueError("El motivo de rechazo es obligatorio")
        self.estado = EstadoSolicitud.RECHAZADA
        self.motivo_rechazo = motivo
        self.resuelto_en = datetime.now(timezone.utc)
