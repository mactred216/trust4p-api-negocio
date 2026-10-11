from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_auditoria,
                                  obtener_repositorio_empresa,
                                  obtener_repositorio_sesion,
                                  obtener_repositorio_usuario)
from src.api.main import app
from src.dominio.entidades.usuario import Rol, Usuario

ADMIN_ID = "admin-1"


def usuario(id, rol="representante", empresa_id="emp-1", **extra):
    return Usuario(
        id=id,
        correo=f"{id}@ejemplo.com",
        clave_hash="h",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo=rol),
        empresa_id=empresa_id if rol == "representante" else None,
        **extra,
    )


@pytest.fixture
def entorno():
    repo_usuario = AsyncMock()
    repo_sesion = AsyncMock()
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": ADMIN_ID,
        "rol_codigo": "administrador",
        "permisos": ["usuarios.gestionar"],
    }
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = AsyncMock(activo=True)
    app.dependency_overrides[obtener_repositorio_usuario] = lambda: repo_usuario
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_empresa] = lambda: repo_empresa
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: AsyncMock()
    yield TestClient(app, cookies={"sesion": "t"}), repo_usuario, repo_sesion
    app.dependency_overrides.clear()


def test_el_administrador_cambia_el_rol_y_se_cierran_las_sesiones_del_usuario(entorno):
    cliente, repo_usuario, repo_sesion = entorno
    repo_usuario.obtener_por_id.return_value = usuario("u-2")

    r = cliente.patch("/v1/usuarios/u-2", json={"rol_codigo": "consultor"})

    assert r.status_code == 200
    assert r.json()["rol_codigo"] == "consultor" and r.json()["empresa_id"] is None
    repo_sesion.revocar_todas_de_usuario.assert_awaited_once_with("u-2")


def test_pasar_a_representante_exige_empresa(entorno):
    cliente, repo_usuario, repo_sesion = entorno
    repo_usuario.obtener_por_id.return_value = usuario("u-2", rol="consultor")

    r = cliente.patch("/v1/usuarios/u-2", json={"rol_codigo": "representante"})

    assert r.status_code == 400
    assert "empresa" in r.json()["detail"].lower()
    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()


def test_un_rol_inexistente_se_rechaza(entorno):
    cliente, repo_usuario, _ = entorno
    repo_usuario.obtener_por_id.return_value = usuario("u-2")

    r = cliente.patch("/v1/usuarios/u-2", json={"rol_codigo": "superusuario"})

    assert r.status_code == 422


def test_no_puede_cambiarse_su_propio_rol(entorno):
    cliente, repo_usuario, repo_sesion = entorno
    repo_usuario.obtener_por_id.return_value = usuario(ADMIN_ID, rol="administrador")

    r = cliente.patch(f"/v1/usuarios/{ADMIN_ID}", json={"rol_codigo": "consultor"})

    assert r.status_code == 400
    assert "propio rol" in r.json()["detail"]
    repo_usuario.actualizar.assert_not_called()
    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()


def test_si_puede_editar_su_propio_nombre(entorno):
    cliente, repo_usuario, _ = entorno
    repo_usuario.obtener_por_id.return_value = usuario(ADMIN_ID, rol="administrador")

    r = cliente.patch(f"/v1/usuarios/{ADMIN_ID}", json={"nombres": "Elena"})

    assert r.status_code == 200 and r.json()["nombres"] == "Elena"


def test_desactivar_cierra_las_sesiones(entorno):
    cliente, repo_usuario, repo_sesion = entorno
    repo_usuario.obtener_por_id.return_value = usuario("u-2")

    r = cliente.post("/v1/usuarios/u-2/desactivar")

    assert r.status_code == 204
    repo_sesion.revocar_todas_de_usuario.assert_awaited_once_with("u-2")


def test_no_puede_desactivar_su_propia_cuenta(entorno):
    cliente, _, repo_sesion = entorno

    r = cliente.post(f"/v1/usuarios/{ADMIN_ID}/desactivar")

    assert r.status_code == 400
    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()


def test_la_respuesta_indica_si_el_usuario_esta_bloqueado(entorno):
    cliente, repo_usuario, _ = entorno
    futuro = datetime.now(timezone.utc) + timedelta(minutes=10)
    repo_usuario.obtener_por_id.return_value = usuario(
        "u-2", intentos_fallidos=5, bloqueado_hasta=futuro
    )
    assert cliente.get("/v1/usuarios/u-2").json()["bloqueado"] is True

    pasado = datetime.now(timezone.utc) - timedelta(minutes=1)
    repo_usuario.obtener_por_id.return_value = usuario("u-2", bloqueado_hasta=pasado)
    assert cliente.get("/v1/usuarios/u-2").json()["bloqueado"] is False

    repo_usuario.obtener_por_id.return_value = usuario("u-2")
    assert cliente.get("/v1/usuarios/u-2").json()["bloqueado"] is False
