from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_auditoria,
                                  obtener_repositorio_modelo_madurez,
                                  obtener_repositorio_sesion)
from src.api.main import app
from tests.unitarias.aplicacion.test_catalogo_perfiles_cultura import \
    crear_modelo

RUTA = "/v1/modelos-madurez/m1/perfiles-cultura"


def sesion(rol, permisos):
    return {"usuario_id": f"{rol}-1", "rol_codigo": rol, "permisos": permisos}


@pytest.fixture
def entorno():
    modelo = crear_modelo()
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_id.return_value = modelo
    repo_sesion = AsyncMock()
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "administrador", ["modelo.gestionar"]
    )
    app.dependency_overrides[obtener_repositorio_modelo_madurez] = lambda: repo_modelo
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: AsyncMock()
    cliente = TestClient(app, cookies={"sesion": "t"})
    yield cliente, modelo, repo_sesion
    app.dependency_overrides.clear()


def test_el_administrador_define_un_perfil_y_la_respuesta_lo_incluye(entorno):
    cliente, modelo, _ = entorno

    r = cliente.post(
        RUTA, json={"codigo": "ENFP", "nombre": "Innovador nato", "descripcion": "Texto"}
    )

    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["perfiles_cultura"] == [
        {"codigo": "ENFP", "nombre": "Innovador nato", "descripcion": "Texto", "activo": True}
    ]
    assert len(cuerpo["combinaciones_perfil_cultural"]) == 16
    assert modelo.perfil_cultura_para("ENFP") is not None


def test_edita_y_desactiva_un_perfil(entorno):
    cliente, _, _ = entorno
    cliente.post(RUTA, json={"codigo": "ENFP", "nombre": "A", "descripcion": "B"})

    r = cliente.patch(f"{RUTA}/ENFP", json={"nombre": "Nuevo", "activo": False})

    assert r.status_code == 200
    perfil = r.json()["perfiles_cultura"][0]
    assert perfil["nombre"] == "Nuevo" and perfil["activo"] is False


def test_quita_un_perfil(entorno):
    cliente, _, _ = entorno
    cliente.post(RUTA, json={"codigo": "ENFP", "nombre": "A", "descripcion": "B"})

    r = cliente.delete(f"{RUTA}/ENFP")

    assert r.status_code == 200
    assert r.json()["perfiles_cultura"] == []


def test_una_combinacion_invalida_responde_400_con_el_motivo(entorno):
    cliente, _, _ = entorno

    r = cliente.post(RUTA, json={"codigo": "ZZZZ", "nombre": "A", "descripcion": "B"})

    assert r.status_code == 400
    assert "no es una combinación válida" in r.json()["detail"]


def test_los_campos_vacios_se_rechazan(entorno):
    cliente, _, _ = entorno

    r = cliente.post(RUTA, json={"codigo": "ENFP", "nombre": "  ", "descripcion": "B"})

    assert r.status_code == 422


def test_un_modelo_inexistente_responde_404(entorno):
    cliente, _, _ = entorno
    app.dependency_overrides[obtener_repositorio_modelo_madurez] = lambda: AsyncMock(
        obtener_por_id=AsyncMock(return_value=None)
    )

    r = cliente.post(RUTA, json={"codigo": "ENFP", "nombre": "A", "descripcion": "B"})

    assert r.status_code == 404


@pytest.mark.parametrize("rol", ["representante", "consultor"])
def test_solo_el_administrador_gestiona_el_catalogo(entorno, rol):
    cliente, _, repo_sesion = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(rol, ["modelo.gestionar"])

    r = cliente.post(RUTA, json={"codigo": "ENFP", "nombre": "A", "descripcion": "B"})

    assert r.status_code == 403
