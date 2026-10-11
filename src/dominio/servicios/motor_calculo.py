from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.dominio.entidades.diagnostico import Diagnostico, Respuesta
from src.dominio.entidades.modelo_madurez import (ORDEN_EJES_PERFIL_CULTURAL,
                                                  ModeloMadurez, Nivel,
                                                  Pregunta)
from src.dominio.servicios.logica_adaptativa import preguntas_aplicables

"""RF-12/RF-13 (HU-013/HU-014), ADR-005: motor de cálculo determinístico del
índice de madurez. Vive en el núcleo de dominio y no invoca al modelo de
lenguaje ni a ningún servicio externo — solo depende de Diagnostico y
ModeloMadurez, lo que permite probarlo por unidad sin dependencias y
garantiza que el mismo conjunto de respuestas siempre produzca el mismo
índice (ASR-01). El perfil de cultura, el lienzo de negocio y las
recomendaciones (RF-14, RF-15, RF-16) son generados por el agente a partir
del resultado de este motor y no se calculan aquí."""


class EstrategiaPuntuacion(ABC):
    """Patrón Estrategia (ADR-005): cada tipo de pregunta sabe convertir su
    propia respuesta en un valor dentro de la escala del modelo."""

    @abstractmethod
    def puntuar(self, respuesta: Respuesta, pregunta: Pregunta) -> Optional[Decimal]:
        """None si la respuesta no aporta un valor numérico al índice."""
        ...


class PuntuacionPorOpcion(EstrategiaPuntuacion):
    """seleccion_unica/seleccion_multiple: el valor de la opción marcada: si
    se marcó más de una (selección múltiple), el promedio de sus valores."""

    def puntuar(self, respuesta: Respuesta, pregunta: Pregunta) -> Optional[Decimal]:
        valores_por_opcion = {o.codigo: o.valor for o in pregunta.opciones}
        valores = [
            valores_por_opcion[codigo]
            for codigo in respuesta.opciones_codigo
            if codigo in valores_por_opcion
        ]
        if not valores:
            return None
        return sum(valores, Decimal("0")) / len(valores)


class PuntuacionDirecta(EstrategiaPuntuacion):
    """escala/numerica: el valor ingresado ya está expresado en la escala
    del modelo (escala_min..escala_max), no requiere conversión."""

    def puntuar(self, respuesta: Respuesta, pregunta: Pregunta) -> Optional[Decimal]:
        return respuesta.valor


class SinPuntuacionNumerica(EstrategiaPuntuacion):
    """texto_libre: no aporta valor numérico al índice. El texto se remite
    sin resumir al agente (RF-36), que es quien lo interpreta; la capa
    determinística no puede convertirlo en un número sin perder información."""

    def puntuar(self, respuesta: Respuesta, pregunta: Pregunta) -> Optional[Decimal]:
        return None


ESTRATEGIAS_POR_TIPO: dict[str, EstrategiaPuntuacion] = {
    "seleccion_unica": PuntuacionPorOpcion(),
    "seleccion_multiple": PuntuacionPorOpcion(),
    "escala": PuntuacionDirecta(),
    "numerica": PuntuacionDirecta(),
    "texto_libre": SinPuntuacionNumerica(),
}


@dataclass
class PuntajeDimension:
    dimension_codigo: str
    puntaje: Decimal


@dataclass
class EjeCultural:
    eje_codigo: str
    polo_codigo: str
    polo_nombre: str


@dataclass
class PerfilCultural:
    """RF-14: solo la determinación (qué código aplica) es del motor de
    cálculo — la descripción narrativa la escribe el agente a partir de
    este código, buscándolo en la base de conocimiento."""

    codigo: str
    ejes: list[EjeCultural]


def determinar_perfil_cultural(
    diagnostico: Diagnostico, modelo: ModeloMadurez
) -> PerfilCultural:
    """RF-14: para cada uno de los cuatro ejes del marco teórico, determina
    hacia qué polo se inclina la empresa según el puntaje de la dimensión
    que el administrador asoció a ese eje, y arma el código combinado."""
    ejes_por_codigo = {e.codigo: e for e in modelo.ejes_perfil_cultural}
    resultado_ejes = []
    for codigo_eje in ORDEN_EJES_PERFIL_CULTURAL:
        eje = ejes_por_codigo.get(codigo_eje)
        if eje is None:
            continue
        puntaje = calcular_puntaje_dimension(
            eje.dimension_codigo, modelo.preguntas, diagnostico.respuestas
        )
        if puntaje >= eje.umbral:
            resultado_ejes.append(
                EjeCultural(codigo_eje, eje.polo_alto_codigo, eje.polo_alto_nombre)
            )
        else:
            resultado_ejes.append(
                EjeCultural(codigo_eje, eje.polo_bajo_codigo, eje.polo_bajo_nombre)
            )
    codigo = "".join(e.polo_codigo for e in resultado_ejes)
    return PerfilCultural(codigo=codigo, ejes=resultado_ejes)


@dataclass
class ResultadoCalculo:
    """Lo que produce el motor de cálculo (RF-12/RF-13/RF-14). Los campos
    puramente narrativos del resultado completo (descripción del perfil de
    cultura, lienzo, recomendaciones, síntesis) los añade el agente aparte,
    conforme al ADR-005, y no se modelan en esta clase."""

    indice_global: Decimal
    nivel: int
    nivel_nombre: str
    nivel_descripcion: str
    dimensiones: list[PuntajeDimension]
    perfil_cultural: PerfilCultural


class RubricaNoCubreElIndice(Exception):
    """Ningún nivel de la rúbrica publicada cubre el índice calculado."""


def _puntuar_respuesta(respuesta: Respuesta, pregunta: Pregunta) -> Optional[Decimal]:
    estrategia = ESTRATEGIAS_POR_TIPO.get(pregunta.tipo)
    if estrategia is None:
        return None
    return estrategia.puntuar(respuesta, pregunta)


def calcular_puntaje_dimension(
    dimension_codigo: str, preguntas: list[Pregunta], respuestas: list[Respuesta]
) -> Decimal:
    """RF-13: promedio ponderado de las preguntas de la dimensión con aporte
    numérico, usando el peso relativo de cada pregunta (RF-31/R-03)
    renormalizado sobre el subconjunto que sí aporta número — excluye
    texto_libre y las preguntas no aplicables por la lógica adaptativa
    (RF-08), para que su peso no reste valor alcanzable a la dimensión."""
    respuestas_por_pregunta = {r.pregunta_codigo: r for r in respuestas}
    preguntas_dimension = [
        p
        for p in preguntas_aplicables(preguntas, respuestas)
        if p.dimension_codigo == dimension_codigo
    ]

    suma_ponderada = Decimal("0")
    suma_pesos = Decimal("0")
    for pregunta in preguntas_dimension:
        respuesta = respuestas_por_pregunta.get(pregunta.codigo)
        if respuesta is None:
            continue
        valor = _puntuar_respuesta(respuesta, pregunta)
        if valor is None:
            continue
        suma_ponderada += valor * pregunta.peso
        suma_pesos += pregunta.peso

    if suma_pesos == 0:
        return Decimal("0")
    return suma_ponderada / suma_pesos


def calcular_nivel(indice_global: Decimal, niveles: list[Nivel]) -> Nivel:
    """RF-32: el nivel cuya rúbrica cubre el índice calculado. Si el índice
    cae exactamente en el límite compartido por dos niveles, se asigna al de
    umbral menor (los niveles se evalúan en orden ascendente)."""
    for nivel in sorted(niveles, key=lambda n: n.nivel):
        if nivel.umbral_min <= indice_global <= nivel.umbral_max:
            return nivel
    raise RubricaNoCubreElIndice(
        f"Ningún nivel de la rúbrica cubre el índice calculado ({indice_global})"
    )


def calcular_resultado(
    diagnostico: Diagnostico, modelo: ModeloMadurez
) -> ResultadoCalculo:
    """RF-12+RF-13, ADR-005: motor de cálculo determinístico del índice de
    madurez. No invoca al modelo de lenguaje ni a ningún adaptador."""
    dimensiones = [
        PuntajeDimension(
            dimension_codigo=dimension.codigo,
            puntaje=calcular_puntaje_dimension(
                dimension.codigo, modelo.preguntas, diagnostico.respuestas
            ),
        )
        for dimension in modelo.dimensiones
    ]

    peso_por_dimension = {d.codigo: d.peso for d in modelo.dimensiones}
    indice_global = sum(
        (pd.puntaje * peso_por_dimension[pd.dimension_codigo] for pd in dimensiones),
        Decimal("0"),
    )

    nivel = calcular_nivel(indice_global, modelo.niveles)
    perfil_cultural = determinar_perfil_cultural(diagnostico, modelo)

    return ResultadoCalculo(
        indice_global=indice_global,
        nivel=nivel.nivel,
        nivel_nombre=nivel.nombre,
        nivel_descripcion=nivel.descripcion,
        dimensiones=dimensiones,
        perfil_cultural=perfil_cultural,
    )
