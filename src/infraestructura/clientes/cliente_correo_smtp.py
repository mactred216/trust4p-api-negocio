import asyncio
import os
import smtplib
from email.message import EmailMessage

from src.dominio.puertos.servicio_correo import ServicioCorreo


class ClienteCorreoSMTP(ServicioCorreo):
    """Adaptador SMTP real (Gmail: smtp.gmail.com:587 con STARTTLS y contraseña de aplicación)."""

    def __init__(
        self,
        host: str | None = None,
        puerto: int | None = None,
        usuario: str | None = None,
        clave: str | None = None,
        remitente: str | None = None,
    ):
        self._host = host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self._puerto = puerto or int(os.getenv("SMTP_PUERTO", "587"))
        self._usuario = usuario or os.getenv("SMTP_USUARIO")
        self._clave = clave or os.getenv("SMTP_CLAVE")
        self._remitente = remitente or os.getenv("SMTP_REMITENTE") or self._usuario

    async def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        await asyncio.to_thread(self._enviar_sincrono, destinatario, asunto, cuerpo)

    def _enviar_sincrono(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = self._remitente
        mensaje["To"] = destinatario
        mensaje.set_content(cuerpo)

        with smtplib.SMTP(self._host, self._puerto, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(self._usuario, self._clave)
            smtp.send_message(mensaje)
