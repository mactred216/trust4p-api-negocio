from decimal import Decimal, InvalidOperation

from src.dominio.entidades.diagnostico import Respuesta
from src.dominio.entidades.modelo_madurez import CondicionActivacion, Pregunta

"""RF-08/HU-09: lógica adaptativa de bloques de preguntas. Cruza dos agregados
(ModeloMadurez y Diagnostico), por eso vive como servicio de dominio y no
como método de ninguna de las dos entidades."""


def _valor_comparable(respuesta: Respuesta) -> str | None:
    if respuesta.opcion_codigo is not None:
        return respuesta.opcion_codigo
    if respuesta.texto is not None:
        return respuesta.texto
    if respuesta.valor is not None:
        return str(respuesta.valor)
    return None


def evaluar_condicion(
    condicion: CondicionActivacion, respuestas_por_pregunta: dict[str, Respuesta]
) -> bool:
    respuesta = respuestas_por_pregunta.get(condicion.pregunta_codigo)
    if respuesta is None:
        return False

    valor = _valor_comparable(respuesta)
    if valor is None:
        return False

    if condicion.operador == "igual":
        return valor == condicion.valor
    if condicion.operador == "diferente":
        return valor != condicion.valor
    if condicion.operador == "contiene":
        return condicion.valor in valor
    if condicion.operador in ("mayor_que", "menor_que"):
        try:
            valor_num = Decimal(valor)
            umbral = Decimal(condicion.valor)
        except InvalidOperation:
            return False
        return (
            valor_num > umbral
            if condicion.operador == "mayor_que"
            else valor_num < umbral
        )
    return False


def preguntas_aplicables(
    preguntas: list[Pregunta], respuestas: list[Respuesta]
) -> list[Pregunta]:
    """Preguntas activas cuya condición de activación (si tiene) se cumple con
    las respuestas dadas hasta el momento. Una pregunta sin condición siempre
    es aplicable (si está activa)."""
    respuestas_por_pregunta = {r.pregunta_codigo: r for r in respuestas}
    return [
        p
        for p in preguntas
        if p.activo
        and (
            p.condicion is None
            or evaluar_condicion(p.condicion, respuestas_por_pregunta)
        )
    ]
