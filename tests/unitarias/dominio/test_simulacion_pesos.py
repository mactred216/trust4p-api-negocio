from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               Respuesta, ResultadoDiagnostico)
from src.dominio.entidades.modelo_madurez import (Dimension, ModeloMadurez,
                                                  Nivel, Pregunta)
from src.dominio.servicios.simulacion_pesos import (modelo_con_pesos_simulados,
                                                    simular_diagnostico)


def crear_modelo() -> ModeloMadurez:
    pregunta = lambda codigo, dim: Pregunta(  # noqa: E731
        codigo=codigo,
        dimension_codigo=dim,
        enunciado="?",
        tipo="escala",
        obligatoria=True,
        peso=Decimal("1"),
        en_demo=False,
        orden=1,
    )
    return ModeloMadurez(
        id="m-1",
        version="1",
        nombre="Modelo",
        publicado=True,
        dimensiones=[
            Dimension(codigo="A", nombre="A", peso=Decimal("0.5"), orden=1),
            Dimension(codigo="B", nombre="B", peso=Decimal("0.5"), orden=2),
        ],
        niveles=[
            Nivel(1, "Inicial", "...", Decimal("1"), Decimal("4")),
            Nivel(2, "Gestionado", "...", Decimal("4"), Decimal("7")),
            Nivel(3, "Optimizado", "...", Decimal("7"), Decimal("10")),
        ],
        preguntas=[pregunta("pa", "A"), pregunta("pb", "B")],
    )


def crear_diagnostico() -> Diagnostico:
    """A = 8, B = 2 -> con pesos 0.5/0.5 el índice es 5 (nivel 2)."""
    d = Diagnostico(
        id="d-1",
        empresa_id="e-1",
        empresa_nombre="Empresa",
        usuario_id="u-1",
        modelo_version="1",
        consecutivo=1,
        estado="evaluado",
        respuestas=[
            Respuesta("pa", "A", valor=Decimal("8")),
            Respuesta("pb", "B", valor=Decimal("2")),
        ],
    )
    d.resultado = ResultadoDiagnostico(
        indice_global=Decimal("5"),
        nivel=2,
        nivel_descripcion="...",
        dimensiones=[
            DimensionResultado("A", Decimal("8")),
            DimensionResultado("B", Decimal("2")),
        ],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    return d


def pesos(a, b):
    return {"A": Decimal(a), "B": Decimal(b)}


def test_modelo_simulado_no_modifica_el_original():
    modelo = crear_modelo()

    simulado = modelo_con_pesos_simulados(modelo, pesos("0.9", "0.1"))

    assert [d.peso for d in simulado.dimensiones] == [Decimal("0.9"), Decimal("0.1")]
    assert [d.peso for d in modelo.dimensiones] == [Decimal("0.5"), Decimal("0.5")]


def test_pesos_que_no_suman_uno_se_rechazan():
    with pytest.raises(ValueError, match="debe ser igual a 1"):
        modelo_con_pesos_simulados(crear_modelo(), pesos("0.6", "0.6"))


def test_faltan_pesos_de_dimensiones():
    with pytest.raises(ValueError, match="Faltan pesos"):
        modelo_con_pesos_simulados(crear_modelo(), {"A": Decimal("1")})


def test_dimension_inexistente():
    with pytest.raises(ValueError, match="inexistentes"):
        modelo_con_pesos_simulados(
            crear_modelo(), {**pesos("0.5", "0.5"), "Z": Decimal("0.1")}
        )


def test_simular_con_pesos_originales_no_varia():
    modelo = modelo_con_pesos_simulados(crear_modelo(), pesos("0.5", "0.5"))

    comparacion = simular_diagnostico(crear_diagnostico(), modelo)

    assert comparacion.variacion_indice == Decimal("0.00")
    assert comparacion.cambia_de_nivel is False


def test_simular_pesos_que_suben_el_nivel():
    modelo = modelo_con_pesos_simulados(crear_modelo(), pesos("0.9", "0.1"))

    comparacion = simular_diagnostico(crear_diagnostico(), modelo)

    assert comparacion.indice_original == Decimal("5.00")
    assert comparacion.indice_simulado == Decimal("7.40")
    assert comparacion.variacion_indice == Decimal("2.40")
    assert (comparacion.nivel_original, comparacion.nivel_simulado) == (2, 3)
    assert comparacion.cambia_de_nivel is True


def test_simular_no_altera_el_diagnostico():
    diagnostico = crear_diagnostico()
    modelo = modelo_con_pesos_simulados(crear_modelo(), pesos("0.1", "0.9"))

    simular_diagnostico(diagnostico, modelo)

    assert diagnostico.resultado.indice_global == Decimal("5")
    assert diagnostico.resultado.nivel == 2
    assert diagnostico.estado == "evaluado"
