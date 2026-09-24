from decimal import Decimal

import pytest

from src.dominio.entidades.modelo_madurez import Dimension, ModeloMadurez


def crear_modelo_prueba(publicado: bool = False) -> ModeloMadurez:
    return ModeloMadurez(
        id="modelo-1", version="v1", nombre="Modelo inicial", publicado=publicado
    )


def crear_dimension(codigo="innovacion", peso="0.5", orden=1) -> Dimension:
    return Dimension(
        codigo=codigo, nombre="Innovación", peso=Decimal(peso), orden=orden
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
