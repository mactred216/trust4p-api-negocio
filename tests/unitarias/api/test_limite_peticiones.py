from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.api.middleware.limite_peticiones import (LimitadorPeticiones,
                                                  limitar_peticiones)


class PeticionFalsa:
    def __init__(self, host="1.2.3.4"):
        self.client = type("C", (), {"host": host})()


def test_admite_hasta_el_maximo_y_luego_rechaza():
    limitador = LimitadorPeticiones(maximo=2, ventana_segundos=60)

    assert limitador.registrar("a") is None
    assert limitador.registrar("a") is None
    espera = limitador.registrar("a")

    assert espera is not None and 1 <= espera <= 60


def test_cada_origen_tiene_su_propio_cupo():
    limitador = LimitadorPeticiones(maximo=1, ventana_segundos=60)

    assert limitador.registrar("a") is None
    assert limitador.registrar("b") is None
    assert limitador.registrar("a") is not None


def test_la_ventana_se_libera_con_el_tiempo():
    limitador = LimitadorPeticiones(maximo=1, ventana_segundos=60)
    with patch("src.api.middleware.limite_peticiones.time.monotonic") as reloj:
        reloj.return_value = 1000.0
        assert limitador.registrar("a") is None
        reloj.return_value = 1030.0
        assert limitador.registrar("a") == 30
        reloj.return_value = 1061.0
        assert limitador.registrar("a") is None


@pytest.mark.asyncio
async def test_dependencia_responde_429_con_retry_after():
    dependencia = limitar_peticiones(LimitadorPeticiones(1, 60))

    await dependencia(PeticionFalsa())
    with pytest.raises(HTTPException) as e:
        await dependencia(PeticionFalsa())

    assert e.value.status_code == 429
    assert "Retry-After" in e.value.headers


def test_depura_origenes_vencidos_cuando_hay_demasiados():
    limitador = LimitadorPeticiones(maximo=1, ventana_segundos=60)
    with patch("src.api.middleware.limite_peticiones.MAXIMO_ORIGENES_RECORDADOS", 3):
        with patch("src.api.middleware.limite_peticiones.time.monotonic") as reloj:
            reloj.return_value = 0.0
            for origen in "abc":
                limitador.registrar(origen)
            reloj.return_value = 100.0
            limitador.registrar("d")

    assert set(limitador._registros) == {"d"}


# ---------------- Origen detrás de proxies (Cloud Run) ----------------


class PeticionConProxy:
    def __init__(self, xff=None, host="10.0.0.1"):
        self.client = type("C", (), {"host": host})()
        self.headers = {} if xff is None else {"x-forwarded-for": xff}


def test_origen_usa_la_ip_de_conexion_sin_proxies(monkeypatch):
    from src.api.middleware.limite_peticiones import origen_de

    monkeypatch.delenv("SALTOS_PROXY", raising=False)

    assert origen_de(PeticionConProxy("9.9.9.9")) == "10.0.0.1"


def test_origen_toma_la_entrada_que_agrego_el_proxy_propio(monkeypatch):
    from src.api.middleware.limite_peticiones import origen_de

    monkeypatch.setenv("SALTOS_PROXY", "2")

    # cliente, proxy nginx
    assert origen_de(PeticionConProxy("203.0.113.7, 10.8.0.2")) == "203.0.113.7"


def test_origen_ignora_lo_que_el_cliente_antepone_a_la_cabecera(monkeypatch):
    from src.api.middleware.limite_peticiones import origen_de

    monkeypatch.setenv("SALTOS_PROXY", "2")

    assert (
        origen_de(PeticionConProxy("1.1.1.1, 203.0.113.7, 10.8.0.2")) == "203.0.113.7"
    )


def test_origen_con_menos_entradas_que_saltos_usa_la_primera(monkeypatch):
    from src.api.middleware.limite_peticiones import origen_de

    monkeypatch.setenv("SALTOS_PROXY", "2")

    assert origen_de(PeticionConProxy("203.0.113.7")) == "203.0.113.7"


def test_origen_sin_cabecera_vuelve_a_la_ip_de_conexion(monkeypatch):
    from src.api.middleware.limite_peticiones import origen_de

    monkeypatch.setenv("SALTOS_PROXY", "2")

    assert origen_de(PeticionConProxy(None)) == "10.0.0.1"
