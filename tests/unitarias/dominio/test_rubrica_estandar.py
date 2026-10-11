from decimal import Decimal

import pytest

from src.dominio.catalogo_rubrica import NIVELES_ESTANDAR, rubrica_estandar
from src.dominio.entidades.modelo_madurez import ModeloMadurez
from src.dominio.servicios.motor_calculo import calcular_nivel

# Rúbrica estándar: 10 niveles de igual amplitud sobre la escala del modelo.


def test_son_diez_niveles_con_nombre_y_descripcion():
    niveles = rubrica_estandar(0, 100)

    assert [n.nivel for n in niveles] == list(range(1, 11))
    assert len(NIVELES_ESTANDAR) == 10
    assert all(n.nombre.strip() and n.descripcion.strip() for n in niveles)
    assert len({n.nombre for n in niveles}) == 10


def test_con_escala_0_a_100_cada_nivel_abarca_diez_puntos():
    rangos = [(n.umbral_min, n.umbral_max) for n in rubrica_estandar(0, 100)]

    assert rangos == [(Decimal(i * 10), Decimal((i + 1) * 10)) for i in range(10)]


def test_con_escala_1_a_10_las_bandas_son_exactas():
    niveles = rubrica_estandar(1, 10)

    assert niveles[0].umbral_min == Decimal("1")
    assert niveles[0].umbral_max == Decimal("1.9")
    assert niveles[-1].umbral_max == Decimal("10")


@pytest.mark.parametrize("escala", [(0, 100), (1, 10), (0, 5), (1, 7), (0, 1000)])
def test_cubre_toda_la_escala_sin_huecos_ni_solapamientos(escala):
    niveles = rubrica_estandar(*escala)
    modelo = ModeloMadurez(id="m", version="1", nombre="M", escala_min=escala[0], escala_max=escala[1])
    modelo.niveles = niveles

    modelo.validar_niveles()  # la misma regla que se exige al publicar

    assert niveles[0].umbral_min == Decimal(escala[0])
    assert niveles[-1].umbral_max == Decimal(escala[1])
    assert all(a.umbral_max == b.umbral_min for a, b in zip(niveles, niveles[1:]))


@pytest.mark.parametrize(
    "indice,nivel",
    [(0, 1), (9.99, 1), (10, 1), (10.01, 2), (20, 2), (25, 3), (50, 5), (75, 8), (89.9, 9), (90, 9), (90.1, 10), (100, 10)],
)
def test_el_nivel_de_un_indice_y_los_limites_pertenecen_al_nivel_inferior(indice, nivel):
    assert calcular_nivel(Decimal(str(indice)), rubrica_estandar(0, 100)).nivel == nivel


def test_reemplazar_niveles_sustituye_la_rubrica_de_un_borrador():
    modelo = ModeloMadurez(id="m", version="1", nombre="M", escala_min=0, escala_max=100)
    modelo.niveles = rubrica_estandar(0, 100)[:3]

    modelo.reemplazar_niveles(rubrica_estandar(0, 100))

    assert len(modelo.niveles) == 10


def test_una_version_publicada_no_cambia_de_rubrica():
    modelo = ModeloMadurez(id="m", version="1", nombre="M", escala_min=0, escala_max=100, publicado=True)

    with pytest.raises(ValueError):
        modelo.reemplazar_niveles(rubrica_estandar(0, 100))
