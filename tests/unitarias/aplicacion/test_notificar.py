from unittest.mock import AsyncMock

import pytest

from src.aplicacion.servicios.notificar import enviar_notificacion


@pytest.mark.asyncio
async def test_enviar_notificacion_exitosa_registra_enviada_en():
    servicio_correo = AsyncMock()
    repo_notificacion = AsyncMock()
    repo_notificacion.registrar.side_effect = lambda n: n

    resultado = await enviar_notificacion(
        servicio_correo,
        repo_notificacion,
        usuario_id="user-1",
        correo_destino="ana@innovatech.com",
        tipo="diagnostico_evaluado",
        asunto="Asunto",
        contenido="Contenido",
    )

    servicio_correo.enviar.assert_called_once_with(
        destinatario="ana@innovatech.com", asunto="Asunto", cuerpo="Contenido"
    )
    assert resultado.enviada_en is not None
    assert resultado.error is None
    repo_notificacion.registrar.assert_called_once()


@pytest.mark.asyncio
async def test_enviar_notificacion_con_fallo_de_correo_no_propaga_y_registra_error():
    """Un fallo de correo nunca debe interrumpir la operación de negocio que
    lo origina (RF-45) — se registra el error, no se relanza."""
    servicio_correo = AsyncMock()
    servicio_correo.enviar.side_effect = RuntimeError("SMTP no disponible")
    repo_notificacion = AsyncMock()
    repo_notificacion.registrar.side_effect = lambda n: n

    resultado = await enviar_notificacion(
        servicio_correo,
        repo_notificacion,
        usuario_id=None,
        correo_destino="admin@trust4p.com",
        tipo="diagnostico_fallido",
        asunto="Asunto",
        contenido="Contenido",
    )

    assert resultado.enviada_en is None
    assert "SMTP no disponible" in resultado.error
