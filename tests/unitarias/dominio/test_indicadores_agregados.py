from decimal import Decimal

import pytest

from src.dominio.servicios.indicadores_agregados import (
    MINIMO_EMPRESAS, MuestraEmpresa, calcular_indicadores, clasificar_tamano,
    filas_para_exportacion, filtrar_muestras)


def muestra(sector="J62", tamano="pequena", nivel=2, indice="6", dim="7"):
    return MuestraEmpresa(
        sector_codigo=sector,
        sector_nombre=f"Sector {sector}",
        tamano=tamano,
        nivel=nivel,
        indice_global=Decimal(indice),
        puntajes_dimension={"innovacion": Decimal(dim)},
    )


@pytest.mark.parametrize(
    "empleados,esperado",
    [
        (None, None),
        (1, "micro"),
        (10, "micro"),
        (11, "pequena"),
        (50, "pequena"),
        (51, "mediana"),
        (200, "mediana"),
        (201, "grande"),
    ],
)
def test_clasificar_tamano(empleados, esperado):
    assert clasificar_tamano(empleados) == esperado


def test_menos_de_tres_empresas_no_presenta_detalle():
    """HU-023 CA-01."""
    resultado = calcular_indicadores([muestra(), muestra()])

    assert resultado.detalle_disponible is False
    assert resultado.mensaje is not None
    assert resultado.total_empresas is None
    assert resultado.por_nivel == []


def test_sin_empresas_tampoco_presenta_detalle():
    assert calcular_indicadores([]).detalle_disponible is False


def test_tres_empresas_presenta_detalle_y_promedios():
    resultado = calcular_indicadores(
        [muestra(indice="5"), muestra(indice="6"), muestra(indice="7")]
    )

    assert MINIMO_EMPRESAS == 3
    assert resultado.detalle_disponible is True
    assert resultado.total_empresas == 3
    assert resultado.indice_promedio == Decimal("6.00")
    assert resultado.promedio_por_dimension == {"innovacion": Decimal("7.00")}


def test_distribucion_por_nivel_en_porcentaje():
    muestras = [muestra(nivel=2)] * 3 + [muestra(nivel=3)] * 3
    resultado = calcular_indicadores(muestras)

    assert [(g.clave, g.empresas, g.porcentaje) for g in resultado.por_nivel] == [
        ("2", 3, Decimal("50.00")),
        ("3", 3, Decimal("50.00")),
    ]


def test_grupo_con_menos_de_tres_empresas_se_suprime():
    """Evita que restar grupos revele a una empresa."""
    muestras = [muestra(nivel=2)] * 4 + [muestra(nivel=3)] * 2
    resultado = calcular_indicadores(muestras)

    assert resultado.total_empresas == 6
    assert [g.clave for g in resultado.por_nivel] == ["2"]


def test_empresas_sin_tamano_no_forman_grupo_de_tamano():
    muestras = [muestra(tamano=None)] * 3
    assert calcular_indicadores(muestras).por_tamano == []


def test_filtrar_por_sector_y_tamano():
    muestras = [
        muestra(sector="J62", tamano="micro"),
        muestra(sector="J62", tamano="pequena"),
        muestra(sector="C10", tamano="micro"),
    ]

    assert len(filtrar_muestras(muestras, sector_codigo="J62")) == 2
    assert len(filtrar_muestras(muestras, tamano="micro")) == 2
    assert len(filtrar_muestras(muestras, "J62", "micro")) == 1
    assert len(filtrar_muestras(muestras)) == 3


def test_filtro_que_deja_menos_de_tres_oculta_el_detalle():
    muestras = [muestra(sector="J62")] * 3 + [muestra(sector="C10")] * 2
    assert calcular_indicadores(filtrar_muestras(muestras)).detalle_disponible
    assert not calcular_indicadores(
        filtrar_muestras(muestras, sector_codigo="C10")
    ).detalle_disponible


def test_exportacion_omite_celdas_pequenas_y_anonimiza():
    muestras = [muestra(nivel=2)] * 3 + [muestra(nivel=3)] * 2
    filas = filas_para_exportacion(muestras)

    assert len(filas) == 1
    assert (
        filas[0].sector_codigo,
        filas[0].tamano,
        filas[0].nivel,
        filas[0].empresas,
    ) == ("J62", "pequena", 2, 3)
    assert not hasattr(filas[0], "empresa_id")
