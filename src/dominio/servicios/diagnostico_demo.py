from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.dominio.entidades.diagnostico import Respuesta
from src.dominio.entidades.modelo_madurez import ModeloMadurez, Pregunta
from src.dominio.servicios.logica_adaptativa import preguntas_aplicables
from src.dominio.servicios.motor_calculo import (ESTRATEGIAS_POR_TIPO,
                                                 RubricaNoCubreElIndice,
                                                 calcular_nivel,
                                                 calcular_puntaje_dimension)

"""RF-49 (HU-007): diagnóstico de demostración. Función pura y sin estado: toma
el subconjunto público del modelo vigente (preguntas con en_demo) y las
respuestas del visitante y devuelve un resultado orientativo reutilizando el
motor determinístico (ADR-005) y la rúbrica del modelo (RF-32). No hay entidad
Diagnostico, ni identificador de empresa, ni persistencia: lo que se calcula
solo vive durante la petición (HU-007 CA-02)."""

AVISO_DEMOSTRACION = (
    "Resultado orientativo de demostración: se calculó solo con un subconjunto "
    "de preguntas, no se almacena y no constituye un diagnóstico de empresa."
)

TIPOS_NUMERICOS = {"escala", "numerica"}


@dataclass
class RespuestaDemo:
    pregunta_codigo: str
    opciones_codigo: list[str]
    valor: Decimal | None = None
    texto: str | None = None


@dataclass
class DimensionDemo:
    codigo: str
    nombre: str
    puntaje: Decimal


@dataclass
class ResultadoDemo:
    indice_global: Decimal
    nivel: int
    nivel_nombre: str
    nivel_descripcion: str
    dimensiones: list[DimensionDemo]
    dimensiones_sin_evaluar: list[str]
    preguntas_respondidas: int
    total_preguntas: int
    aviso: str = AVISO_DEMOSTRACION


def preguntas_de_demostracion(modelo: ModeloMadurez) -> list[Pregunta]:
    """Preguntas activas marcadas en_demo. Se descartan las que dependen (por
    condición de activación) de una pregunta que no está en la demostración,
    porque el visitante nunca podría activarlas."""
    demo = [p for p in modelo.preguntas if p.activo and p.en_demo]
    estable = False
    while not estable:
        codigos = {p.codigo for p in demo}
        depurada = [
            p
            for p in demo
            if p.condicion is None or p.condicion.pregunta_codigo in codigos
        ]
        estable = len(depurada) == len(demo)
        demo = depurada
    return sorted(demo, key=lambda p: p.orden)


def _validar_respuesta(
    respuesta: RespuestaDemo, pregunta: Pregunta, modelo: ModeloMadurez
) -> None:
    if pregunta.tipo in ("seleccion_unica", "seleccion_multiple"):
        if not respuesta.opciones_codigo:
            raise ValueError(f"La pregunta '{pregunta.codigo}' requiere una opción")
        if pregunta.tipo == "seleccion_unica" and len(respuesta.opciones_codigo) > 1:
            raise ValueError(
                f"La pregunta '{pregunta.codigo}' es de selección única: "
                "solo admite una opción"
            )
        invalidas = set(respuesta.opciones_codigo) - {
            o.codigo for o in pregunta.opciones
        }
        if invalidas:
            raise ValueError(
                f"La pregunta '{pregunta.codigo}' no tiene las opciones {sorted(invalidas)}"
            )
    elif pregunta.tipo in TIPOS_NUMERICOS:
        if respuesta.valor is None:
            raise ValueError(f"La pregunta '{pregunta.codigo}' requiere un valor")
        if not (modelo.escala_min <= respuesta.valor <= modelo.escala_max):
            raise ValueError(
                f"El valor de la pregunta '{pregunta.codigo}' debe estar entre "
                f"{modelo.escala_min} y {modelo.escala_max}"
            )
    elif pregunta.tipo == "texto_libre" and not respuesta.texto:
        raise ValueError(f"La pregunta '{pregunta.codigo}' requiere un texto")


def calcular_resultado_demo(
    modelo: ModeloMadurez, respuestas_demo: list[RespuestaDemo]
) -> ResultadoDemo:
    preguntas = preguntas_de_demostracion(modelo)
    por_codigo = {p.codigo: p for p in preguntas}

    vistos: set[str] = set()
    respuestas: list[Respuesta] = []
    for r in respuestas_demo:
        pregunta = por_codigo.get(r.pregunta_codigo)
        if pregunta is None:
            raise ValueError(
                f"La pregunta '{r.pregunta_codigo}' no forma parte de la demostración"
            )
        if r.pregunta_codigo in vistos:
            raise ValueError(f"La pregunta '{r.pregunta_codigo}' está repetida")
        vistos.add(r.pregunta_codigo)
        _validar_respuesta(r, pregunta, modelo)
        respuestas.append(
            Respuesta(
                pregunta_codigo=r.pregunta_codigo,
                dimension_codigo=pregunta.dimension_codigo,
                opciones_codigo=r.opciones_codigo,
                valor=r.valor,
                texto=r.texto,
            )
        )

    aplicables = preguntas_aplicables(preguntas, respuestas)
    faltantes = [
        p.codigo for p in aplicables if p.obligatoria and p.codigo not in vistos
    ]
    if faltantes:
        raise ValueError(
            f"Faltan preguntas obligatorias por responder: {', '.join(sorted(faltantes))}"
        )

    por_dimension = {d.codigo: d for d in modelo.dimensiones}
    respuestas_por_pregunta = {r.pregunta_codigo: r for r in respuestas}
    dimensiones: list[DimensionDemo] = []
    sin_evaluar: list[str] = []
    for dimension in sorted(modelo.dimensiones, key=lambda d: d.orden):
        tiene_aporte = any(
            p.dimension_codigo == dimension.codigo
            and p.codigo in respuestas_por_pregunta
            and ESTRATEGIAS_POR_TIPO[p.tipo].puntuar(
                respuestas_por_pregunta[p.codigo], p
            )
            is not None
            for p in aplicables
        )
        if tiene_aporte:
            dimensiones.append(
                DimensionDemo(
                    codigo=dimension.codigo,
                    nombre=dimension.nombre,
                    puntaje=calcular_puntaje_dimension(
                        dimension.codigo, preguntas, respuestas
                    ),
                )
            )
        else:
            sin_evaluar.append(dimension.nombre)

    if not dimensiones:
        raise ValueError("Las respuestas no aportan ningún valor numérico")

    suma_pesos = sum((por_dimension[d.codigo].peso for d in dimensiones), Decimal("0"))
    indice = (
        sum(
            (d.puntaje * por_dimension[d.codigo].peso for d in dimensiones),
            Decimal("0"),
        )
        / suma_pesos
    )

    try:
        nivel = calcular_nivel(indice, modelo.niveles)
    except RubricaNoCubreElIndice as e:
        raise ValueError(str(e))

    return ResultadoDemo(
        indice_global=indice.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        nivel=nivel.nivel,
        nivel_nombre=nivel.nombre,
        nivel_descripcion=nivel.descripcion,
        dimensiones=[
            DimensionDemo(
                d.codigo,
                d.nombre,
                d.puntaje.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            )
            for d in dimensiones
        ],
        dimensiones_sin_evaluar=sin_evaluar,
        preguntas_respondidas=len(respuestas),
        total_preguntas=len(preguntas),
    )
