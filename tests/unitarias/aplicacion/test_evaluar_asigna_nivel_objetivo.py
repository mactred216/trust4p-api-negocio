from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.dominio.entidades.diagnostico import (Diagnostico, Recomendacion,
                                               Respuesta)
from src.dominio.entidades.modelo_madurez import (Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)
from src.dominio.entidades.usuario import Rol, Usuario
from src.dominio.puertos.cliente_servicio_agente import RespuestaAgente

# Las recomendaciones del agente son las tareas para llegar al siguiente nivel.


def modelo(niveles: int) -> ModeloMadurez:
    m = ModeloMadurez(id="m1", version="1", nombre="M", escala_min=0, escala_max=100)
    m.dimensiones = [Dimension(codigo="d", nombre="D", peso=Decimal("1"), orden=1)]
    m.preguntas = [
        Pregunta(
            codigo="p1", dimension_codigo="d", enunciado="¿?", tipo="seleccion_unica",
            obligatoria=True, peso=Decimal("1"), en_demo=False, orden=1,
            opciones=[OpcionPregunta(codigo="x", etiqueta="X", valor=Decimal("45"))],
        )
    ]
    ancho = Decimal(100) / niveles
    m.niveles = [
        Nivel(nivel=i + 1, nombre=f"N{i + 1}", descripcion="d", umbral_min=ancho * i, umbral_max=ancho * (i + 1))
        for i in range(niveles)
    ]
    return m


async def evaluar(niveles: int):
    diagnostico = Diagnostico(
        id="d-1", empresa_id="e", empresa_nombre="E", usuario_id="u-1", modelo_version="1",
        consecutivo=1, estado="completado",
        respuestas=[Respuesta(pregunta_codigo="p1", dimension_codigo="d", opciones_codigo=["x"])],
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo(niveles)
    cliente = AsyncMock()
    cliente.evaluar.return_value = RespuestaAgente(
        perfil_cultura_descripcion="p", dimensiones_observaciones={}, lienzo_negocio={}, sintesis="s",
        recomendaciones=[
            Recomendacion(origen="agente", titulo="A", contenido="c"),
            Recomendacion(origen="agente", titulo="B", contenido="c"),
        ],
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = Usuario(
        id="u-1", correo="a@x.com", clave_hash="h", nombres="A", apellidos="B",
        rol=Rol(codigo="representante"), empresa_id="e",
    )
    repo_usuario.listar_por_rol.return_value = []
    caso = EvaluarDiagnostico(repo_diagnostico, repo_modelo, cliente, repo_usuario, AsyncMock(), AsyncMock())
    await caso.ejecutar("d-1")
    return diagnostico


@pytest.mark.asyncio
async def test_las_recomendaciones_del_agente_apuntan_al_siguiente_nivel():
    d = await evaluar(niveles=10)  # índice 45 -> nivel 5 de 10

    assert d.estado == "evaluado" and d.resultado.nivel == 5
    assert [r.nivel_objetivo for r in d.recomendaciones] == [6, 6]
    assert all(r.estado == "pendiente" for r in d.recomendaciones)


@pytest.mark.asyncio
async def test_en_el_nivel_maximo_de_la_rubrica_no_hay_nivel_al_que_apuntar():
    d = await evaluar(niveles=1)  # una sola banda: ya está en el máximo

    assert d.resultado.nivel == 1
    assert [r.nivel_objetivo for r in d.recomendaciones] == [None, None]
