from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import obtener_caso_uso_obtener_version_vigente
from src.api.main import app
from src.aplicacion.casos_uso.gestionar_modelo_madurez import \
    ModeloNoEncontrado
from src.dominio.entidades.modelo_madurez import (Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)


def modelo_con_dimensiones_desordenadas() -> ModeloMadurez:
    modelo = ModeloMadurez(
        id="m-1",
        version="2026.9",
        nombre="Modelo de prueba",
        publicado=True,
        escala_min=0,
        escala_max=100,
    )
    modelo.dimensiones = [
        Dimension(codigo="b", nombre="Segunda", peso=Decimal("0.4"), orden=2),
        Dimension(
            codigo="a",
            nombre="Primera",
            peso=Decimal("0.6"),
            orden=1,
            descripcion="La primera",
        ),
    ]
    modelo.niveles = [
        Nivel(
            nivel=2,
            nombre="Dos",
            descripcion="d2",
            umbral_min=Decimal("50"),
            umbral_max=Decimal("100"),
        ),
        Nivel(
            nivel=1,
            nombre="Uno",
            descripcion="d1",
            umbral_min=Decimal("0"),
            umbral_max=Decimal("50"),
        ),
    ]
    modelo.preguntas = [
        Pregunta(
            codigo="q",
            dimension_codigo="a",
            enunciado="Interna",
            tipo="seleccion_unica",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
            opciones=[OpcionPregunta(codigo="x", etiqueta="x", valor=Decimal("1"))],
        )
    ]
    return modelo


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


def con_caso_de_uso(resultado=None, error=None):
    caso_uso = AsyncMock()
    if error:
        caso_uso.ejecutar.side_effect = error
    else:
        caso_uso.ejecutar.return_value = resultado
    app.dependency_overrides[obtener_caso_uso_obtener_version_vigente] = (
        lambda: caso_uso
    )


def test_es_publico_y_devuelve_dimensiones_y_niveles_en_orden(cliente):
    con_caso_de_uso(modelo_con_dimensiones_desordenadas())

    r = cliente.get("/v1/modelo-vigente")  # sin cookie de sesión

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["version"] == "2026.9"
    assert [d["nombre"] for d in cuerpo["dimensiones"]] == ["Primera", "Segunda"]
    assert cuerpo["dimensiones"][0]["descripcion"] == "La primera"
    assert [n["numero"] for n in cuerpo["niveles"]] == [1, 2]
    assert cuerpo["escala_max"] == 100


def test_no_expone_preguntas_ni_configuracion_interna(cliente):
    con_caso_de_uso(modelo_con_dimensiones_desordenadas())

    cuerpo = cliente.get("/v1/modelo-vigente").json()

    assert "preguntas" not in cuerpo
    assert "ejes_perfil_cultural" not in cuerpo
    assert "Interna" not in str(cuerpo)


def test_sin_version_publicada_responde_404(cliente):
    con_caso_de_uso(error=ModeloNoEncontrado())

    r = cliente.get("/v1/modelo-vigente")

    assert r.status_code == 404
