from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.resolver_solicitud import (ResolverSolicitud,
                                                         SolicitudNoEncontrada)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.solicitud_acceso import SolicitudAcceso
from src.dominio.entidades.token_verificacion import TokenVerificacion


def crear_solicitud_prueba():
    return SolicitudAcceso(
        id="sol-1",
        nombre_empresa="InnovaTech",
        correo_solicitante="ana@innovatech.com",
        nombre_solicitante="Ana Pérez",
    )


@pytest.mark.asyncio
async def test_aprobar_solicitud_crea_empresa_y_token():
    solicitud = crear_solicitud_prueba()
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = solicitud
    repo_empresa = AsyncMock()
    repo_empresa.guardar.side_effect = lambda e: Empresa(
        id="emp-1", nombre=e.nombre, sector=e.sector
    )
    repo_token = AsyncMock()
    repo_token.guardar.side_effect = lambda t, c: t
    servicio_correo = AsyncMock()
    repo_notificacion = AsyncMock()

    caso_uso = ResolverSolicitud(
        repo_solicitud, repo_empresa, repo_token, servicio_correo, repo_notificacion
    )
    sector = Sector(id="1", codigo="J62", nombre="Software")
    empresa, codigo = await caso_uso.aprobar("sol-1", sector)

    assert empresa.id == "emp-1"
    assert isinstance(codigo, str)
    assert len(codigo) > 0
    repo_solicitud.actualizar.assert_called_once()
    repo_token.guardar.assert_called_once()
    servicio_correo.enviar.assert_called_once()
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"] == "ana@innovatech.com"
    )
    repo_notificacion.registrar.assert_called_once()
    notificacion = repo_notificacion.registrar.call_args[0][0]
    assert notificacion.tipo == "invitacion"
    assert notificacion.enviada_en is not None


@pytest.mark.asyncio
async def test_aprobar_solicitud_inexistente_lanza_excepcion():
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = None
    repo_empresa = AsyncMock()
    repo_token = AsyncMock()
    servicio_correo = AsyncMock()
    repo_notificacion = AsyncMock()

    caso_uso = ResolverSolicitud(
        repo_solicitud, repo_empresa, repo_token, servicio_correo, repo_notificacion
    )

    with pytest.raises(SolicitudNoEncontrada):
        await caso_uso.aprobar(
            "sol-inexistente", Sector(id="1", codigo="J62", nombre="Software")
        )


@pytest.mark.asyncio
async def test_rechazar_solicitud_con_motivo():
    solicitud = crear_solicitud_prueba()
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = solicitud
    repo_empresa = AsyncMock()
    repo_token = AsyncMock()
    servicio_correo = AsyncMock()
    repo_notificacion = AsyncMock()

    caso_uso = ResolverSolicitud(
        repo_solicitud, repo_empresa, repo_token, servicio_correo, repo_notificacion
    )
    await caso_uso.rechazar("sol-1", motivo="No cumple criterio de tamaño")

    repo_empresa.guardar.assert_not_called()
    repo_solicitud.actualizar.assert_called_once()
    # HU-002 CA-02: se notifica al solicitante con el motivo
    servicio_correo.enviar.assert_called_once()
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"]
        == solicitud.correo_solicitante
    )
    assert (
        "No cumple criterio de tamaño"
        in servicio_correo.enviar.call_args.kwargs["cuerpo"]
    )
    assert repo_notificacion.registrar.call_args[0][0].tipo == "solicitud_rechazada"
