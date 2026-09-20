from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.resolver_solicitud import (ResolverSolicitud,
                                                         SolicitudNoEncontrada)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.solicitud_acceso import SolicitudAcceso


def crear_solicitud_prueba():
    return SolicitudAcceso(
        id="sol-1",
        nombre_empresa="InnovaTech",
        correo_solicitante="ana@innovatech.com",
        nombre_solicitante="Ana Pérez",
    )


@pytest.mark.asyncio
async def test_aprobar_solicitud_crea_empresa():
    solicitud = crear_solicitud_prueba()
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = solicitud
    repo_empresa = AsyncMock()
    repo_empresa.guardar.side_effect = lambda e: Empresa(
        id="emp-1", nombre=e.nombre, sector=e.sector
    )

    caso_uso = ResolverSolicitud(repo_solicitud, repo_empresa)
    sector = Sector(id="1", codigo="J62", nombre="Software")
    empresa = await caso_uso.aprobar("sol-1", sector)

    assert empresa.id == "emp-1"
    assert empresa.nombre == "InnovaTech"
    repo_solicitud.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_aprobar_solicitud_inexistente_lanza_excepcion():
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = None
    repo_empresa = AsyncMock()

    caso_uso = ResolverSolicitud(repo_solicitud, repo_empresa)

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

    caso_uso = ResolverSolicitud(repo_solicitud, repo_empresa)
    await caso_uso.rechazar("sol-1", motivo="No cumple criterio de tamaño")

    repo_empresa.guardar.assert_not_called()
    repo_solicitud.actualizar.assert_called_once()
