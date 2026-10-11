from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_auditoria,
                                  obtener_repositorio_empresa,
                                  obtener_repositorio_sector,
                                  obtener_repositorio_sesion)
from src.api.main import app
from src.dominio.entidades.empresa import Empresa, Sector

SERVICIOS = Sector(id="s-1", codigo="servicios", nombre="Servicios profesionales")
FINTECH = Sector(id="s-2", codigo="fintech", nombre="Fintech y Servicios financieros")


def empresa():
    return Empresa(
        id="emp-1",
        nombre="InnovaTech",
        sector=SERVICIOS,
        nit="900111222",
        numero_empleados=30,
    )


@pytest.fixture
def entorno():
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.side_effect = lambda _id: empresa()
    repo_empresa.obtener_por_nit.return_value = None
    repo_sector = AsyncMock()
    repo_sector.obtener_por_codigo.side_effect = lambda c: FINTECH if c == "fintech" else None
    repo_sesion = AsyncMock()
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "admin-1",
        "rol_codigo": "administrador",
        "permisos": ["empresas.gestionar"],
    }
    repo_auditoria = AsyncMock()
    app.dependency_overrides[obtener_repositorio_empresa] = lambda: repo_empresa
    app.dependency_overrides[obtener_repositorio_sector] = lambda: repo_sector
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: repo_auditoria
    yield TestClient(app, cookies={"sesion": "t"}), repo_empresa, repo_sesion, repo_auditoria
    app.dependency_overrides.clear()


def test_edita_nombre_nit_sector_y_empleados(entorno):
    cliente, repo_empresa, _, _ = entorno

    r = cliente.patch(
        "/v1/empresas/emp-1",
        json={"nombre": "Nueva SAS", "nit": "800555666-1", "sector_codigo": "fintech", "numero_empleados": 120},
    )

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["nombre"] == "Nueva SAS"
    assert cuerpo["nit"] == "800555666-1"
    assert cuerpo["sector_codigo"] == "fintech"
    assert cuerpo["sector_nombre"] == "Fintech y Servicios financieros"
    assert cuerpo["numero_empleados"] == 120
    guardada = repo_empresa.actualizar.await_args.args[0]
    assert guardada.sector == FINTECH


def test_la_auditoria_registra_cada_campo_con_su_valor_anterior_y_nuevo(entorno):
    cliente, _, _, repo_auditoria = entorno

    cliente.patch(
        "/v1/empresas/emp-1",
        json={"nit": "800555666", "sector_codigo": "fintech", "numero_empleados": 120},
    )

    registro = repo_auditoria.registrar.await_args.args[0]
    assert registro.entidad == "empresas" and registro.entidad_id == "emp-1"
    assert registro.valores_anteriores == {
        "nit": "900111222",
        "sector": "servicios",
        "sector_nombre": "Servicios profesionales",
        "numero_empleados": 30,
    }
    assert registro.valores_nuevos == {
        "nit": "800555666",
        "sector": "fintech",
        "sector_nombre": "Fintech y Servicios financieros",
        "numero_empleados": 120,
    }


def test_un_sector_que_no_existe_responde_400_y_no_cambia_nada(entorno):
    cliente, repo_empresa, _, repo_auditoria = entorno

    r = cliente.patch("/v1/empresas/emp-1", json={"sector_codigo": "inventado"})

    assert r.status_code == 400
    assert "sector" in r.json()["detail"].lower()
    repo_empresa.actualizar.assert_not_awaited()
    repo_auditoria.registrar.assert_not_awaited()


def test_un_nit_de_otra_empresa_responde_409(entorno):
    cliente, repo_empresa, _, _ = entorno
    otra = empresa()
    otra.id = "emp-2"
    repo_empresa.obtener_por_nit.return_value = otra

    r = cliente.patch("/v1/empresas/emp-1", json={"nit": "800555666"})

    assert r.status_code == 409


@pytest.mark.parametrize("nit", ["abc", "123", "12-34-56"])
def test_un_nit_con_formato_invalido_responde_422(entorno, nit):
    cliente, _, _, _ = entorno

    assert cliente.patch("/v1/empresas/emp-1", json={"nit": nit}).status_code == 422


def test_un_sector_vacio_responde_422(entorno):
    cliente, _, _, _ = entorno

    assert cliente.patch("/v1/empresas/emp-1", json={"sector_codigo": "  "}).status_code == 422


def test_sin_el_permiso_de_edicion_responde_403(entorno):
    cliente, _, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "u-1",
        "rol_codigo": "administrador",
        "permisos": ["usuarios.gestionar"],
    }

    r = cliente.patch("/v1/empresas/emp-1", json={"sector_codigo": "fintech"})

    assert r.status_code == 403


def test_un_consultor_no_puede_editar_empresas(entorno):
    cliente, _, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "c-1",
        "rol_codigo": "consultor",
        "permisos": ["empresas.gestionar"],
    }

    assert cliente.patch("/v1/empresas/emp-1", json={"nit": "800555666"}).status_code == 403
