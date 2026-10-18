from unittest.mock import patch

import httpx
import pytest

from src.dominio.puertos.cliente_servicio_agente import ServicioAgenteError
from src.infraestructura.clientes.cliente_servicio_agente_http import (
    TIEMPO_ESPERA_POR_DEFECTO, ClienteServicioAgenteHTTP)
from src.infraestructura.clientes.interruptor_circuito import \
    InterruptorDeCircuito


def test_el_plazo_por_defecto_cubre_el_arranque_en_frio_del_agente():
    # El servicio del agente escala a cero. Con 60 s el plazo se agotaba
    # durante el arranque en frío y el diagnóstico quedaba sin interpretación
    # aunque el agente la hubiera generado correctamente.
    with patch.dict("os.environ", {}, clear=True):
        cliente = ClienteServicioAgenteHTTP()

    assert cliente._tiempo_espera == float(TIEMPO_ESPERA_POR_DEFECTO)
    assert cliente._tiempo_espera >= 120


def test_el_plazo_se_ajusta_por_variable_de_entorno():
    with patch.dict("os.environ", {"AGENTE_TIEMPO_ESPERA_SEGUNDOS": "90"}, clear=True):
        cliente = ClienteServicioAgenteHTTP()

    assert cliente._tiempo_espera == 90.0


def test_el_valor_explicito_tiene_prioridad_sobre_el_entorno():
    with patch.dict("os.environ", {"AGENTE_TIEMPO_ESPERA_SEGUNDOS": "90"}, clear=True):
        cliente = ClienteServicioAgenteHTTP(tiempo_espera=15.0)

    assert cliente._tiempo_espera == 15.0


# --- ASR-02: cortocircuito ante la caída del servicio de evaluación ---------

class _RespuestaFalsa:
    def __init__(self, codigo, cuerpo=None):
        self.status_code = codigo
        self._cuerpo = cuerpo
        self.text = "texto"

    def json(self):
        if self._cuerpo is None:
            raise ValueError("sin json")
        return self._cuerpo


def _cliente_http_falso(comportamiento, llamadas):
    class ClienteFalso:
        def __init__(self, *args, **kwargs): ...

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            llamadas.append(1)
            resultado = comportamiento()
            if isinstance(resultado, Exception):
                raise resultado
            return resultado

    return ClienteFalso


def _cliente_agente(interruptor):
    cliente = ClienteServicioAgenteHTTP(
        url_base="http://agente", api_key="k", tiempo_espera=1, interruptor=interruptor
    )
    cliente._construir_solicitud = lambda *a: {}
    return cliente


RESPUESTA_VALIDA = {
    "perfil_cultura_descripcion": "d",
    "dimensiones_observaciones": {},
    "lienzo_negocio": {},
    "sintesis": "s",
    "recomendaciones": [],
}


@pytest.mark.asyncio
async def test_tras_fallos_seguidos_deja_de_llamar_al_servicio():
    llamadas = []
    interruptor = InterruptorDeCircuito(umbral=2, enfriamiento=60)
    cliente = _cliente_agente(interruptor)
    falso = _cliente_http_falso(lambda: httpx.ConnectError("caído"), llamadas)
    with patch("httpx.AsyncClient", falso):
        for _ in range(2):
            with pytest.raises(ServicioAgenteError):
                await cliente.evaluar(None, None, None)
        assert len(llamadas) == 2
        with pytest.raises(ServicioAgenteError) as error:
            await cliente.evaluar(None, None, None)
    assert "cortocircuito" in str(error.value)
    assert len(llamadas) == 2  # la tercera ni siquiera salió


@pytest.mark.asyncio
async def test_un_5xx_cuenta_como_caida_pero_un_4xx_no():
    llamadas = []
    interruptor = InterruptorDeCircuito(umbral=2, enfriamiento=60)
    cliente = _cliente_agente(interruptor)
    with patch("httpx.AsyncClient", _cliente_http_falso(lambda: _RespuestaFalsa(422), llamadas)):
        for _ in range(3):
            with pytest.raises(ServicioAgenteError):
                await cliente.evaluar(None, None, None)
    assert interruptor.estado == "cerrado"
    with patch("httpx.AsyncClient", _cliente_http_falso(lambda: _RespuestaFalsa(503), llamadas)):
        for _ in range(2):
            with pytest.raises(ServicioAgenteError):
                await cliente.evaluar(None, None, None)
    assert interruptor.estado == "abierto"


@pytest.mark.asyncio
async def test_una_respuesta_correcta_cierra_el_circuito_y_la_malformada_cuenta_como_fallo():
    llamadas = []
    interruptor = InterruptorDeCircuito(umbral=1, enfriamiento=0)
    cliente = _cliente_agente(interruptor)
    with patch("httpx.AsyncClient", _cliente_http_falso(lambda: _RespuestaFalsa(200, {"x": 1}), llamadas)):
        with pytest.raises(ServicioAgenteError) as error:
            await cliente.evaluar(None, None, None)
    assert "formato inválido" in str(error.value)
    assert interruptor.estado != "cerrado"
    with patch("httpx.AsyncClient", _cliente_http_falso(lambda: _RespuestaFalsa(200, RESPUESTA_VALIDA), llamadas)):
        respuesta = await cliente.evaluar(None, None, None)
    assert respuesta.sintesis == "s"
    assert interruptor.estado == "cerrado"
