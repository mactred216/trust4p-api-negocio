from decimal import Decimal

import pytest

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)
from src.dominio.servicios.diagnostico_demo import (AVISO_DEMOSTRACION,
                                                    RespuestaDemo,
                                                    calcular_resultado_demo,
                                                    preguntas_de_demostracion)


def pregunta(codigo, dim, tipo="escala", en_demo=True, obligatoria=True, **kw):
    return Pregunta(
        codigo=codigo,
        dimension_codigo=dim,
        enunciado="?",
        tipo=tipo,
        obligatoria=obligatoria,
        peso=Decimal("0.5"),
        en_demo=en_demo,
        orden=kw.pop("orden", 1),
        **kw,
    )


def crear_modelo() -> ModeloMadurez:
    return ModeloMadurez(
        id="m",
        version="1",
        nombre="M",
        publicado=True,
        dimensiones=[
            Dimension("A", "Dim A", Decimal("0.5"), 1),
            Dimension("B", "Dim B", Decimal("0.3"), 2),
            Dimension("C", "Dim C", Decimal("0.2"), 3),
        ],
        niveles=[
            Nivel(1, "Inicial", "d1", Decimal("1"), Decimal("4")),
            Nivel(2, "Gestionado", "d2", Decimal("4"), Decimal("7")),
            Nivel(3, "Optimizado", "d3", Decimal("7"), Decimal("10")),
        ],
        preguntas=[
            pregunta("pa", "A", orden=1),
            pregunta(
                "pb",
                "B",
                tipo="seleccion_unica",
                orden=2,
                opciones=[
                    OpcionPregunta("alta", "Alta", Decimal("9")),
                    OpcionPregunta("baja", "Baja", Decimal("3")),
                ],
            ),
            pregunta("pc", "C", en_demo=False, orden=3),
            pregunta("pd", "A", tipo="texto_libre", obligatoria=False, orden=4),
            pregunta(
                "pe",
                "C",
                orden=5,
                condicion=CondicionActivacion("pc", "mayor_que", "5"),
            ),
            pregunta("pf", "A", orden=6, activo=False),
        ],
    )


def resp(codigo, **kw):
    return RespuestaDemo(codigo, kw.pop("opciones", []), **kw)


def test_solo_incluye_preguntas_activas_en_demo_sin_dependencias_externas():
    codigos = [p.codigo for p in preguntas_de_demostracion(crear_modelo())]
    assert codigos == ["pa", "pb", "pd"]


def test_calcula_resultado_parcial_con_rubrica_y_aviso():
    resultado = calcular_resultado_demo(
        crear_modelo(),
        [resp("pa", valor=Decimal("8")), resp("pb", opciones=["baja"])],
    )

    # A = 8 (peso 0.5), B = 3 (peso 0.3) -> (4 + 0.9) / 0.8 = 6.125
    assert resultado.indice_global == Decimal("6.13")
    assert resultado.nivel == 2
    assert resultado.nivel_nombre == "Gestionado"
    assert [d.codigo for d in resultado.dimensiones] == ["A", "B"]
    assert resultado.dimensiones_sin_evaluar == ["Dim C"]
    assert resultado.preguntas_respondidas == 2
    assert resultado.total_preguntas == 3
    assert resultado.aviso == AVISO_DEMOSTRACION


def test_texto_libre_opcional_no_aporta_al_indice():
    base = calcular_resultado_demo(
        crear_modelo(),
        [resp("pa", valor=Decimal("8")), resp("pb", opciones=["baja"])],
    )
    con_texto = calcular_resultado_demo(
        crear_modelo(),
        [
            resp("pa", valor=Decimal("8")),
            resp("pb", opciones=["baja"]),
            resp("pd", texto="Comentario"),
        ],
    )
    assert con_texto.indice_global == base.indice_global


def test_pregunta_fuera_de_la_demo_se_rechaza():
    with pytest.raises(ValueError, match="no forma parte"):
        calcular_resultado_demo(crear_modelo(), [resp("pc", valor=Decimal("5"))])


def test_faltan_obligatorias():
    with pytest.raises(ValueError, match="Faltan preguntas obligatorias"):
        calcular_resultado_demo(crear_modelo(), [resp("pa", valor=Decimal("8"))])


def test_valor_fuera_de_escala():
    with pytest.raises(ValueError, match="entre 1 y 10"):
        calcular_resultado_demo(
            crear_modelo(),
            [resp("pa", valor=Decimal("50000")), resp("pb", opciones=["baja"])],
        )


def test_opcion_inexistente():
    with pytest.raises(ValueError, match="no tiene las opciones"):
        calcular_resultado_demo(
            crear_modelo(),
            [resp("pa", valor=Decimal("5")), resp("pb", opciones=["media"])],
        )


def test_seleccion_unica_con_dos_opciones():
    with pytest.raises(ValueError, match="selección única"):
        calcular_resultado_demo(
            crear_modelo(),
            [resp("pa", valor=Decimal("5")), resp("pb", opciones=["alta", "baja"])],
        )


def test_respuesta_repetida():
    with pytest.raises(ValueError, match="repetida"):
        calcular_resultado_demo(
            crear_modelo(),
            [
                resp("pa", valor=Decimal("5")),
                resp("pa", valor=Decimal("6")),
                resp("pb", opciones=["baja"]),
            ],
        )


def test_escala_sin_valor():
    with pytest.raises(ValueError, match="requiere un valor"):
        calcular_resultado_demo(
            crear_modelo(), [resp("pa"), resp("pb", opciones=["baja"])]
        )
