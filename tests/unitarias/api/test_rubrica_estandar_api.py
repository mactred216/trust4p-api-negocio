from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_auditoria,
                                  obtener_repositorio_modelo_madurez,
                                  obtener_repositorio_sesion)
from src.api.main import app
from src.dominio.entidades.modelo_madurez import ModeloMadurez, Nivel

RUTA = "/v1/modelos-madurez/m1/niveles/estandar"
ACTUAL = {}  # el modelo que devuelve el repositorio simulado


def modelo(publicado=False):
    m = ModeloMadurez(id="m1", version="2026.2", nombre="M", escala_min=0, escala_max=100, publicado=publicado)
    m.niveles = [
        Nivel(nivel=1, nombre="Inicial", descripcion="a", umbral_min=Decimal(0), umbral_max=Decimal(50)),
        Nivel(nivel=2, nombre="Alto", descripcion="b", umbral_min=Decimal(50), umbral_max=Decimal(100)),
    ]
    return m


@pytest.fixture
def entorno():
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_id.side_effect = lambda _id: ACTUAL["modelo"]
    ACTUAL["modelo"] = modelo()
    repo_sesion = AsyncMock()
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "admin-1",
        "rol_codigo": "administrador",
        "permisos": ["modelo.gestionar"],
    }
    repo_auditoria = AsyncMock()
    app.dependency_overrides[obtener_repositorio_modelo_madurez] = lambda: repo_modelo
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: repo_auditoria
    yield TestClient(app, cookies={"sesion": "t"}), repo_modelo, repo_sesion, repo_auditoria
    app.dependency_overrides.clear()


def test_reemplaza_la_rubrica_del_borrador_por_los_10_niveles(entorno):
    cliente, repo_modelo, _, _ = entorno

    r = cliente.post(RUTA)

    assert r.status_code == 200
    niveles = r.json()["niveles"]
    assert [n["nivel"] for n in niveles] == list(range(1, 11))
    assert Decimal(niveles[0]["umbral_min"]) == 0 and Decimal(niveles[0]["umbral_max"]) == 10
    assert Decimal(niveles[9]["umbral_min"]) == 90 and Decimal(niveles[9]["umbral_max"]) == 100
    repo_modelo.actualizar.assert_awaited_once()


def test_queda_en_la_auditoria_con_la_cantidad_anterior_y_la_nueva(entorno):
    cliente, _, _, repo_auditoria = entorno

    cliente.post(RUTA)

    registro = repo_auditoria.registrar.await_args.args[0]
    assert registro.valores_anteriores == {"niveles": 2}
    assert registro.valores_nuevos == {"rubrica_estandar_aplicada": 10}


def test_una_version_publicada_no_se_modifica(entorno):
    cliente, repo_modelo, _, _ = entorno
    ACTUAL["modelo"] = modelo(publicado=True)

    r = cliente.post(RUTA)

    assert r.status_code == 400
    repo_modelo.actualizar.assert_not_awaited()


def test_un_modelo_inexistente_responde_404(entorno):
    cliente, repo_modelo, _, _ = entorno
    repo_modelo.obtener_por_id.side_effect = lambda _id: None

    assert cliente.post(RUTA).status_code == 404


@pytest.mark.parametrize("rol", ["consultor", "representante"])
def test_solo_el_administrador_puede(entorno, rol):
    cliente, _, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = {
        "usuario_id": "u-1",
        "rol_codigo": rol,
        "permisos": ["modelo.gestionar"],
    }

    assert cliente.post(RUTA).status_code == 403
