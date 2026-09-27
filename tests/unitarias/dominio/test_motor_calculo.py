from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import Diagnostico, Respuesta
from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  OpcionPregunta, Pregunta)
from src.dominio.servicios.motor_calculo import (RubricaNoCubreElIndice,
                                                 calcular_nivel,
                                                 calcular_puntaje_dimension,
                                                 calcular_resultado,
                                                 determinar_perfil_cultural)


def crear_pregunta(
    codigo,
    dimension_codigo,
    tipo,
    peso,
    obligatoria=True,
    opciones=None,
    condicion=None,
    activo=True,
) -> Pregunta:
    return Pregunta(
        codigo=codigo,
        dimension_codigo=dimension_codigo,
        enunciado="¿Pregunta?",
        tipo=tipo,
        obligatoria=obligatoria,
        peso=Decimal(str(peso)),
        en_demo=False,
        orden=1,
        opciones=opciones or [],
        condicion=condicion,
        activo=activo,
    )


def crear_respuesta(codigo, dimension, opciones_codigo=None, valor=None, texto=None):
    return Respuesta(
        pregunta_codigo=codigo,
        dimension_codigo=dimension,
        opciones_codigo=opciones_codigo or [],
        valor=Decimal(str(valor)) if valor is not None else None,
        texto=texto,
    )


def crear_modelo_completo() -> ModeloMadurez:
    modelo = ModeloMadurez(
        id="m1", version="1", nombre="Modelo", escala_min=1, escala_max=10
    )
    modelo.dimensiones = [
        Dimension(
            codigo="innovacion", nombre="Innovación", peso=Decimal("0.6"), orden=1
        ),
        Dimension(codigo="procesos", nombre="Procesos", peso=Decimal("0.4"), orden=2),
    ]
    modelo.preguntas = [
        crear_pregunta(
            "p1",
            "innovacion",
            "seleccion_unica",
            0.5,
            opciones=[
                OpcionPregunta(codigo="alta", etiqueta="Alta", valor=Decimal("10")),
                OpcionPregunta(codigo="media", etiqueta="Media", valor=Decimal("5")),
                OpcionPregunta(codigo="baja", etiqueta="Baja", valor=Decimal("1")),
            ],
        ),
        crear_pregunta("p2", "innovacion", "escala", 0.5),
        crear_pregunta("p3", "procesos", "numerica", 0.7),
        crear_pregunta("p4", "procesos", "texto_libre", 0.3),
    ]
    modelo.niveles = [
        Nivel(
            nivel=1,
            nombre="Inicial",
            descripcion="Nivel inicial",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("4"),
        ),
        Nivel(
            nivel=2,
            nombre="En desarrollo",
            descripcion="Nivel medio",
            umbral_min=Decimal("4"),
            umbral_max=Decimal("7"),
        ),
        Nivel(
            nivel=3,
            nombre="Avanzado",
            descripcion="Nivel alto",
            umbral_min=Decimal("7"),
            umbral_max=Decimal("10"),
        ),
    ]
    modelo.ejes_perfil_cultural = [
        EjePerfilCultural(
            codigo="extroversion",
            nombre="Extroversión",
            polo_alto_codigo="E",
            polo_alto_nombre="Extrovertida",
            polo_bajo_codigo="I",
            polo_bajo_nombre="Introvertida",
            dimension_codigo="innovacion",
            umbral=Decimal("5"),
        ),
        EjePerfilCultural(
            codigo="intuicion",
            nombre="Intuición",
            polo_alto_codigo="N",
            polo_alto_nombre="Intuitiva",
            polo_bajo_codigo="S",
            polo_bajo_nombre="Sensorial",
            dimension_codigo="procesos",
            umbral=Decimal("5"),
        ),
        EjePerfilCultural(
            codigo="sentimiento",
            nombre="Sentimiento",
            polo_alto_codigo="F",
            polo_alto_nombre="Sentimental",
            polo_bajo_codigo="T",
            polo_bajo_nombre="Racional",
            dimension_codigo="innovacion",
            umbral=Decimal("7"),
        ),
        EjePerfilCultural(
            codigo="percepcion",
            nombre="Percepción",
            polo_alto_codigo="P",
            polo_alto_nombre="Perceptiva",
            polo_bajo_codigo="J",
            polo_bajo_nombre="Calificadora",
            dimension_codigo="procesos",
            umbral=Decimal("3"),
        ),
    ]
    return modelo


def crear_diagnostico_prueba(respuestas) -> Diagnostico:
    return Diagnostico(
        id="diag-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=1,
        estado="completado",
        respuestas=respuestas,
    )


def test_puntaje_dimension_pondera_por_peso_relativo():
    modelo = crear_modelo_completo()
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["alta"]),  # 10
        crear_respuesta("p2", "innovacion", valor=6),
    ]
    puntaje = calcular_puntaje_dimension("innovacion", modelo.preguntas, respuestas)
    assert puntaje == Decimal("8")  # (10*.5 + 6*.5) / (.5+.5)


def test_puntaje_dimension_excluye_texto_libre_y_renormaliza():
    """El peso de p4 (texto_libre) no diluye el puntaje: se renormaliza
    sobre las preguntas que sí aportan número."""
    modelo = crear_modelo_completo()
    respuestas = [
        crear_respuesta("p3", "procesos", valor=5),
        crear_respuesta("p4", "procesos", texto="mucho texto"),
    ]
    puntaje = calcular_puntaje_dimension("procesos", modelo.preguntas, respuestas)
    assert puntaje == Decimal("5")  # (5*.7) / .7, no (5*.7)/(.7+.3)


def test_puntaje_dimension_seleccion_multiple_promedia_opciones():
    modelo = crear_modelo_completo()
    modelo.preguntas[0] = crear_pregunta(
        "p1",
        "innovacion",
        "seleccion_multiple",
        0.5,
        opciones=modelo.preguntas[0].opciones,
    )
    respuestas = [
        crear_respuesta(
            "p1", "innovacion", opciones_codigo=["alta", "media"]
        ),  # (10+5)/2=7.5
        crear_respuesta("p2", "innovacion", valor=6),
    ]
    puntaje = calcular_puntaje_dimension("innovacion", modelo.preguntas, respuestas)
    assert puntaje == Decimal("6.75")  # (7.5*.5 + 6*.5) / 1


def test_puntaje_dimension_respeta_preguntas_no_aplicables():
    """RF-08: una pregunta bloqueada por una condición no cumplida no cuenta,
    ni su peso ni su respuesta (si la hubiera)."""
    modelo = crear_modelo_completo()
    modelo.preguntas.append(
        crear_pregunta(
            "p5",
            "innovacion",
            "escala",
            0.5,
            condicion=CondicionActivacion(
                pregunta_codigo="p1", operador="igual", valor="baja"
            ),
        )
    )
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["alta"]),
        crear_respuesta("p2", "innovacion", valor=6),
        crear_respuesta("p5", "innovacion", valor=1),  # no debe contarse: p5 bloqueada
    ]
    puntaje = calcular_puntaje_dimension("innovacion", modelo.preguntas, respuestas)
    assert puntaje == Decimal("8")  # igual que sin p5


def test_puntaje_dimension_sin_respuestas_numericas_es_cero():
    modelo = crear_modelo_completo()
    puntaje = calcular_puntaje_dimension("procesos", modelo.preguntas, [])
    assert puntaje == Decimal("0")


def test_calcular_nivel_dentro_de_rango():
    modelo = crear_modelo_completo()
    nivel = calcular_nivel(Decimal("5"), modelo.niveles)
    assert nivel.nombre == "En desarrollo"


def test_calcular_nivel_limite_compartido_toma_el_menor():
    modelo = crear_modelo_completo()
    nivel = calcular_nivel(Decimal("4"), modelo.niveles)
    assert nivel.nivel == 1


def test_calcular_nivel_fuera_de_rango_falla():
    modelo = crear_modelo_completo()
    with pytest.raises(RubricaNoCubreElIndice):
        calcular_nivel(Decimal("15"), modelo.niveles)


def test_calcular_resultado_completo():
    modelo = crear_modelo_completo()
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["alta"]),  # 10
        crear_respuesta("p2", "innovacion", valor=6),  # innovacion = 8
        crear_respuesta("p3", "procesos", valor=5),  # procesos = 5
        crear_respuesta("p4", "procesos", texto="notas"),
    ]
    diagnostico = crear_diagnostico_prueba(respuestas)

    resultado = calcular_resultado(diagnostico, modelo)

    # indice = 8*0.6 + 5*0.4 = 6.8
    assert resultado.indice_global == Decimal("6.8")
    assert resultado.nivel == 2
    assert resultado.nivel_nombre == "En desarrollo"
    assert {d.dimension_codigo: d.puntaje for d in resultado.dimensiones} == {
        "innovacion": Decimal("8"),
        "procesos": Decimal("5"),
    }
    assert resultado.perfil_cultural.codigo == "ENFP"


def test_calcular_resultado_es_reproducible():
    """La prueba que no se negocia (manual de buenas prácticas, sección
    7.2): el mismo conjunto de respuestas siempre produce el mismo índice,
    sin depender del agente de IA (ASR-01)."""
    modelo = crear_modelo_completo()
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["media"]),
        crear_respuesta("p2", "innovacion", valor=4),
        crear_respuesta("p3", "procesos", valor=6),
        crear_respuesta("p4", "procesos", texto="notas"),
    ]
    diagnostico = crear_diagnostico_prueba(respuestas)

    resultado_1 = calcular_resultado(diagnostico, modelo)
    resultado_2 = calcular_resultado(diagnostico, modelo)

    assert resultado_1.indice_global == resultado_2.indice_global
    assert resultado_1.nivel == resultado_2.nivel
    assert resultado_1.dimensiones == resultado_2.dimensiones
    assert resultado_1.perfil_cultural == resultado_2.perfil_cultural


def test_determinar_perfil_cultural_combina_los_cuatro_ejes():
    modelo = crear_modelo_completo()
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["alta"]),  # innovacion=8
        crear_respuesta("p2", "innovacion", valor=6),
        crear_respuesta("p3", "procesos", valor=5),  # procesos=5
        crear_respuesta("p4", "procesos", texto="notas"),
    ]
    diagnostico = crear_diagnostico_prueba(respuestas)

    perfil = determinar_perfil_cultural(diagnostico, modelo)

    assert perfil.codigo == "ENFP"
    assert [e.eje_codigo for e in perfil.ejes] == [
        "extroversion",
        "intuicion",
        "sentimiento",
        "percepcion",
    ]


def test_determinar_perfil_cultural_polo_bajo_cuando_no_alcanza_el_umbral():
    modelo = crear_modelo_completo()
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["media"]),
        crear_respuesta("p2", "innovacion", valor=4),  # innovacion=4.5
        crear_respuesta("p3", "procesos", valor=6),  # procesos=6
        crear_respuesta("p4", "procesos", texto="notas"),
    ]
    diagnostico = crear_diagnostico_prueba(respuestas)

    perfil = determinar_perfil_cultural(diagnostico, modelo)

    assert perfil.codigo == "INTP"


def test_determinar_perfil_cultural_ignora_ejes_no_configurados():
    modelo = crear_modelo_completo()
    modelo.ejes_perfil_cultural = modelo.ejes_perfil_cultural[:1]  # solo extroversion
    respuestas = [
        crear_respuesta("p1", "innovacion", opciones_codigo=["alta"]),
        crear_respuesta("p2", "innovacion", valor=6),
    ]
    diagnostico = crear_diagnostico_prueba(respuestas)

    perfil = determinar_perfil_cultural(diagnostico, modelo)

    assert perfil.codigo == "E"
    assert len(perfil.ejes) == 1
