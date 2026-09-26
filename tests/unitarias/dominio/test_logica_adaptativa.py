from decimal import Decimal

from src.dominio.entidades.diagnostico import Respuesta
from src.dominio.entidades.modelo_madurez import CondicionActivacion, Pregunta
from src.dominio.servicios.logica_adaptativa import (evaluar_condicion,
                                                     preguntas_aplicables)


def crear_pregunta(
    codigo="p1",
    condicion=None,
    activo=True,
    obligatoria=True,
) -> Pregunta:
    return Pregunta(
        codigo=codigo,
        dimension_codigo="innovacion",
        enunciado="¿Pregunta?",
        tipo="seleccion_unica",
        obligatoria=obligatoria,
        peso=Decimal("1"),
        en_demo=False,
        orden=1,
        condicion=condicion,
        activo=activo,
    )


def crear_respuesta(codigo, opciones_codigo=None, texto=None, valor=None) -> Respuesta:
    return Respuesta(
        pregunta_codigo=codigo,
        dimension_codigo="innovacion",
        opciones_codigo=opciones_codigo or [],
        texto=texto,
        valor=valor,
    )


def test_evaluar_condicion_igual_verdadera():
    condicion = CondicionActivacion(pregunta_codigo="p1", operador="igual", valor="si")
    respuestas = {"p1": crear_respuesta("p1", opciones_codigo=["si"])}
    assert evaluar_condicion(condicion, respuestas) is True


def test_evaluar_condicion_igual_falsa():
    condicion = CondicionActivacion(pregunta_codigo="p1", operador="igual", valor="si")
    respuestas = {"p1": crear_respuesta("p1", opciones_codigo=["no"])}
    assert evaluar_condicion(condicion, respuestas) is False


def test_evaluar_condicion_diferente():
    condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="diferente", valor="si"
    )
    respuestas = {"p1": crear_respuesta("p1", opciones_codigo=["no"])}
    assert evaluar_condicion(condicion, respuestas) is True


def test_evaluar_condicion_contiene():
    condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="contiene", valor="innov"
    )
    respuestas = {"p1": crear_respuesta("p1", texto="cultura de innovacion")}
    assert evaluar_condicion(condicion, respuestas) is True


def test_evaluar_condicion_mayor_que():
    condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="mayor_que", valor="3"
    )
    respuestas = {"p1": crear_respuesta("p1", valor=Decimal("4"))}
    assert evaluar_condicion(condicion, respuestas) is True


def test_evaluar_condicion_menor_que_falsa():
    condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="menor_que", valor="3"
    )
    respuestas = {"p1": crear_respuesta("p1", valor=Decimal("4"))}
    assert evaluar_condicion(condicion, respuestas) is False


def test_evaluar_condicion_sin_respuesta_es_falsa():
    condicion = CondicionActivacion(pregunta_codigo="p1", operador="igual", valor="si")
    assert evaluar_condicion(condicion, {}) is False


def test_evaluar_condicion_numerica_invalida_es_falsa():
    condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="mayor_que", valor="no-es-numero"
    )
    respuestas = {"p1": crear_respuesta("p1", texto="tampoco")}
    assert evaluar_condicion(condicion, respuestas) is False


def test_preguntas_aplicables_sin_condicion_siempre_aplica():
    preguntas = [crear_pregunta("p1")]
    assert preguntas_aplicables(preguntas, []) == preguntas


def test_preguntas_aplicables_excluye_inactivas():
    preguntas = [crear_pregunta("p1", activo=False)]
    assert preguntas_aplicables(preguntas, []) == []


def test_preguntas_aplicables_respeta_condicion_cumplida():
    condicion = CondicionActivacion(pregunta_codigo="p1", operador="igual", valor="si")
    preguntas = [crear_pregunta("p1"), crear_pregunta("p2", condicion=condicion)]
    respuestas = [crear_respuesta("p1", opciones_codigo=["si"])]
    aplicables = preguntas_aplicables(preguntas, respuestas)
    assert {p.codigo for p in aplicables} == {"p1", "p2"}


def test_preguntas_aplicables_excluye_condicion_no_cumplida():
    condicion = CondicionActivacion(pregunta_codigo="p1", operador="igual", valor="si")
    preguntas = [crear_pregunta("p1"), crear_pregunta("p2", condicion=condicion)]
    respuestas = [crear_respuesta("p1", opciones_codigo=["no"])]
    aplicables = preguntas_aplicables(preguntas, respuestas)
    assert {p.codigo for p in aplicables} == {"p1"}
