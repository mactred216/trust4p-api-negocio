"""La herramienta de validación QA/QC se contrasta con resultados publicados.

El ejemplo de Shrout y Fleiss (1979, tabla 2: 6 sujetos, 4 jueces) tiene valores
de referencia ampliamente reproducidos (p. ej. psych::ICC de R), así que sirve
para comprobar que el cálculo del ICC y de sus intervalos es correcto."""

import pytest

from scripts.validacion import estadistica as est

SHROUT_FLEISS = [
    [9, 2, 5, 8],
    [6, 1, 3, 2],
    [8, 4, 6, 8],
    [7, 1, 2, 6],
    [10, 5, 6, 9],
    [6, 2, 4, 7],
]


def test_cuantil_f_coincide_con_tablas():
    # Valores de tabla: F(0,975; 5, 18) = 3,3820 y F(0,95; 3, 10) = 3,7083.
    assert est.f_cuantil(0.975, 5, 18) == pytest.approx(3.3820, abs=1e-3)
    assert est.f_cuantil(0.95, 3, 10) == pytest.approx(3.7083, abs=1e-3)


@pytest.mark.parametrize(
    "forma, estimado, inferior, superior",
    [
        ("ICC1", 0.17, -0.13, 0.72),
        ("ICC2", 0.29, 0.02, 0.76),
        ("ICC3", 0.71, 0.34, 0.95),
        ("ICC1k", 0.44, -0.88, 0.91),
        ("ICC2k", 0.62, 0.07, 0.93),
        ("ICC3k", 0.91, 0.68, 0.99),
    ],
)
def test_icc_reproduce_el_ejemplo_de_shrout_y_fleiss(
    forma, estimado, inferior, superior
):
    r = est.icc(SHROUT_FLEISS)["formas"][forma]
    assert r["estimado"] == pytest.approx(estimado, abs=0.01)
    assert r["inferior"] == pytest.approx(inferior, abs=0.015)
    assert r["superior"] == pytest.approx(superior, abs=0.015)


def test_icc_de_acuerdo_perfecto_es_uno():
    matriz = [[10, 10], [40, 40], [70, 70], [90, 90]]
    r = est.icc(matriz)
    assert r["formas"]["ICC2"]["estimado"] == pytest.approx(1.0)


def test_icc_penaliza_el_sesgo_sistematico_pero_no_el_orden():
    # El sistema puntúa siempre 20 puntos más: el orden es idéntico (ICC3 = 1)
    # pero el acuerdo absoluto (ICC2) baja.
    matriz = [[30, 50], [45, 65], [60, 80], [75, 95]]
    formas = est.icc(matriz)["formas"]
    assert formas["ICC2"]["estimado"] < formas["ICC3"]["estimado"]
    assert formas["ICC3"]["estimado"] == pytest.approx(1.0)


def test_icc_exige_tres_sujetos_y_dos_evaluadores():
    with pytest.raises(ValueError):
        est.icc([[1, 2], [3, 4]])
    with pytest.raises(ValueError):
        est.icc([[1], [2], [3]])


def test_sesgo_y_limites_de_acuerdo():
    r = est.sesgo_y_limites([60, 70, 80, 90], [50, 70, 85, 80])
    assert r["sesgo"] == pytest.approx(3.75)
    assert r["limite_inferior"] < r["sesgo"] < r["limite_superior"]


def test_kappa_ponderado():
    assert est.kappa_ponderado([1, 2, 3, 4], [1, 2, 3, 4], 4) == pytest.approx(1.0)
    parcial = est.kappa_ponderado([1, 2, 3, 4], [1, 2, 4, 4], 4)
    assert 0 < parcial < 1


def test_spearman_y_acuerdo_de_niveles():
    assert est.spearman([10, 20, 30, 40], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert est.spearman([10, 20, 30, 40], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert est.spearman([1, 1, 1], [1, 2, 3]) is None
    assert est.proporcion_de_acuerdo(
        [3, 5, 7], [3, 6, 9], tolerancia=1
    ) == pytest.approx(2 / 3)


def test_reduccion_de_tiempo_es_la_del_kpi():
    assert est.reduccion_de_tiempo(240, 60) == pytest.approx(0.75)
    with pytest.raises(ValueError):
        est.reduccion_de_tiempo(0, 10)


def test_puntaje_sus_extremos_y_validacion():
    mejor = [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]
    peor = [1, 5, 1, 5, 1, 5, 1, 5, 1, 5]
    neutro = [3] * 10
    assert est.puntaje_sus(mejor) == 100
    assert est.puntaje_sus(peor) == 0
    assert est.puntaje_sus(neutro) == 50
    with pytest.raises(ValueError):
        est.puntaje_sus([3] * 9)
