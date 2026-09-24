from decimal import Decimal

import pytest

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, ModeloMadurez,
                                                  Pregunta)


def crear_modelo_prueba(publicado: bool = False) -> ModeloMadurez:
    return ModeloMadurez(
        id="modelo-1", version="v1", nombre="Modelo inicial", publicado=publicado
    )


def crear_dimension(codigo="innovacion", peso="0.5", orden=1) -> Dimension:
    return Dimension(
        codigo=codigo, nombre="Innovación", peso=Decimal(peso), orden=orden
    )


def crear_pregunta(
    codigo="p1", dimension_codigo="innovacion", peso="1", orden=1
) -> Pregunta:
    return Pregunta(
        codigo=codigo,
        dimension_codigo=dimension_codigo,
        enunciado="¿Su empresa invierte en I+D?",
        tipo="escala",
        obligatoria=True,
        peso=Decimal(peso),
        en_demo=False,
        orden=orden,
    )


def test_agregar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    assert len(modelo.dimensiones) == 1


def test_agregar_dimension_con_codigo_duplicado_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    with pytest.raises(ValueError):
        modelo.agregar_dimension(crear_dimension())


def test_editar_dimension_actualiza_solo_campos_enviados():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    modelo.editar_dimension("innovacion", peso=Decimal("0.7"))
    assert modelo.dimensiones[0].peso == Decimal("0.7")
    assert modelo.dimensiones[0].nombre == "Innovación"


def test_editar_dimension_inexistente_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.editar_dimension("no-existe", peso=Decimal("0.5"))


def test_quitar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    modelo.quitar_dimension("innovacion")
    assert modelo.dimensiones == []


def test_no_se_puede_modificar_una_version_publicada():
    modelo = crear_modelo_prueba(publicado=True)
    with pytest.raises(ValueError):
        modelo.agregar_dimension(crear_dimension())


# R-02: la suma de los pesos de las dimensiones debe totalizar 1 (RF-30, HU-031 CA-01)
def test_validar_pesos_dimensiones_correctos_no_lanza():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "0.5", 1))
    modelo.agregar_dimension(crear_dimension("cultura", "0.5", 2))
    modelo.validar_pesos_dimensiones()  # no debe lanzar


def test_validar_pesos_dimensiones_que_no_suman_uno_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "0.5", 1))
    modelo.agregar_dimension(crear_dimension("cultura", "0.3", 2))
    with pytest.raises(ValueError):
        modelo.validar_pesos_dimensiones()


def test_validar_pesos_sin_dimensiones_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.validar_pesos_dimensiones()


# HU-032: asociar preguntas a dimensiones
def crear_modelo_con_dimension() -> ModeloMadurez:
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    return modelo


def test_agregar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    assert len(modelo.preguntas) == 1


def test_agregar_pregunta_a_dimension_inexistente_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(crear_pregunta(dimension_codigo="no-existe"))


def test_agregar_pregunta_con_codigo_duplicado_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1"))
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(crear_pregunta("p1"))


def test_agregar_pregunta_con_condicion_a_pregunta_inexistente_falla():
    modelo = crear_modelo_con_dimension()
    pregunta = crear_pregunta("p2")
    pregunta.condicion = CondicionActivacion(
        pregunta_codigo="no-existe", operador="igual", valor="si"
    )
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(pregunta)


def test_agregar_pregunta_con_condicion_a_pregunta_existente():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1"))
    pregunta_condicionada = crear_pregunta("p2")
    pregunta_condicionada.condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="igual", valor="si"
    )
    modelo.agregar_pregunta(pregunta_condicionada)
    assert len(modelo.preguntas) == 2


def test_editar_pregunta_actualiza_solo_campos_enviados():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    modelo.editar_pregunta("p1", peso=Decimal("0.5"))
    assert modelo.preguntas[0].peso == Decimal("0.5")
    assert modelo.preguntas[0].enunciado == "¿Su empresa invierte en I+D?"


def test_editar_pregunta_inexistente_falla():
    modelo = crear_modelo_con_dimension()
    with pytest.raises(ValueError):
        modelo.editar_pregunta("no-existe", peso=Decimal("0.5"))


def test_quitar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    modelo.quitar_pregunta("p1")
    assert modelo.preguntas == []


def test_quitar_pregunta_referenciada_por_condicion_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1"))
    pregunta_condicionada = crear_pregunta("p2")
    pregunta_condicionada.condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="igual", valor="si"
    )
    modelo.agregar_pregunta(pregunta_condicionada)
    with pytest.raises(ValueError):
        modelo.quitar_pregunta("p1")


# R-03: la suma de los pesos de las preguntas de cada dimensión debe totalizar 1 (RF-31)
def test_validar_pesos_preguntas_correctos_no_lanza():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1", peso="0.6"))
    modelo.agregar_pregunta(crear_pregunta("p2", peso="0.4"))
    modelo.validar_pesos_preguntas()  # no debe lanzar


def test_validar_pesos_preguntas_que_no_suman_uno_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1", peso="0.5"))
    with pytest.raises(ValueError):
        modelo.validar_pesos_preguntas()


def test_validar_pesos_dimension_sin_preguntas_falla():
    modelo = crear_modelo_con_dimension()
    with pytest.raises(ValueError):
        modelo.validar_pesos_preguntas()
