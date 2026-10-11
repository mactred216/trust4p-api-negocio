from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_permiso,
                                  obtener_repositorio_sesion)
from src.api.main import app
from src.dominio.catalogo_permisos import (NOMBRES_MODULOS_PERMISOS,
                                           PERMISOS_POR_ROL, PERMISOS_SISTEMA,
                                           nombre_modulo_permiso)
from src.dominio.entidades.permiso import Permiso

# El código del permiso (roles.gestionar) es interno; el usuario final ve un
# nombre legible, y cada módulo también.


def test_cada_permiso_del_catalogo_tiene_un_nombre_legible_y_unico():
    nombres = [nombre for _, _, nombre, _ in PERMISOS_SISTEMA]

    assert all(n.strip() for n in nombres)
    assert len(set(nombres)) == len(nombres)
    # un nombre para personas no se parece a un código técnico
    assert not any("." in n or "_" in n for n in nombres)


def test_todos_los_modulos_del_catalogo_tienen_nombre():
    modulos = {modulo for _, modulo, _, _ in PERMISOS_SISTEMA}

    assert modulos <= set(NOMBRES_MODULOS_PERMISOS)
    assert nombre_modulo_permiso("administracion") == "Administración"


def test_un_modulo_desconocido_se_muestra_con_su_codigo_capitalizado():
    assert nombre_modulo_permiso("reportes") == "Reportes"


def test_los_permisos_por_rol_existen_en_el_catalogo():
    codigos = {c for c, _, _, _ in PERMISOS_SISTEMA}

    for permisos in PERMISOS_POR_ROL.values():
        assert set(permisos) <= codigos


@pytest.fixture
def cliente():
    repo_sesion = AsyncMock()
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "admin-1",
        "rol_codigo": "administrador",
        "permisos": ["roles.gestionar"],
    }
    repo_permiso = AsyncMock()
    repo_permiso.listar_activos.return_value = [
        Permiso(
            id="p1",
            codigo="roles.gestionar",
            modulo="administracion",
            descripcion="Gestionar roles y permisos",
            nombre="Gestionar roles y permisos",
            creado_en=datetime.now(timezone.utc),
        ),
        # creado antes de que existiera el nombre: no debe romper la pantalla
        Permiso(
            id="p2",
            codigo="reportes.ver",
            modulo="reportes",
            descripcion="Ver reportes",
        ),
    ]
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_permiso] = lambda: repo_permiso
    yield TestClient(app, cookies={"sesion": "t"})
    app.dependency_overrides.clear()


def test_la_api_devuelve_el_nombre_del_permiso_y_del_modulo(cliente):
    r = cliente.get("/v1/roles/permisos")

    assert r.status_code == 200
    asignado = next(p for p in r.json() if p["codigo"] == "roles.gestionar")
    assert asignado["nombre"] == "Gestionar roles y permisos"
    assert asignado["modulo_nombre"] == "Administración"
    assert asignado["modulo"] == "administracion"


def test_sin_nombre_guardado_la_api_usa_el_codigo_y_no_falla(cliente):
    r = cliente.get("/v1/roles/permisos")

    sin_nombre = next(p for p in r.json() if p["codigo"] == "reportes.ver")
    assert sin_nombre["nombre"] == "reportes.ver"
    assert sin_nombre["modulo_nombre"] == "Reportes"
