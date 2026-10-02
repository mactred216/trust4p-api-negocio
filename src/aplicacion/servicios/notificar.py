from datetime import datetime, timezone
from typing import Optional

from src.dominio.entidades.notificacion import Notificacion
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.servicio_correo import ServicioCorreo


async def enviar_notificacion(
    servicio_correo: ServicioCorreo,
    repo_notificacion: RepositorioNotificacion,
    usuario_id: Optional[str],
    correo_destino: str,
    tipo: str,
    asunto: str,
    contenido: str,
) -> Notificacion:
    """RF-45/RF-48: envía el correo y registra el resultado en la bitácora
    de notificaciones, exista o no haya salido el envío. Un fallo de correo
    nunca debe interrumpir la operación de negocio que lo origina (una
    invitación, una evaluación, un cierre) — por eso no se propaga."""
    try:
        await servicio_correo.enviar(
            destinatario=correo_destino, asunto=asunto, cuerpo=contenido
        )
        enviada_en = datetime.now(timezone.utc)
        error = None
    except Exception as e:
        enviada_en = None
        error = str(e)

    return await repo_notificacion.registrar(
        Notificacion(
            id=None,
            usuario_id=usuario_id,
            correo_destino=correo_destino,
            tipo=tipo,
            asunto=asunto,
            contenido=contenido,
            enviada_en=enviada_en,
            error=error,
        )
    )
