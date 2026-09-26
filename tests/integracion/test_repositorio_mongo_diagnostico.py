from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import Diagnostico, Respuesta
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
