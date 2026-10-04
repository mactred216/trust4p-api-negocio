from fastapi.testclient import TestClient

from src.api.main import app

cliente = TestClient(app)


def test_preflight_de_un_origen_permitido_incluye_credenciales():
    r = cliente.options(
        "/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-credentials"] == "true"


def test_origen_no_permitido_no_recibe_cabeceras_cors():
    r = cliente.options(
        "/v1/auth/login",
        headers={
            "Origin": "http://sitio-malicioso.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in r.headers


def test_las_respuestas_llevan_cabeceras_de_seguridad():
    r = cliente.get("/openapi.json")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "max-age" in r.headers["strict-transport-security"]


def test_la_api_no_se_almacena_en_cache():
    r = cliente.get("/v1/auth/login")  # 405: solo interesa la cabecera
    assert r.headers["cache-control"] == "no-store"
