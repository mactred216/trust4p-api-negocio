from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.middleware.autorizacion import requiere_rol


class PeticionFalsa:
    def __init__(self, token="t"):
        self.cookies = {"sesion": token} if token else {}


def repo_con(sesion):
    repo = AsyncMock()
    repo.obtener_sesion_por_token.return_value = sesion
    return repo


@pytest.mark.asyncio
async def test_sin_cookie_responde_401():
    verificar = requiere_rol("consultor", "diagnosticos.consultar")
    with pytest.raises(HTTPException) as e:
        await verificar(PeticionFalsa(None), repo_con(None))
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_rol_incorrecto_responde_403():
    verificar = requiere_rol("consultor", "diagnosticos.consultar")
    sesion = {
        "usuario_id": "u",
        "rol_codigo": "representante",
        "permisos": ["diagnosticos.consultar"],
    }
    with pytest.raises(HTTPException) as e:
        await verificar(PeticionFalsa(), repo_con(sesion))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_rol_correcto_sin_el_permiso_responde_403():
    """HU-028 CA-01: retirado el permiso al rol, la accion se deniega."""
    verificar = requiere_rol("consultor", "diagnosticos.consultar")
    sesion = {"usuario_id": "u", "rol_codigo": "consultor", "permisos": []}
    with pytest.raises(HTTPException) as e:
        await verificar(PeticionFalsa(), repo_con(sesion))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_rol_y_permiso_correctos_devuelven_el_usuario():
    verificar = requiere_rol("consultor", "diagnosticos.consultar")
    sesion = {
        "usuario_id": "u-1",
        "rol_codigo": "consultor",
        "permisos": ["diagnosticos.consultar", "otro"],
    }
    assert await verificar(PeticionFalsa(), repo_con(sesion)) == "u-1"


@pytest.mark.asyncio
async def test_sin_permiso_requerido_solo_valida_el_rol():
    verificar = requiere_rol("consultor")
    sesion = {"usuario_id": "u-1", "rol_codigo": "consultor", "permisos": []}
    assert await verificar(PeticionFalsa(), repo_con(sesion)) == "u-1"


@pytest.mark.asyncio
async def test_sesion_sin_campo_permisos_se_trata_como_vacia():
    verificar = requiere_rol("consultor", "x.y")
    with pytest.raises(HTTPException):
        await verificar(
            PeticionFalsa(), repo_con({"usuario_id": "u", "rol_codigo": "consultor"})
        )
