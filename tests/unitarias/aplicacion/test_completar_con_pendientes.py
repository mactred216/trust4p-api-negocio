from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_diagnostico import (
    CompletarDiagnostico, PreguntasPendientes)
from src.dominio.entidades.diagnostico import Diagnostico, Respuesta
from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, ModeloMadurez,
                                                  Pregunta)
from src.dominio.entidades.usuario import Rol, Usuario


def pregunta(codigo, obligatoria=True, condicion=None):
    return Pregunta(
        codigo=codigo,
        dimension_codigo="d1",
        enunciado="?",
        tipo="escala",
        obligatoria=obligatoria,
        peso=Decimal("0.25"),
        en_demo=False,
        orden=1,
        condicion=condicion,
    )


def armar(respondidas, con_modelo=True):
    modelo = ModeloMadurez(
        id="m",
        version="1",
        nombre="M",
        dimensiones=[Dimension("d1", "D", Decimal("1"), 1)],
        preguntas=[
            pregunta("p1"),
            pregunta("p2"),
            pregunta("p3", obligatoria=False),
            pregunta("p4", condicion=CondicionActivacion("p1", "mayor_que", "5")),
        ],
    )
    diagnostico = Diagnostico(
        id="d",
        empresa_id="e",
        empresa_nombre="E",
        usuario_id="u",
        modelo_version="1",
        consecutivo=1,
        porcentaje_avance=50,
        respuestas=[
            Respuesta(c, "d1", valor=Decimal(v)) for c, v in respondidas.items()
        ],
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = Usuario(
        id="u",
        correo="u@x.com",
        clave_hash="h",
        nombres="U",
        apellidos="U",
        rol=Rol("representante"),
        empresa_id="e",
    )
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo
    return CompletarDiagnostico(
        repo_diagnostico, repo_usuario, repo_modelo if con_modelo else None
    )


@pytest.mark.asyncio
async def test_indica_cuales_obligatorias_faltan():
    """HU-008 CA-02."""
    caso_uso = armar({"p1": "3"})

    with pytest.raises(PreguntasPendientes) as e:
        await caso_uso.ejecutar("u", "d")

    assert e.value.codigos == ["p2"]
    assert "p2" in str(e.value)


@pytest.mark.asyncio
async def test_incluye_las_condicionales_que_se_activaron():
    caso_uso = armar({"p1": "9", "p2": "5"})

    with pytest.raises(PreguntasPendientes) as e:
        await caso_uso.ejecutar("u", "d")

    assert e.value.codigos == ["p4"]


@pytest.mark.asyncio
async def test_no_cuenta_las_opcionales_ni_las_no_aplicables():
    caso_uso = armar({})

    with pytest.raises(PreguntasPendientes) as e:
        await caso_uso.ejecutar("u", "d")

    assert e.value.codigos == ["p1", "p2"]


@pytest.mark.asyncio
async def test_sin_repositorio_de_modelo_mantiene_el_mensaje_generico():
    caso_uso = armar({"p1": "3"}, con_modelo=False)

    with pytest.raises(ValueError) as e:
        await caso_uso.ejecutar("u", "d")

    assert not isinstance(e.value, PreguntasPendientes)


@pytest.mark.asyncio
async def test_un_diagnostico_ya_completado_no_reporta_pendientes():
    caso_uso = armar({"p1": "3", "p2": "4"})
    caso_uso._diagnosticos.obtener_por_id.return_value.estado = "completado"

    with pytest.raises(ValueError) as e:
        await caso_uso.ejecutar("u", "d")

    assert not isinstance(e.value, PreguntasPendientes)
