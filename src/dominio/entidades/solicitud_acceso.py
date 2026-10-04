from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SolicitudYaResuelta(ValueError):
    """RF-02: una solicitud solo se resuelve una vez."""


class EstadoSolicitud(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass
class SolicitudAcceso:
    """RF-01: datos de la empresa y del solicitante. Los campos de RF-01 que
    se agregaron después del primer corte (NIT, sector, tamaño, cargo,
    teléfono, ciudad) son opcionales a nivel de entidad para no romper
    solicitudes ya radicadas; el endpoint público los exige al radicar."""

    id: Optional[str]
    nombre_empresa: str
    correo_solicitante: str
    nombre_solicitante: str
    estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE
    empresa_id: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resuelto_en: Optional[datetime] = None
    nit: Optional[str] = None
    sector_codigo: Optional[str] = None
    sector_nombre: Optional[str] = None
    numero_empleados: Optional[int] = None
    ciudad: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    acepto_tratamiento_en: Optional[datetime] = None
    version_politica_aceptada: Optional[str] = None

    def aprobar(self, empresa_id: str) -> None:
        """RF-02: solo se puede resolver una vez (evita doble aprobación)."""
        if self.estado != EstadoSolicitud.PENDIENTE:
            raise SolicitudYaResuelta("La solicitud ya fue resuelta")
        self.estado = EstadoSolicitud.APROBADA
        self.empresa_id = empresa_id
        self.resuelto_en = datetime.now(timezone.utc)

    def rechazar(self, motivo: str) -> None:
        """RF-02: el rechazo exige motivo explícito, no queda ambiguo."""
        if self.estado != EstadoSolicitud.PENDIENTE:
            raise SolicitudYaResuelta("La solicitud ya fue resuelta")
        if not motivo or not motivo.strip():
            raise ValueError("El motivo de rechazo es obligatorio")
        self.estado = EstadoSolicitud.RECHAZADA
        self.motivo_rechazo = motivo
        self.resuelto_en = datetime.now(timezone.utc)
