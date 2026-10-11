from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from bson import ObjectId

from src.dominio.entidades.diagnostico import (AvanceNivel, Diagnostico,
                                               DimensionResultado,
                                               PerfilCulturaResultado,
                                               Recomendacion,
                                               ResultadoDiagnostico)
from src.infraestructura.persistencia.repositorio_mongo_diagnostico import \
    RepositorioMongoDiagnostico


def diagnostico(recomendaciones):
    d = Diagnostico(
        id=None, empresa_id="emp-1", empresa_nombre="InnovaTech", usuario_id="u-1",
        modelo_version="2026.2", consecutivo=1, estado="evaluado",
    )
    d.resultado = ResultadoDiagnostico(
        indice_global=Decimal("25"), nivel=3, nivel_descripcion="x",
        dimensiones=[DimensionResultado(codigo="proposito", puntaje=Decimal("30"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    d.recomendaciones = recomendaciones
    return d


@pytest.mark.asyncio
async def test_las_tareas_conservan_estado_fecha_nivel_e_identificador(db):
    repo = RepositorioMongoDiagnostico(db)
    ahora = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    tarea = Recomendacion(
        origen="consultor", titulo="Capacitar", contenido="Detalle", estado="completada",
        fecha_limite=date(2026, 12, 1), nivel_objetivo=4, actualizado_en=ahora, completada_en=ahora,
    )
    d = diagnostico([tarea])
    d.nivel_alcanzado = 4
    d.avances_de_nivel = [AvanceNivel(nivel=4, alcanzado_en=ahora, consultor_id="c-1", consultor_nombre="Julia Herrera")]

    guardado = await repo.guardar(d)
    leido = await repo.obtener_por_id(guardado.id)

    r = leido.recomendaciones[0]
    assert (r.id, r.estado, r.fecha_limite, r.nivel_objetivo) == (tarea.id, "completada", date(2026, 12, 1), 4)
    assert r.completada_en is not None and r.actualizado_en is not None
    assert leido.nivel_alcanzado == 4
    assert [(a.nivel, a.consultor_nombre) for a in leido.avances_de_nivel] == [(4, "Julia Herrera")]


@pytest.mark.asyncio
async def test_una_tarea_sin_fecha_ni_avances_vuelve_vacia(db):
    repo = RepositorioMongoDiagnostico(db)
    guardado = await repo.guardar(diagnostico([Recomendacion(origen="agente", titulo="A", contenido="c")]))

    leido = await repo.obtener_por_id(guardado.id)

    r = leido.recomendaciones[0]
    assert (r.estado, r.fecha_limite, r.nivel_objetivo) == ("pendiente", None, None)
    assert leido.nivel_alcanzado is None and leido.avances_de_nivel == []


@pytest.mark.asyncio
async def test_las_recomendaciones_anteriores_al_plan_reciben_un_id_estable_y_se_pueden_editar(db):
    """Los diagnósticos ya evaluados guardaron sus recomendaciones sin id ni estado."""
    creada = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    resultado = await db["diagnosticos"].insert_one({
        "empresa_id": "emp-1", "empresa_nombre": "InnovaTech", "usuario_id": "u-1",
        "modelo_version": "2026.1", "consecutivo": 1, "estado": "evaluado", "porcentaje_avance": 100,
        "respuestas": [], "resultado": None,
        "recomendaciones": [
            {"origen": "agente", "titulo": "Antigua A", "contenido": "c", "visible": True, "creado_en": creada},
            {"origen": "consultor", "titulo": "Antigua B", "contenido": "c", "visible": True, "creado_en": creada},
        ],
        "iniciado_en": creada,
    })
    repo = RepositorioMongoDiagnostico(db)

    primera = await repo.obtener_por_id(str(resultado.inserted_id))
    segunda = await repo.obtener_por_id(str(resultado.inserted_id))

    ids = [r.id for r in primera.recomendaciones]
    assert len(set(ids)) == 2 and all(i.startswith("ant-") for i in ids)
    assert ids == [r.id for r in segunda.recomendaciones]  # estable entre lecturas
    assert all(r.estado == "pendiente" for r in primera.recomendaciones)

    # tras guardar, el id derivado queda persistido y sigue siendo el mismo
    await repo.actualizar(primera)
    en_base = await db["diagnosticos"].find_one({"_id": ObjectId(primera.id)})
    assert [r["id"] for r in en_base["recomendaciones"]] == ids
