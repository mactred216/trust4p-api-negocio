from unittest.mock import patch

from src.infraestructura.clientes.cliente_servicio_agente_http import (
    TIEMPO_ESPERA_POR_DEFECTO, ClienteServicioAgenteHTTP)


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
