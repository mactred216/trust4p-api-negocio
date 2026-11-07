"""C7: evaluación en segundo plano contra MongoDB real. Una sola evaluación a
la vez por diagnóstico, reprocesos simultáneos sin duplicados y recuperación
de las evaluaciones que una instancia dejó a medias."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from src.aplicacion.casos_uso.evaluar_diagnostico import (
    MOTIVO_INTERRUMPIDA, EvaluarDiagnostico,
    RecuperarEvaluacionesInterrumpidas)
from src.aplicacion.casos_uso.reprocesar_diagnostico import (
    ReprocesarDiagnostico, ReprocesarPendientes)
from src.infraestructura.persistencia.repositorio_mongo_diagnostico import \
    RepositorioMongoDiagnostico
from tests.unitarias.aplicacion.test_evaluar_diagnostico import (
    crear_diagnostico_prueba, crear_mocks_notificacion, crear_modelo_prueba,
    crear_respuesta_agente_valida)

AHORA = lambda: datetime.now(timezone.utc)  # noqa: E731


async def diagnostico_en(db, estado="completado", completado_hace=timedelta(0), **extra):
    d = crear_diagnostico_prueba()
    d.id = None
    d.estado = estado
    d.completado_en = AHORA() - completado_hace
    d = await RepositorioMongoDiagnostico(db).guardar(d)
    if extra:
        await db["diagnosticos"].update_one({"_id": ObjectId(d.id)}, {"$set": extra})
    return d.id


@pytest.mark.asyncio
async def test_dos_reclamos_simultaneos_solo_uno_gana(db):
    repo = RepositorioMongoDiagnostico(db)
    diag = await diagnostico_en(db)
    vence = AHORA() + timedelta(minutes=10)

    ganados = await asyncio.gather(*[repo.reclamar_evaluacion(diag, f"t{i}", vence) for i in range(10)])

    assert sum(ganados) == 1


@pytest.mark.asyncio
async def test_un_reclamo_vencido_puede_retomarse_y_liberar_es_por_token(db):
    repo = RepositorioMongoDiagnostico(db)
    diag = await diagnostico_en(db)
    assert await repo.reclamar_evaluacion(diag, "viejo", AHORA() - timedelta(seconds=1))
    assert await repo.reclamar_evaluacion(diag, "nuevo", AHORA() + timedelta(minutes=10))
    await repo.liberar_evaluacion(diag, "viejo")  # no es suyo: no hace nada
    assert not await repo.reclamar_evaluacion(diag, "otro", AHORA() + timedelta(minutes=10))
    await repo.liberar_evaluacion(diag, "nuevo")
    assert await repo.reclamar_evaluacion(diag, "otro", AHORA() + timedelta(minutes=10))


@pytest.mark.asyncio
async def test_solo_se_reclama_un_diagnostico_pendiente_de_evaluar(db):
    repo = RepositorioMongoDiagnostico(db)
    evaluado = await diagnostico_en(db, estado="evaluado")
    assert not await repo.reclamar_evaluacion(evaluado, "t", AHORA() + timedelta(minutes=10))


@pytest.mark.asyncio
async def test_dos_evaluaciones_simultaneas_llaman_al_agente_una_vez(db):
    """Simula dos instancias (o un reproceso repetido) evaluando a la vez."""
    diag = await diagnostico_en(db)
    llamadas = 0

    async def agente_lento(*_):
        nonlocal llamadas
        llamadas += 1
        await asyncio.sleep(0.3)
        return crear_respuesta_agente_valida()

    def caso_uso():
        repo_modelo = AsyncMock()
        repo_modelo.obtener_por_version.return_value = crear_modelo_prueba()
        agente = AsyncMock()
        agente.evaluar.side_effect = agente_lento
        return EvaluarDiagnostico(RepositorioMongoDiagnostico(db), repo_modelo, agente, *crear_mocks_notificacion())

    await asyncio.gather(caso_uso().ejecutar(diag), caso_uso().ejecutar(diag))

    assert llamadas == 1
    doc = await db["diagnosticos"].find_one({"_id": ObjectId(diag)})
    assert doc["estado"] == "evaluado"
    assert doc["evaluacion_en_curso"] is None


@pytest.mark.asyncio
async def test_reprocesos_simultaneos_del_mismo_diagnostico_solo_uno_pasa(db):
    diag = await diagnostico_en(db, estado="fallido")
    usuarios = AsyncMock()
    from src.dominio.entidades.usuario import Rol, Usuario
    usuarios.obtener_por_id.return_value = Usuario(
        id="adm", correo="a@x.com", clave_hash="x", nombres="A", apellidos="B", rol=Rol(codigo="administrador")
    )

    resultados = await asyncio.gather(
        *[ReprocesarDiagnostico(RepositorioMongoDiagnostico(db), usuarios).ejecutar("adm", diag) for _ in range(5)],
        return_exceptions=True,
    )

    assert sum(1 for r in resultados if not isinstance(r, Exception)) == 1
    # los demás se rechazan: o los ganó la escritura condicional, o ya leyeron
    # el diagnóstico en 'completado'
    assert all(
        isinstance(r, ValueError)
        and ("ya se está reprocesando" in str(r) or "Solo un diagnóstico fallido" in str(r))
        for r in resultados
        if isinstance(r, Exception)
    )


@pytest.mark.asyncio
async def test_recuperar_marca_solo_las_evaluaciones_realmente_perdidas(db):
    plazo = timedelta(minutes=10)
    perdida = await diagnostico_en(db, completado_hace=timedelta(minutes=30))
    reciente = await diagnostico_en(db, completado_hace=timedelta(minutes=2))
    viva = await diagnostico_en(
        db, completado_hace=timedelta(minutes=30),
        evaluacion_en_curso={"token": "t", "iniciada_en": AHORA(), "vence_en": AHORA() + plazo},
    )
    vencida = await diagnostico_en(
        db, completado_hace=timedelta(minutes=30),
        evaluacion_en_curso={"token": "t", "iniciada_en": AHORA() - plazo * 2, "vence_en": AHORA() - plazo},
    )
    reabierta = await diagnostico_en(db, completado_hace=timedelta(days=3), reabierto_en=AHORA())
    evaluada = await diagnostico_en(db, estado="evaluado", completado_hace=timedelta(days=3))

    ids = await RecuperarEvaluacionesInterrumpidas(RepositorioMongoDiagnostico(db), plazo).ejecutar()

    assert sorted(ids) == sorted([perdida, vencida])
    doc = await db["diagnosticos"].find_one({"_id": ObjectId(perdida)})
    assert doc["estado"] == "fallido" and doc["motivo_fallo"] == MOTIVO_INTERRUMPIDA
    for intacto, estado in ((reciente, "completado"), (viva, "completado"), (reabierta, "completado"), (evaluada, "evaluado")):
        assert (await db["diagnosticos"].find_one({"_id": ObjectId(intacto)}))["estado"] == estado
    # repetir no cambia nada (idempotente)
    assert await RecuperarEvaluacionesInterrumpidas(RepositorioMongoDiagnostico(db), plazo).ejecutar() == []


@pytest.mark.asyncio
async def test_reprocesar_pendientes_incluye_las_interrumpidas(db):
    perdida = await diagnostico_en(db, completado_hace=timedelta(hours=1))
    fallida = await diagnostico_en(db, estado="fallido")
    repo = RepositorioMongoDiagnostico(db)

    ids = await ReprocesarPendientes(repo, RecuperarEvaluacionesInterrumpidas(repo, timedelta(minutes=10))).ejecutar()

    assert sorted(ids) == sorted([perdida, fallida])
    for d in (perdida, fallida):
        assert (await db["diagnosticos"].find_one({"_id": ObjectId(d)}))["estado"] == "completado"
