import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class TipoToken(str, Enum):
    INVITACION = "invitacion"
    RESTABLECER_CLAVE = "restablecer_clave"
    VERIFICAR_CORREO = "verificar_correo"


DURACION_INVITACION_HORAS = 72  # tres días para completar el registro


@dataclass
class TokenVerificacion:
    id: Optional[str]
    tipo: TipoToken
    correo_destino: str
    solicitud_id: Optional[str] = None
    usuario_id: Optional[str] = None
    expira_en: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
        + timedelta(hours=DURACION_INVITACION_HORAS)
    )
    usado_en: Optional[datetime] = None
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def esta_vigente(self) -> bool:
        if self.usado_en is not None:
            return False

        expira_en = self.expira_en
        if expira_en.tzinfo is None:
            expira_en = expira_en.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) < expira_en

    def marcar_usado(self) -> None:
        """RF-03: un token es de un solo uso."""
        if not self.esta_vigente():
            raise ValueError("El token no está vigente o ya fue utilizado")
        self.usado_en = datetime.now(timezone.utc)

    @staticmethod
    def generar_codigo() -> str:
        return secrets.token_urlsafe(32)
