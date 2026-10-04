from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# RF-45/RF-48: eventos notificables por correo. 'diagnostico_fallido' extiende
# el catálogo del Diccionario de Datos (que solo lista invitacion |
# diagnostico_evaluado | recomendacion_registrada | diagnostico_cerrado) para
# cubrir RF-38 ("notifica al administrador" cuando se agotan los reintentos
# del agente), que el diccionario no había anticipado como tipo de
# notificación.
TIPOS_VALIDOS = {
    "invitacion",
    "diagnostico_evaluado",
    "diagnostico_fallido",
    "recomendacion_registrada",
    "diagnostico_cerrado",
    "solicitud_nueva",
    "solicitud_rechazada",
}


@dataclass
class Notificacion:
    """RF-45/RF-48: registro de cada intento de envío de correo, con su
    resultado. Colección de solo anexado — un intento fallido no se
    reintenta automáticamente en esta versión (no hay programador de
    reintentos); queda registrado para que el administrador pueda
    diagnosticar problemas de entrega."""

    id: Optional[str]
    usuario_id: Optional[str]
    correo_destino: str
    tipo: str
    asunto: str
    contenido: str
    enviada_en: Optional[datetime] = None
    intentos: int = 1
    error: Optional[str] = None
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
