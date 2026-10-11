from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarPerfilCultura, CrearNuevaVersion, EditarPerfilCultura,
    ModeloNoEncontrado, QuitarPerfilCultura)
from src.dominio.entidades.diagnostico import (Diagnostico, Recomendacion,
                                               Respuesta)
from src.dominio.entidades.modelo_madurez import (EJES_PERFIL_CULTURAL_CODIGOS,
                                                  Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  OpcionPregunta, Pregunta)
from src.dominio.puertos.cliente_servicio_agente import RespuestaAgente

# RF-14: catálogo de perfiles de cultura. El administrador da nombre y
# descripción a cada combinación de polos; el cálculo sigue saliendo de los ejes.


def crear_modelo(publicado: bool = False) -> ModeloMadurez:
    modelo = ModeloMadurez(
        id="m1", version="1", nombre="Modelo", escala_min=1, escala_max=10
    )
    modelo.dimensiones = [
        Dimension(codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1)
    ]
    modelo.preguntas = [
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Qué tanto invierte su empresa en innovación?",
            tipo="seleccion_unica",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
            opciones=[
                OpcionPregunta(codigo="alta", etiqueta="Alta", valor=Decimal("8"))
            ],
        )
    ]
    modelo.niveles = [
        Nivel(
            nivel=1,
            nombre="Único",
            descripcion="Cubre toda la escala",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("10"),
        )
    ]
    # Polos reales de los cuatro ejes; con umbral 5 y puntaje 8 todos caen al alto.
    polos = {
        "extroversion": ("E", "I"),
        "intuicion": ("N", "S"),
        "sentimiento": ("F", "T"),
        "percepcion": ("P", "J"),
    }
    for codigo in EJES_PERFIL_CULTURAL_CODIGOS:
        alto, bajo = polos[codigo]
        modelo.agregar_eje_perfil_cultural(
            EjePerfilCultural(
                codigo=codigo,
                nombre=codigo,
                polo_alto_codigo=alto,
                polo_alto_nombre=f"{alto} nombre",
                polo_bajo_codigo=bajo,
                polo_bajo_nombre=f"{bajo} nombre",
                dimension_codigo="innovacion",
                umbral=Decimal("5"),
            )
        )
    if publicado:
        modelo.publicar("admin-1")
    return modelo


# ---------- dominio ----------


def test_las_combinaciones_salen_de_los_polos_de_los_ejes():
    combinaciones = crear_modelo().combinaciones_perfil_cultural()

    assert len(combinaciones) == 16
    assert len(set(combinaciones)) == 16
    assert "ENFP" in combinaciones and "ISTJ" in combinaciones
    assert all(len(c) == 4 for c in combinaciones)


def test_sin_los_cuatro_ejes_no_hay_combinaciones_ni_se_puede_definir_un_perfil():
    modelo = crear_modelo()
    modelo.quitar_eje_perfil_cultural("percepcion")

    assert modelo.combinaciones_perfil_cultural() == []
    with pytest.raises(ValueError, match="Configure primero los cuatro ejes"):
        modelo.agregar_perfil_cultura("ENFP", "Innovador", "Descripción")


def test_agrega_un_perfil_del_catalogo():
    modelo = crear_modelo()

    modelo.agregar_perfil_cultura("ENFP", "Innovador nato", "Descripción del perfil")

    perfil = modelo.perfil_cultura_para("ENFP")
    assert perfil.nombre == "Innovador nato"
    assert perfil.descripcion == "Descripción del perfil"
    assert perfil.activo is True


def test_no_acepta_una_combinacion_que_no_existe():
    with pytest.raises(ValueError, match="no es una combinación válida"):
        crear_modelo().agregar_perfil_cultura("ZZZZ", "X", "Y")


def test_no_acepta_el_mismo_perfil_dos_veces():
    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "A", "B")

    with pytest.raises(ValueError, match="ya está definido"):
        modelo.agregar_perfil_cultura("ENFP", "C", "D")


def test_edita_nombre_y_descripcion():
    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "A", "B")

    modelo.editar_perfil_cultura("ENFP", nombre="Nuevo", descripcion="Otra")

    perfil = modelo.perfil_cultura_para("ENFP")
    assert (perfil.nombre, perfil.descripcion) == ("Nuevo", "Otra")


def test_un_perfil_desactivado_no_se_usa_pero_se_conserva():
    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "A", "B")

    modelo.editar_perfil_cultura("ENFP", activo=False)

    assert modelo.perfil_cultura_para("ENFP") is None
    assert len(modelo.perfiles_cultura) == 1
    modelo.editar_perfil_cultura("ENFP", activo=True)
    assert modelo.perfil_cultura_para("ENFP") is not None


def test_quita_un_perfil():
    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "A", "B")

    modelo.quitar_perfil_cultura("ENFP")

    assert modelo.perfiles_cultura == []
    with pytest.raises(ValueError, match="No existe el perfil"):
        modelo.quitar_perfil_cultura("ENFP")


def test_una_version_publicada_no_se_modifica():
    modelo = crear_modelo(publicado=True)

    for accion in (
        lambda: modelo.agregar_perfil_cultura("ENFP", "A", "B"),
        lambda: modelo.editar_perfil_cultura("ENFP", nombre="X"),
        lambda: modelo.quitar_perfil_cultura("ENFP"),
    ):
        with pytest.raises(ValueError):
            accion()


def test_no_se_publica_si_un_perfil_ya_no_corresponde_a_los_polos():
    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "A", "B")
    modelo.editar_eje_perfil_cultural("extroversion", polo_alto_codigo="X")

    with pytest.raises(ValueError, match="ya no corresponden a los polos"):
        modelo.publicar("admin-1")


def test_publica_con_el_catalogo_vacio_o_valido():
    crear_modelo().publicar("admin-1")  # sin catálogo: el agente describe

    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "A", "B")
    modelo.publicar("admin-1")
    assert modelo.publicado


# ---------- casos de uso ----------


@pytest.mark.asyncio
async def test_casos_de_uso_agregar_editar_y_quitar():
    modelo = crear_modelo()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    await AgregarPerfilCultura(repo).ejecutar("m1", "ENFP", "A", "B")
    await EditarPerfilCultura(repo).ejecutar("m1", "ENFP", nombre="C")
    assert modelo.perfil_cultura_para("ENFP").nombre == "C"
    await QuitarPerfilCultura(repo).ejecutar("m1", "ENFP")

    assert modelo.perfiles_cultura == []
    assert repo.actualizar.await_count == 3


@pytest.mark.asyncio
async def test_los_casos_de_uso_fallan_si_el_modelo_no_existe():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    with pytest.raises(ModeloNoEncontrado):
        await AgregarPerfilCultura(repo).ejecutar("x", "ENFP", "A", "B")
    with pytest.raises(ModeloNoEncontrado):
        await EditarPerfilCultura(repo).ejecutar("x", "ENFP", nombre="A")
    with pytest.raises(ModeloNoEncontrado):
        await QuitarPerfilCultura(repo).ejecutar("x", "ENFP")


@pytest.mark.asyncio
async def test_la_nueva_version_copia_el_catalogo_y_es_independiente_del_origen():
    origen = crear_modelo()
    origen.agregar_perfil_cultura("ENFP", "A", "B")
    origen.editar_perfil_cultura("ENFP", activo=False)
    origen.publicar("admin-1")
    repo = AsyncMock()
    repo.obtener_por_id.return_value = origen
    repo.obtener_por_version.return_value = None
    repo.guardar.side_effect = lambda m: m

    clon = await CrearNuevaVersion(repo).ejecutar("m1")

    assert [(p.codigo, p.nombre, p.descripcion, p.activo) for p in clon.perfiles_cultura] == [
        ("ENFP", "A", "B", False)
    ]
    clon.editar_perfil_cultura("ENFP", nombre="Cambiado")
    assert origen.perfiles_cultura[0].nombre == "A"


# ---------- evaluación ----------


def _evaluar(modelo):
    diagnostico = Diagnostico(
        id="diag-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=1,
        estado="completado",
        respuestas=[
            Respuesta(
                pregunta_codigo="p1",
                dimension_codigo="innovacion",
                opciones_codigo=["alta"],
            )
        ],
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo
    cliente = AsyncMock()
    cliente.evaluar.return_value = RespuestaAgente(
        perfil_cultura_descripcion="Texto del agente",
        dimensiones_observaciones={"innovacion": "Observación"},
        lienzo_negocio={"segmentos_clientes": "..."},
        sintesis="Síntesis",
        recomendaciones=[
            Recomendacion(
                origen="agente",
                dimension_codigo="innovacion",
                titulo="T",
                contenido="C",
                prioridad=1,
            )
        ],
    )
    caso_uso = EvaluarDiagnostico(
        repo_diagnostico, repo_modelo, cliente, AsyncMock(), AsyncMock(), AsyncMock()
    )
    return diagnostico, caso_uso


@pytest.mark.asyncio
async def test_el_resultado_usa_nombre_y_descripcion_del_catalogo():
    modelo = crear_modelo()  # con puntaje 8 y umbral 5 todos los ejes van al polo alto
    modelo.agregar_perfil_cultura("ENFP", "Innovador nato", "Descripción curada")
    diagnostico, caso_uso = _evaluar(modelo)

    await caso_uso.ejecutar("diag-1")

    assert diagnostico.estado == "evaluado"
    assert diagnostico.resultado.perfil_cultura.codigo == "ENFP"
    assert diagnostico.resultado.perfil_cultura.nombre == "Innovador nato"
    assert diagnostico.resultado.perfil_cultura.descripcion == "Descripción curada"


@pytest.mark.asyncio
async def test_sin_perfil_en_el_catalogo_la_descripcion_la_pone_el_agente():
    diagnostico, caso_uso = _evaluar(crear_modelo())

    await caso_uso.ejecutar("diag-1")

    assert diagnostico.resultado.perfil_cultura.nombre is None
    assert diagnostico.resultado.perfil_cultura.descripcion == "Texto del agente"


@pytest.mark.asyncio
async def test_un_perfil_desactivado_no_se_aplica():
    modelo = crear_modelo()
    modelo.agregar_perfil_cultura("ENFP", "Innovador nato", "Descripción curada")
    modelo.editar_perfil_cultura("ENFP", activo=False)
    diagnostico, caso_uso = _evaluar(modelo)

    await caso_uso.ejecutar("diag-1")

    assert diagnostico.resultado.perfil_cultura.nombre is None
    assert diagnostico.resultado.perfil_cultura.descripcion == "Texto del agente"
