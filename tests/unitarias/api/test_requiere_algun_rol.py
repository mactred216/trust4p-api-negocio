from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.middleware.autorizacion import requiere_algun_rol

ACCESO = requiere_algun_rol(
    {"administrador": "informes.descargar", "consultor": "informes.descargar"}
)


class PeticionFalsa:
    def __init__(self, token="t"):
        self.cookies = {"sesion": token} if token else {}


def repo_con(sesion):
    repo = AsyncMock()
    repo.obtener_sesion_por_token.return_value = sesion
    return repo


@pytest.mark.asyncio
async def test_admite_cada_rol_listado_con_su_permiso():
    for rol in ("administrador", "consultor"):
        sesion = {
            "usuario_id": f"{rol}-1",
            "rol_codigo": rol,
            "permisos": ["informes.descargar"],
        }
        assert await ACCESO(PeticionFalsa(), repo_con(sesion)) == f"{rol}-1"


@pytest.mark.asyncio
async def test_rechaza_a_un_rol_no_listado():
    sesion = {
        "usuario_id": "u",
        "rol_codigo": "representante",
        "permisos": ["informes.descargar"],
    }
    with pytest.raises(HTTPException) as e:
        await ACCESO(PeticionFalsa(), repo_con(sesion))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_rechaza_si_al_rol_le_retiraron_el_permiso():
    sesion = {"usuario_id": "u", "rol_codigo": "consultor", "permisos": []}
    with pytest.raises(HTTPException) as e:
        await ACCESO(PeticionFalsa(), repo_con(sesion))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_cada_rol_puede_exigir_un_permiso_distinto():
    acceso = requiere_algun_rol({"administrador": "a.x", "consultor": "c.y"})
    admin = {"usuario_id": "u", "rol_codigo": "administrador", "permisos": ["c.y"]}

    with pytest.raises(HTTPException) as e:
        await acceso(PeticionFalsa(), repo_con(admin))
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_sin_cookie_responde_401():
    with pytest.raises(HTTPException) as e:
        await ACCESO(PeticionFalsa(None), repo_con(None))
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_sesion_vencida_responde_401():
    with pytest.raises(HTTPException) as e:
        await ACCESO(PeticionFalsa(), repo_con(None))
    assert e.value.status_code == 401
