from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarDimension, AgregarNivel, AgregarPregunta, ConsultarModelo,
    CrearModeloMadurez, CrearNuevaVersion, DesactivarPregunta, EditarDimension,
    EditarNivel, EditarPregunta, ListarModelos, ModeloNoEncontrado,
    ObtenerVersionVigente, Publicar, QuitarDimension, QuitarNivel,
    ReactivarPregunta, VersionDuplicada)
from src.dominio.entidades.modelo_madurez import (EJES_PERFIL_CULTURAL_CODIGOS,
                                                  Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  Pregunta)


def crear_modelo_prueba() -> ModeloMadurez:
    return ModeloMadurez(id="modelo-1", version="v1", nombre="Modelo inicial")


def crear_modelo_con_dimension() -> ModeloMadurez:
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(
        Dimension(codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1)
    )
    return modelo


def crear_modelo_publicable() -> ModeloMadurez:
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )
    )
    modelo.agregar_nivel(
        Nivel(
            nivel=1,
            nombre="Único",
            descripcion="Nivel único",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("10"),
        )
    )
    for codigo in EJES_PERFIL_CULTURAL_CODIGOS:
        modelo.agregar_eje_perfil_cultural(
            EjePerfilCultural(
                codigo=codigo,
                nombre=codigo,
                polo_alto_codigo="A",
                polo_alto_nombre=f"{codigo} alto",
                polo_bajo_codigo="B",
                polo_bajo_nombre=f"{codigo} bajo",
                dimension_codigo="innovacion",
                umbral=Decimal("5"),
            )
        )
    return modelo


@pytest.mark.asyncio
async def test_crear_modelo_madurez():
    repo = AsyncMock()
    repo.obtener_por_version.return_value = None
    repo.guardar.side_effect = lambda m: m

    caso_uso = CrearModeloMadurez(repo)
    modelo = await caso_uso.ejecutar(version="v1", nombre="Modelo inicial")

    assert modelo.version == "v1"
    repo.guardar.assert_called_once()


@pytest.mark.asyncio
async def test_crear_modelo_con_version_duplicada_falla():
    repo = AsyncMock()
    repo.obtener_por_version.return_value = crear_modelo_prueba()

    caso_uso = CrearModeloMadurez(repo)
    with pytest.raises(VersionDuplicada):
        await caso_uso.ejecutar(version="v1", nombre="Modelo inicial")
    repo.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_listar_modelos():
    repo = AsyncMock()
    repo.listar.return_value = [crear_modelo_prueba()]

    caso_uso = ListarModelos(repo)
    modelos = await caso_uso.ejecutar()

    assert len(modelos) == 1


@pytest.mark.asyncio
async def test_consultar_modelo_existente():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_prueba()

    caso_uso = ConsultarModelo(repo)
    modelo = await caso_uso.ejecutar("modelo-1")

    assert modelo.id == "modelo-1"


@pytest.mark.asyncio
async def test_consultar_modelo_inexistente_lanza_excepcion():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = ConsultarModelo(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar("no-existe")


@pytest.mark.asyncio
async def test_agregar_dimension():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_prueba()

    caso_uso = AgregarDimension(repo)
    modelo = await caso_uso.ejecutar(
        "modelo-1", codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1
    )

    assert len(modelo.dimensiones) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_dimension_a_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = AgregarDimension(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar(
            "no-existe",
            codigo="innovacion",
            nombre="Innovación",
            peso=Decimal("1"),
            orden=1,
        )


@pytest.mark.asyncio
async def test_editar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(
        Dimension(
            codigo="innovacion", nombre="Innovación", peso=Decimal("0.5"), orden=1
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = EditarDimension(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "innovacion", peso=Decimal("0.8"))

    assert resultado.dimensiones[0].peso == Decimal("0.8")
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_quitar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(
        Dimension(codigo="innovacion", nombre="Innovación", peso=Decimal("1"), orden=1)
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = QuitarDimension(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "innovacion")

    assert resultado.dimensiones == []
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_pregunta():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_con_dimension()

    caso_uso = AgregarPregunta(repo)
    modelo = await caso_uso.ejecutar(
        "modelo-1",
        codigo="p1",
        dimension_codigo="innovacion",
        enunciado="¿Invierte en I+D?",
        tipo="escala",
        obligatoria=True,
        peso=Decimal("1"),
        en_demo=False,
        orden=1,
    )

    assert len(modelo.preguntas) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_pregunta_a_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = AgregarPregunta(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar(
            "no-existe",
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )


@pytest.mark.asyncio
async def test_editar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = EditarPregunta(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "p1", peso=Decimal("0.5"))

    assert resultado.preguntas[0].peso == Decimal("0.5")
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_desactivar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = DesactivarPregunta(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "p1")

    assert resultado.preguntas[0].activo is False
    assert len(resultado.preguntas) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_reactivar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(
        Pregunta(
            codigo="p1",
            dimension_codigo="innovacion",
            enunciado="¿Invierte en I+D?",
            tipo="escala",
            obligatoria=True,
            peso=Decimal("1"),
            en_demo=False,
            orden=1,
            activo=False,
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = ReactivarPregunta(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "p1")

    assert resultado.preguntas[0].activo is True
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_nivel():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_modelo_prueba()

    caso_uso = AgregarNivel(repo)
    modelo = await caso_uso.ejecutar(
        "modelo-1",
        nivel=1,
        nombre="Inicial",
        descripcion="Sin proceso formal",
        umbral_min=Decimal("1"),
        umbral_max=Decimal("5"),
    )

    assert len(modelo.niveles) == 1
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_nivel_a_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = AgregarNivel(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar(
            "no-existe",
            nivel=1,
            nombre="Inicial",
            descripcion="Sin proceso formal",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("5"),
        )


@pytest.mark.asyncio
async def test_editar_nivel():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(
        Nivel(
            nivel=1,
            nombre="Inicial",
            descripcion="Sin proceso formal",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("5"),
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = EditarNivel(repo)
    resultado = await caso_uso.ejecutar("modelo-1", 1, umbral_max=Decimal("6"))

    assert resultado.niveles[0].umbral_max == Decimal("6")
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_quitar_nivel():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(
        Nivel(
            nivel=1,
            nombre="Inicial",
            descripcion="Sin proceso formal",
            umbral_min=Decimal("1"),
            umbral_max=Decimal("5"),
        )
    )
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = QuitarNivel(repo)
    resultado = await caso_uso.ejecutar("modelo-1", 1)

    assert resultado.niveles == []
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_publicar_modelo_completo():
    modelo = crear_modelo_publicable()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = Publicar(repo)
    resultado = await caso_uso.ejecutar("modelo-1", "admin-1")

    assert resultado.publicado is True
    assert resultado.publicado_por == "admin-1"
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_publicar_modelo_incompleto_falla():
    modelo = crear_modelo_con_dimension()  # sin preguntas ni niveles
    repo = AsyncMock()
    repo.obtener_por_id.return_value = modelo

    caso_uso = Publicar(repo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("modelo-1", "admin-1")
    repo.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_publicar_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = Publicar(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar("no-existe", "admin-1")


@pytest.mark.asyncio
async def test_obtener_version_vigente():
    repo = AsyncMock()
    repo.obtener_vigente.return_value = crear_modelo_publicable()

    caso_uso = ObtenerVersionVigente(repo)
    modelo = await caso_uso.ejecutar()

    assert modelo.id == "modelo-1"


@pytest.mark.asyncio
async def test_obtener_version_vigente_sin_ninguna_publicada_falla():
    repo = AsyncMock()
    repo.obtener_vigente.return_value = None

    caso_uso = ObtenerVersionVigente(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar()


@pytest.mark.asyncio
async def test_crear_nueva_version_clona_configuracion():
    origen = crear_modelo_publicable()
    origen.publicar("admin-1")
    repo = AsyncMock()
    repo.obtener_por_id.return_value = origen
    repo.obtener_por_version.return_value = None
    repo.guardar.side_effect = lambda m: m

    caso_uso = CrearNuevaVersion(repo)
    clon = await caso_uso.ejecutar("modelo-1")

    assert clon.version == "v2"
    assert clon.publicado is False
    assert clon.id is None
    assert len(clon.dimensiones) == 1
    assert len(clon.preguntas) == 1
    assert len(clon.niveles) == 1
    # el clon es independiente: modificarlo no debe afectar al origen
    clon.dimensiones[0].peso = Decimal("0.5")
    assert origen.dimensiones[0].peso == Decimal("1")


@pytest.mark.asyncio
async def test_crear_nueva_version_evita_colision_de_version():
    origen = crear_modelo_publicable()
    origen.publicar("admin-1")
    repo = AsyncMock()
    repo.obtener_por_id.return_value = origen
    # "v2" ya existe (p.ej. una versión creada y luego descartada); debe saltar a "v3"
    repo.obtener_por_version.side_effect = lambda v: object() if v == "v2" else None
    repo.guardar.side_effect = lambda m: m

    caso_uso = CrearNuevaVersion(repo)
    clon = await caso_uso.ejecutar("modelo-1")

    assert clon.version == "v3"


@pytest.mark.asyncio
async def test_crear_nueva_version_de_modelo_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = CrearNuevaVersion(repo)
    with pytest.raises(ModeloNoEncontrado):
        await caso_uso.ejecutar("no-existe")


@pytest.mark.asyncio
async def test_crear_nueva_version_sin_digito_final_agrega_sufijo():
    origen = crear_modelo_publicable()
    origen.version = "piloto"
    origen.publicar("admin-1")
    repo = AsyncMock()
    repo.obtener_por_id.return_value = origen
    repo.obtener_por_version.return_value = None
    repo.guardar.side_effect = lambda m: m

    caso_uso = CrearNuevaVersion(repo)
    clon = await caso_uso.ejecutar("modelo-1")

    assert clon.version == "piloto-2"
