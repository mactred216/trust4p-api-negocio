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
