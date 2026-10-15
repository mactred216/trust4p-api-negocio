"""Estadística de la validación QA/QC, sin dependencias externas.

Implementa lo que necesita el cuarto objetivo: coeficiente de correlación
intraclase con intervalo de confianza (Shrout y Fleiss, 1979; McGraw y Wong,
1996), kappa ponderado, correlación de Spearman, sesgo y límites de acuerdo de
Bland-Altman, reducción de tiempo y puntaje del cuestionario SUS.

Se escribe en Python puro para que la herramienta corra en el entorno del
proyecto sin instalar scipy ni numpy. Las funciones de distribución F se
resuelven con la beta incompleta regularizada y una búsqueda por bisección;
las pruebas contrastan el resultado con el ejemplo publicado de Shrout y
Fleiss."""

import math
from collections import Counter
from typing import Optional, Sequence

NIVEL_CONFIANZA = 0.95


# ----------------------------------------------------------------- distribución F
def _beta_continua(a: float, b: float, x: float) -> float:
    """Fracción continua de la beta incompleta (método de Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-16:
            break
    return h


def beta_incompleta(a: float, b: float, x: float) -> float:
    """Función beta incompleta regularizada I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continua(a, b, x) / a
    return 1.0 - front * _beta_continua(b, a, 1.0 - x) / b


def f_acumulada(f: float, d1: float, d2: float) -> float:
    if f <= 0:
        return 0.0
    return beta_incompleta(d1 / 2.0, d2 / 2.0, d1 * f / (d1 * f + d2))


def f_cuantil(p: float, d1: float, d2: float) -> float:
    """Valor f tal que P(F <= f) = p, con F de Fisher-Snedecor (d1, d2)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p debe estar entre 0 y 1")
    bajo, alto = 0.0, 1.0
    while f_acumulada(alto, d1, d2) < p:
        alto *= 2.0
        if alto > 1e12:
            break
    for _ in range(200):
        medio = (bajo + alto) / 2.0
        if f_acumulada(medio, d1, d2) < p:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2.0


# ----------------------------------------------------------------------- ICC
FORMAS_ICC = ("ICC1", "ICC2", "ICC3", "ICC1k", "ICC2k", "ICC3k")


def icc(matriz: Sequence[Sequence[float]], alfa: float = 1 - NIVEL_CONFIANZA) -> dict:
    """ICC de las seis formas de Shrout y Fleiss para una matriz de n sujetos
    (filas) por k evaluadores (columnas). Devuelve, por forma, el estimador y su
    intervalo de confianza; además las medias cuadráticas.

    En este proyecto los dos evaluadores son el sistema y la experta, y el
    estimador de referencia es ICC2 (acuerdo absoluto, efectos aleatorios,
    medición única): penaliza tanto la diferencia de orden como la de nivel."""
    n = len(matriz)
    if n < 3:
        raise ValueError("El ICC exige al menos 3 sujetos")
    k = len(matriz[0])
    if k < 2 or any(len(fila) != k for fila in matriz):
        raise ValueError(
            "Todas las filas deben tener los mismos evaluadores (mínimo 2)"
        )

    total = sum(sum(fila) for fila in matriz)
    media = total / (n * k)
    sst = sum((x - media) ** 2 for fila in matriz for x in fila)
    ssr = k * sum((sum(fila) / k - media) ** 2 for fila in matriz)
    columnas = [sum(matriz[i][j] for i in range(n)) / n for j in range(k)]
    ssc = n * sum((c - media) ** 2 for c in columnas)
    sse = sst - ssr - ssc

    msr = ssr / (n - 1)
    msc = ssc / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    msw = (sst - ssr) / (n * (k - 1))

    resultado: dict = {
        "n": n,
        "k": k,
        "msr": msr,
        "msc": msc,
        "mse": mse,
        "msw": msw,
        "formas": {},
    }
    if msr + (k - 1) * msw == 0 or msr == 0:
        return {**resultado, "definido": False}

    q = 1 - alfa / 2.0

    def f_q(p, a, b):
        return f_cuantil(p, a, b)

    def poner(nombre, estimado, inferior, superior):
        resultado["formas"][nombre] = {
            "estimado": estimado,
            "inferior": inferior,
            "superior": superior,
        }

    # --- ICC(1,1) y ICC(1,k)
    if msw > 0:
        f1 = msr / msw
        df1, df2 = n - 1, n * (k - 1)
        f1_inf = f1 / f_q(q, df1, df2)
        f1_sup = f1 * f_q(q, df2, df1)
        poner(
            "ICC1",
            (msr - msw) / (msr + (k - 1) * msw),
            (f1_inf - 1) / (f1_inf + (k - 1)),
            (f1_sup - 1) / (f1_sup + (k - 1)),
        )
        poner("ICC1k", (msr - msw) / msr, 1 - 1 / f1_inf, 1 - 1 / f1_sup)

    # --- ICC(3,1) y ICC(3,k)
    if mse > 0:
        f3 = msr / mse
        df3 = (n - 1) * (k - 1)
        f3_inf = f3 / f_q(q, n - 1, df3)
        f3_sup = f3 * f_q(q, df3, n - 1)
        poner(
            "ICC3",
            (msr - mse) / (msr + (k - 1) * mse),
            (f3_inf - 1) / (f3_inf + (k - 1)),
            (f3_sup - 1) / (f3_sup + (k - 1)),
        )
        poner("ICC3k", (msr - mse) / msr, 1 - 1 / f3_inf, 1 - 1 / f3_sup)

        # --- ICC(2,1) y ICC(2,k)
        icc2 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
        icc2k = (msr - mse) / (msr + (msc - mse) / n)
        fj = msc / mse
        vn = (
            (k - 1)
            * (n - 1)
            * (k * icc2 * fj + n * (1 + (k - 1) * icc2) - k * icc2) ** 2
        )
        vd = (n - 1) * k**2 * icc2**2 * fj**2 + (
            n * (1 + (k - 1) * icc2) - k * icc2
        ) ** 2
        v = vn / vd
        f2_sup = f_q(q, n - 1, v)
        f2_inf = f_q(q, v, n - 1)
        base = k * msc + (k * n - k - n) * mse
        poner(
            "ICC2",
            icc2,
            n * (msr - f2_sup * mse) / (f2_sup * base + n * msr),
            n * (f2_inf * msr - mse) / (base + n * f2_inf * msr),
        )
        # El intervalo de ICC(2,k) se obtiene transformando el de ICC(2,1).
        formas = resultado["formas"]["ICC2"]
        poner(
            "ICC2k",
            icc2k,
            k * formas["inferior"] / (1 + (k - 1) * formas["inferior"]),
            k * formas["superior"] / (1 + (k - 1) * formas["superior"]),
        )
    elif msr > 0:
        # Sin varianza residual (los evaluadores difieren, a lo sumo, en un
        # desplazamiento constante): ICC3 vale 1, pero ICC2 sigue penalizando
        # ese desplazamiento. Sin varianza residual no hay intervalo analítico.
        poner("ICC3", 1.0, None, None)
        poner("ICC3k", 1.0, None, None)
        poner("ICC2", msr / (msr + k * msc / n), None, None)
        poner("ICC2k", msr / (msr + msc / n), None, None)
    resultado["definido"] = True
    return resultado


# ----------------------------------------------------------- otras medidas de acuerdo
def sesgo_y_limites(a: Sequence[float], b: Sequence[float]) -> dict:
    """Bland-Altman: media de las diferencias (a - b) y límites de acuerdo al 95 %."""
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("Se necesitan al menos dos pares")
    dif = [x - y for x, y in zip(a, b)]
    media = sum(dif) / len(dif)
    sd = math.sqrt(sum((d - media) ** 2 for d in dif) / (len(dif) - 1))
    return {
        "sesgo": media,
        "sd": sd,
        "limite_inferior": media - 1.96 * sd,
        "limite_superior": media + 1.96 * sd,
        "diferencia_absoluta_media": sum(abs(d) for d in dif) / len(dif),
    }


def kappa_ponderado(
    a: Sequence[int], b: Sequence[int], niveles: int, pesos: str = "lineal"
) -> Optional[float]:
    """Kappa ponderado de Cohen entre dos series de niveles 1..niveles."""
    if len(a) != len(b) or not a:
        raise ValueError("Series de distinta longitud o vacías")
    n = len(a)

    def peso(i, j):
        d = abs(i - j) / (niveles - 1)
        return d if pesos == "lineal" else d * d

    ca, cb = Counter(a), Counter(b)
    observado = sum(peso(x, y) for x, y in zip(a, b)) / n
    esperado = sum(
        peso(i, j) * (ca[i] / n) * (cb[j] / n)
        for i in range(1, niveles + 1)
        for j in range(1, niveles + 1)
    )
    if esperado == 0:
        return None
    return 1 - observado / esperado


def _rangos(valores: Sequence[float]) -> list[float]:
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    rangos = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        for t in range(i, j + 1):
            rangos[orden[t]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return rangos


def spearman(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    """Correlación de Spearman (Pearson sobre rangos); None si una serie es constante."""
    if len(a) != len(b) or len(a) < 3:
        raise ValueError("Se necesitan al menos tres pares")
    ra, rb = _rangos(a), _rangos(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return None if den == 0 else num / den


def proporcion_de_acuerdo(
    a: Sequence[int], b: Sequence[int], tolerancia: int = 0
) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("Series de distinta longitud o vacías")
    return sum(1 for x, y in zip(a, b) if abs(x - y) <= tolerancia) / len(a)


# ------------------------------------------------------------- tiempo y usabilidad
def reduccion_de_tiempo(manual: float, sistema: float) -> float:
    """(manual - sistema) / manual, tal como la define el KPI del objetivo 4."""
    if manual <= 0:
        raise ValueError("El tiempo manual debe ser positivo")
    return (manual - sistema) / manual


def puntaje_sus(respuestas: Sequence[int]) -> float:
    """Puntaje SUS (0 a 100) de un participante con 10 respuestas de 1 a 5.
    Ítems impares: respuesta - 1; ítems pares: 5 - respuesta; suma por 2,5."""
    if len(respuestas) != 10 or any(not 1 <= r <= 5 for r in respuestas):
        raise ValueError("El SUS exige 10 respuestas entre 1 y 5")
    suma = sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(respuestas))
    return suma * 2.5


def clasificar_icc(valor: float) -> str:
    """Bandas de interpretación de Koo y Li (2016) para el ICC."""
    if valor < 0.5:
        return "pobre"
    if valor < 0.75:
        return "moderada"
    if valor < 0.9:
        return "buena"
    return "excelente"
