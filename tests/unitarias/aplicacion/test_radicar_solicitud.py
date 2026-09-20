# tests/unitarias/aplicacion/test_radicar_solicitud.py
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.radicar_solicitud import (RadicarSolicitud,
                                                        SolicitudDuplicada)


@pytest.mark.asyncio
async def test_radicar_solicitud_nueva_se_guarda():
    repo = AsyncMock()
    repo.existe_pendiente_con_correo.return_value = False
    repo.guardar.side_effect = lambda s: s  # simula que Mongo la devuelve igual

    caso_uso = RadicarSolicitud(repo)
    resultado = await caso_uso.ejecutar(
        nombre_empresa="InnovaTech",
        correo_solicitante="ana@innovatech.com",
        nombre_solicitante="Ana Pérez",
    )

    assert resultado.nombre_empresa == "InnovaTech"
    repo.guardar.assert_called_once()


@pytest.mark.asyncio
async def test_no_se_puede_radicar_con_correo_ya_pendiente():
    repo = AsyncMock()
    repo.existe_pendiente_con_correo.return_value = True

    caso_uso = RadicarSolicitud(repo)

    with pytest.raises(SolicitudDuplicada):
        await caso_uso.ejecutar(
            nombre_empresa="InnovaTech",
            correo_solicitante="ana@innovatech.com",
            nombre_solicitante="Ana Pérez",
        )

    repo.guardar.assert_not_called()
