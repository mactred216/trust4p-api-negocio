from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_auditoria,
                                  obtener_repositorio_sesion,
                                  obtener_repositorio_usuario)
from src.api.main import app
from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.entidades.usuario import Rol, Usuario


def elena():
    return Usuario(
        id="u-1",
        correo="elena@trust4p.com",
        clave_hash="h",
        nombres="Elena",
        apellidos="Rostova",
        rol=Rol(codigo="administrador"),
    )


@pytest.fixture
def entorno():
    repo_sesion = AsyncMock()
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "u-1",
        "rol_codigo": "administrador",
        "permisos": ["auditoria.consultar"],
    }
    repo_auditoria = AsyncMock()
    repo_auditoria.listar.return_value = [
        RegistroAuditoria(id="r1", usuario_id="u-1", entidad="empresas", entidad_id="e-1", accion="actualizar"),
        RegistroAuditoria(id="r2", usuario_id=None, entidad="sesiones", entidad_id=None, accion="autenticar"),
    ]
    repo_usuario = AsyncMock()
    repo_usuario.listar_por_ids.return_value = [elena()]
    repo_usuario.buscar.return_value = [elena()]
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: repo_auditoria
    app.dependency_overrides[obtener_repositorio_usuario] = lambda: repo_usuario
    yield TestClient(app, cookies={"sesion": "t"}), repo_sesion, repo_auditoria, repo_usuario
    app.dependency_overrides.clear()


def test_la_bitacora_devuelve_nombre_y_correo_de_quien_actuo(entorno):
    cliente, *_ = entorno

    r = cliente.get("/v1/auditoria")

    assert r.status_code == 200
    con_usuario, del_sistema = r.json()
    assert con_usuario["usuario_id"] == "u-1"  # el id se conserva para quien lo necesite
    assert con_usuario["usuario_nombre"] == "Elena Rostova"
    assert con_usuario["usuario_correo"] == "elena@trust4p.com"
    assert del_sistema["usuario_id"] is None
    assert del_sistema["usuario_nombre"] is None and del_sistema["usuario_correo"] is None


def test_se_filtra_por_nombre_o_correo(entorno):
    cliente, _, repo_auditoria, repo_usuario = entorno

    r = cliente.get("/v1/auditoria", params={"usuario": "elena@trust"})

    assert r.status_code == 200
    repo_usuario.buscar.assert_awaited_once_with("elena@trust")
    assert repo_auditoria.listar.await_args.kwargs["usuario_ids"] == ["u-1"]


def test_si_nadie_coincide_responde_lista_vacia(entorno):
    cliente, _, repo_auditoria, repo_usuario = entorno
    repo_usuario.buscar.return_value = []

    r = cliente.get("/v1/auditoria", params={"usuario": "nadie"})

    assert r.status_code == 200 and r.json() == []
    repo_auditoria.listar.assert_not_awaited()


def test_el_filtro_por_id_sigue_funcionando(entorno):
    cliente, _, repo_auditoria, _ = entorno

    cliente.get("/v1/auditoria", params={"usuario_id": "u-1"})

    assert repo_auditoria.listar.await_args.kwargs["usuario_id"] == "u-1"


def test_un_texto_de_usuario_demasiado_largo_se_rechaza(entorno):
    cliente, *_ = entorno

    assert cliente.get("/v1/auditoria", params={"usuario": "x" * 101}).status_code == 422


def test_solo_el_administrador_con_permiso_consulta_la_bitacora(entorno):
    cliente, repo_sesion, *_ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "c-1",
        "rol_codigo": "consultor",
        "permisos": ["auditoria.consultar"],
    }

    assert cliente.get("/v1/auditoria").status_code == 403
