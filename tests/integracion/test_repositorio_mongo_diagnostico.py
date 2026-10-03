from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               Recomendacion, Respuesta,
                                               ResultadoDiagnostico)
from src.infraestructura.persistencia.repositorio_mongo_diagnostico import \
    RepositorioMongoDiagnostico


def crear_diagnostico_prueba(
    empresa_id="emp-integracion-1", consecutivo=1
) -> Diagnostico:
    return Diagnostico(
        id=None,
        empresa_id=empresa_id,
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="v1",
        consecutivo=consecutivo,
        respuestas=[
            Respuesta(
                pregunta_codigo="p1",
                dimension_codigo="innovacion",
                opciones_codigo=["alta"],
                valor=Decimal("3"),
            )
        ],
    )


@pytest.mark.asyncio
async def test_guardar_y_obtener_por_id_conserva_respuestas(db):
    repo = RepositorioMongoDiagnostico(db)
    diagnostico = await repo.guardar(crear_diagnostico_prueba())

    recuperado = await repo.obtener_por_id(diagnostico.id)

    assert recuperado is not None
    assert recuperado.empresa_nombre == "InnovaTech"
    assert len(recuperado.respuestas) == 1
    assert recuperado.respuestas[0].valor == Decimal("3")


@pytest.mark.asyncio
async def test_obtener_en_curso_por_empresa_ignora_cerrados(db):
    repo = RepositorioMongoDiagnostico(db)
    cerrado = crear_diagnostico_prueba(consecutivo=1)
    cerrado.estado = "cerrado"
    await repo.guardar(cerrado)

    en_curso = crear_diagnostico_prueba(consecutivo=2)
    await repo.guardar(en_curso)

    recuperado = await repo.obtener_en_curso_por_empresa("emp-integracion-1")

    assert recuperado is not None
    assert recuperado.consecutivo == 2


@pytest.mark.asyncio
async def test_obtener_en_curso_por_empresa_sin_ninguno_devuelve_none(db):
    repo = RepositorioMongoDiagnostico(db)
    cerrado = crear_diagnostico_prueba()
    cerrado.estado = "cerrado"
    await repo.guardar(cerrado)

    assert await repo.obtener_en_curso_por_empresa("emp-integracion-1") is None


@pytest.mark.asyncio
async def test_contar_por_empresa(db):
    repo = RepositorioMongoDiagnostico(db)
    await repo.guardar(crear_diagnostico_prueba(consecutivo=1))
    d2 = crear_diagnostico_prueba(consecutivo=1)
    d2.estado = "cerrado"
    await repo.guardar(d2)

    assert await repo.contar_por_empresa("emp-integracion-1") == 2
    assert await repo.contar_por_empresa("empresa-sin-diagnosticos") == 0


@pytest.mark.asyncio
async def test_listar_por_empresa_ordena_por_consecutivo_descendente(db):
    repo = RepositorioMongoDiagnostico(db)
    await repo.guardar(crear_diagnostico_prueba(consecutivo=1))
    await repo.guardar(crear_diagnostico_prueba(consecutivo=2))

    diagnosticos = await repo.listar_por_empresa("emp-integracion-1")

    assert [d.consecutivo for d in diagnosticos] == [2, 1]


@pytest.mark.asyncio
async def test_actualizar_persiste_nueva_respuesta(db):
    repo = RepositorioMongoDiagnostico(db)
    diagnostico = await repo.guardar(crear_diagnostico_prueba())

    diagnostico.registrar_respuesta(
        Respuesta(pregunta_codigo="p2", dimension_codigo="cultura", texto="Sí, mucho"),
        {"p1", "p2"},
    )
    await repo.actualizar(diagnostico)

    recuperado = await repo.obtener_por_id(diagnostico.id)
    assert len(recuperado.respuestas) == 2
    assert recuperado.porcentaje_avance == 100


@pytest.mark.asyncio
async def test_actualizar_persiste_diagnostico_completado(db):
    repo = RepositorioMongoDiagnostico(db)
    diagnostico = await repo.guardar(crear_diagnostico_prueba())
    diagnostico.porcentaje_avance = 100
    diagnostico.marcar_completado()

    await repo.actualizar(diagnostico)

    recuperado = await repo.obtener_por_id(diagnostico.id)
    assert recuperado.estado == "completado"
    assert recuperado.completado_en is not None


@pytest.mark.asyncio
async def test_obtener_por_id_con_formato_invalido_devuelve_none(db):
    repo = RepositorioMongoDiagnostico(db)

    assert await repo.obtener_por_id("no-es-un-object-id") is None


@pytest.mark.asyncio
async def test_actualizar_persiste_resultado_y_recomendaciones_de_evaluacion(db):
    """HU-038: el resultado narrativo del agente y las recomendaciones deben
    sobrevivir un ciclo de guardar/leer, incluyendo los Decimal del índice,
    los puntajes por dimensión y el objeto anidado perfil_cultura."""
    repo = RepositorioMongoDiagnostico(db)
    diagnostico = await repo.guardar(crear_diagnostico_prueba())
    diagnostico.porcentaje_avance = 100
    diagnostico.marcar_completado()
    resultado = ResultadoDiagnostico(
        indice_global=Decimal("7.2"),
        nivel=2,
        nivel_descripcion="...",
        dimensiones=[DimensionResultado(codigo="innovacion", puntaje=Decimal("8"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    diagnostico.registrar_resultado_calculado(resultado)
    recomendaciones = [
        Recomendacion(
            origen="agente",
            dimension_codigo="innovacion",
            titulo="Título",
            contenido="Contenido",
            prioridad=1,
        )
    ]
    diagnostico.marcar_evaluado(
        perfil_cultura_descripcion="Descripción del perfil",
        dimensiones_observaciones={"innovacion": "Observación"},
        lienzo_negocio={"segmentos_clientes": "..."},
        sintesis="Síntesis",
        recomendaciones=recomendaciones,
    )

    await repo.actualizar(diagnostico)
    recuperado = await repo.obtener_por_id(diagnostico.id)

    assert recuperado.estado == "evaluado"
    assert recuperado.evaluado_en is not None
    assert recuperado.resultado.indice_global == Decimal("7.2")
    assert recuperado.resultado.dimensiones[0].puntaje == Decimal("8")
    assert recuperado.resultado.dimensiones[0].observacion == "Observación"
    assert recuperado.resultado.perfil_cultura.codigo == "ENFP"
    assert recuperado.resultado.perfil_cultura.descripcion == "Descripción del perfil"
    assert recuperado.resultado.sintesis == "Síntesis"
    assert recuperado.resultado.generado_en is not None
    assert len(recuperado.recomendaciones) == 1
    assert recuperado.recomendaciones[0].titulo == "Título"
    assert recuperado.recomendaciones[0].origen == "agente"
    assert recuperado.recomendaciones[0].visible is True
    assert recuperado.recomendaciones[0].creado_en is not None


@pytest.mark.asyncio
async def test_actualizar_persiste_diagnostico_fallido_conservando_resultado(db):
    """ASR-02: el resultado determinístico ya calculado debe sobrevivir un
    ciclo de guardar/leer incluso cuando el diagnóstico queda 'fallido'."""
    repo = RepositorioMongoDiagnostico(db)
    diagnostico = await repo.guardar(crear_diagnostico_prueba())
    diagnostico.porcentaje_avance = 100
    diagnostico.marcar_completado()
    diagnostico.registrar_resultado_calculado(
        ResultadoDiagnostico(
            indice_global=Decimal("7.2"),
            nivel=2,
            nivel_descripcion="...",
            dimensiones=[DimensionResultado(codigo="innovacion", puntaje=Decimal("8"))],
            perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
        )
    )
    diagnostico.marcar_fallido("El servicio del agente no respondió")

    await repo.actualizar(diagnostico)
    recuperado = await repo.obtener_por_id(diagnostico.id)

    assert recuperado.estado == "fallido"
    assert recuperado.motivo_fallo == "El servicio del agente no respondió"
    assert recuperado.resultado is not None
    assert recuperado.resultado.indice_global == Decimal("7.2")
    assert recuperado.resultado.perfil_cultura.codigo == "ENFP"
    assert recuperado.resultado.sintesis is None


@pytest.mark.asyncio
async def test_listar_por_modelo_version_filtra_por_version(db):
    repo = RepositorioMongoDiagnostico(db)
    await repo.guardar(crear_diagnostico_prueba(empresa_id="emp-a", consecutivo=1))
    await repo.guardar(crear_diagnostico_prueba(empresa_id="emp-b", consecutivo=1))
    otra_version = crear_diagnostico_prueba(empresa_id="emp-c", consecutivo=1)
    otra_version.modelo_version = "v2"
    await repo.guardar(otra_version)

    diagnosticos = await repo.listar_por_modelo_version("v1")

    assert sorted(d.empresa_id for d in diagnosticos) == ["emp-a", "emp-b"]
    assert await repo.listar_por_modelo_version("v-inexistente") == []
