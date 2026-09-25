from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import Diagnostico, Respuesta


def crear_diagnostico_prueba(estado: str = "borrador") -> Diagnostico:
    return Diagnostico(
        id="diag-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="v1",
        consecutivo=1,
        estado=estado,
    )


def crear_respuesta(codigo="p1", dimension="innovacion") -> Respuesta:
    return Respuesta(
        pregunta_codigo=codigo, dimension_codigo=dimension, opcion_codigo="alta"
    )


def test_registrar_respuesta_la_agrega():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta(), total_preguntas_activas=2)
    assert len(diagnostico.respuestas) == 1


def test_registrar_respuesta_actualiza_avance():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), total_preguntas_activas=4)
    assert diagnostico.porcentaje_avance == 25


def test_registrar_respuesta_reemplaza_la_anterior_para_la_misma_pregunta():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), total_preguntas_activas=2)
    nueva = Respuesta(
        pregunta_codigo="p1", dimension_codigo="innovacion", opcion_codigo="baja"
    )
    diagnostico.registrar_respuesta(nueva, total_preguntas_activas=2)

    assert len(diagnostico.respuestas) == 1
    assert diagnostico.respuestas[0].opcion_codigo == "baja"


def test_registrar_respuesta_en_diagnostico_cerrado_falla():
    diagnostico = crear_diagnostico_prueba(estado="cerrado")
    with pytest.raises(ValueError):
        diagnostico.registrar_respuesta(crear_respuesta(), total_preguntas_activas=2)


def test_avance_no_supera_cien_por_ciento():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), total_preguntas_activas=1)
    assert diagnostico.porcentaje_avance == 100


def test_avance_con_cero_preguntas_activas_es_cero():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), total_preguntas_activas=0)
    assert diagnostico.porcentaje_avance == 0


def test_respuesta_de_devuelve_la_respuesta_existente():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), total_preguntas_activas=2)
    assert diagnostico.respuesta_de("p1") is not None
    assert diagnostico.respuesta_de("no-existe") is None


def test_esta_cerrado():
    assert crear_diagnostico_prueba(estado="cerrado").esta_cerrado() is True
    assert crear_diagnostico_prueba(estado="borrador").esta_cerrado() is False
