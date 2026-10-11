from datetime import date
from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               Recomendacion,
                                               ResultadoDiagnostico)

# Las recomendaciones son las tareas del plan de mejora: tienen estado, fecha
# límite y el nivel que ayudan a alcanzar. El consultor las gestiona y confirma
# cuándo la empresa alcanza el siguiente nivel.

NIVEL_MAXIMO = 10


def diagnostico(nivel=3, estado="evaluado", recomendaciones=None) -> Diagnostico:
    d = Diagnostico(
        id="d-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="u-1",
        modelo_version="2026.2",
        consecutivo=1,
        estado=estado,
    )
    d.resultado = ResultadoDiagnostico(
        indice_global=Decimal(nivel * 10 - 5),
        nivel=nivel,
        nivel_descripcion="x",
        dimensiones=[DimensionResultado(codigo="proposito", puntaje=Decimal("30"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    d.recomendaciones = recomendaciones if recomendaciones is not None else []
    return d


def tarea(titulo="T", estado="pendiente", nivel_objetivo=None, visible=True) -> Recomendacion:
    return Recomendacion(
        origen="consultor", titulo=titulo, contenido="c", estado=estado,
        nivel_objetivo=nivel_objetivo, visible=visible,
    )


# ---------- nacen como tareas ----------


def test_las_recomendaciones_del_agente_apuntan_al_siguiente_nivel_al_evaluarse():
    d = diagnostico(nivel=3, estado="completado")
    d.marcar_evaluado("p", {}, {}, "s", [tarea("A"), tarea("B")], nivel_maximo=NIVEL_MAXIMO)

    assert [r.nivel_objetivo for r in d.recomendaciones] == [4, 4]
    assert all(r.estado == "pendiente" and r.fecha_limite is None for r in d.recomendaciones)


def test_si_la_empresa_ya_esta_en_el_nivel_maximo_no_hay_nivel_al_que_apuntar():
    d = diagnostico(nivel=10, estado="completado")
    d.marcar_evaluado("p", {}, {}, "s", [tarea("A")], nivel_maximo=NIVEL_MAXIMO)

    assert d.recomendaciones[0].nivel_objetivo is None


def test_cada_tarea_tiene_un_identificador_propio():
    assert len({tarea().id for _ in range(50)}) == 50


def test_una_tarea_anterior_sin_nivel_apunta_al_siguiente_del_diagnostico():
    d = diagnostico(nivel=3, recomendaciones=[tarea()])

    assert d.nivel_objetivo_de(d.recomendaciones[0]) == 4


# ---------- agregar ----------


def test_una_tarea_nueva_apunta_por_defecto_al_siguiente_nivel_de_la_empresa():
    d = diagnostico(nivel=3)

    r = d.agregar_recomendacion_consultor("c-1", "Capacitar", "Detalle", nivel_maximo=NIVEL_MAXIMO)

    assert r.nivel_objetivo == 4 and r.estado == "pendiente"


def test_tras_confirmar_un_nivel_las_tareas_nuevas_apuntan_al_siguiente():
    d = diagnostico(nivel=3)
    d.nivel_alcanzado = 4

    r = d.agregar_recomendacion_consultor("c-1", "T", "c", nivel_maximo=NIVEL_MAXIMO)

    assert r.nivel_objetivo == 5


def test_se_puede_fijar_la_fecha_y_un_nivel_mas_lejano():
    d = diagnostico(nivel=3)

    r = d.agregar_recomendacion_consultor(
        "c-1", "T", "c", fecha_limite=date(2026, 12, 1), nivel_objetivo=6, nivel_maximo=NIVEL_MAXIMO
    )

    assert (r.fecha_limite, r.nivel_objetivo) == (date(2026, 12, 1), 6)


@pytest.mark.parametrize("nivel", [3, 2, 11])
def test_el_nivel_objetivo_debe_ser_mayor_que_el_actual_y_no_superar_el_maximo(nivel):
    with pytest.raises(ValueError, match="nivel"):
        diagnostico(nivel=3).agregar_recomendacion_consultor(
            "c-1", "T", "c", nivel_objetivo=nivel, nivel_maximo=NIVEL_MAXIMO
        )


# ---------- editar ----------


def test_el_consultor_cambia_estado_y_fecha_de_una_tarea():
    r = tarea()
    d = diagnostico(recomendaciones=[r])

    d.editar_recomendacion(r, {"estado": "en_curso", "fecha_limite": date(2026, 11, 30)})

    assert (r.estado, r.fecha_limite) == ("en_curso", date(2026, 11, 30))
    assert r.completada_en is None and r.actualizado_en is not None


def test_completar_registra_cuando_y_reabrir_lo_borra():
    r = tarea()
    d = diagnostico(recomendaciones=[r])

    d.editar_recomendacion(r, {"estado": "completada"})
    assert r.completada_en is not None

    d.editar_recomendacion(r, {"estado": "pendiente"})
    assert r.completada_en is None


def test_una_fecha_limite_explicita_en_none_la_quita():
    r = tarea()
    r.fecha_limite = date(2026, 11, 30)
    d = diagnostico(recomendaciones=[r])

    d.editar_recomendacion(r, {"fecha_limite": None})

    assert r.fecha_limite is None


def test_solo_cambia_lo_que_se_envia():
    r = tarea("Original")
    r.fecha_limite = date(2026, 11, 30)
    d = diagnostico(recomendaciones=[r])

    d.editar_recomendacion(r, {"contenido": "Nuevo detalle"})

    assert (r.titulo, r.contenido, r.fecha_limite) == ("Original", "Nuevo detalle", date(2026, 11, 30))


def test_se_puede_ocultar_o_compartir_una_tarea():
    r = tarea()
    d = diagnostico(recomendaciones=[r])

    d.editar_recomendacion(r, {"visible": False})

    assert r.visible is False


def test_un_estado_invalido_se_rechaza():
    r = tarea()
    with pytest.raises(ValueError, match="Estado inválido"):
        diagnostico(recomendaciones=[r]).editar_recomendacion(r, {"estado": "terminada"})


def test_cambiar_el_nivel_objetivo_valida_el_rango():
    r = tarea(nivel_objetivo=4)
    d = diagnostico(nivel=3, recomendaciones=[r])

    d.editar_recomendacion(r, {"nivel_objetivo": 5}, nivel_maximo=NIVEL_MAXIMO)
    assert r.nivel_objetivo == 5

    with pytest.raises(ValueError):
        d.editar_recomendacion(r, {"nivel_objetivo": 3}, nivel_maximo=NIVEL_MAXIMO)
    with pytest.raises(ValueError):
        d.editar_recomendacion(r, {"nivel_objetivo": 11}, nivel_maximo=NIVEL_MAXIMO)


def test_un_diagnostico_cerrado_no_admite_cambios():
    r = tarea()
    d = diagnostico(estado="cerrado", recomendaciones=[r])

    with pytest.raises(ValueError, match="cerrado"):
        d.editar_recomendacion(r, {"estado": "completada"})


def test_solo_un_diagnostico_evaluado_tiene_plan_editable():
    r = tarea()
    with pytest.raises(ValueError, match="evaluado"):
        diagnostico(estado="fallido", recomendaciones=[r]).editar_recomendacion(r, {"estado": "completada"})


def test_una_tarea_de_un_nivel_ya_confirmado_no_se_reabre_pero_sigue_siendo_editable_en_lo_demas():
    r = tarea("Hecha", estado="completada", nivel_objetivo=4)
    d = diagnostico(nivel=3, recomendaciones=[r])
    d.nivel_alcanzado = 4

    with pytest.raises(ValueError, match="ya fue confirmado"):
        d.editar_recomendacion(r, {"estado": "pendiente"})

    d.editar_recomendacion(r, {"contenido": "Aclaración"})
    assert r.contenido == "Aclaración"


# ---------- avanzar de nivel ----------


def test_confirma_el_siguiente_nivel_cuando_todas_sus_tareas_estan_completadas():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 4), tarea("B", "completada", 4)])

    avance = d.avanzar_nivel("c-1", "Julia Herrera", NIVEL_MAXIMO)

    assert avance.nivel == 4 and avance.consultor_nombre == "Julia Herrera"
    assert d.nivel_alcanzado == 4 and d.nivel_actual() == 4
    assert [a.nivel for a in d.avances_de_nivel] == [4]


def test_no_confirma_si_falta_alguna_tarea_y_dice_cuantas():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 4), tarea("B", "en_curso", 4), tarea("C", "pendiente", 4)])

    with pytest.raises(ValueError, match="Faltan 2 de 3 tareas"):
        d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)

    assert d.nivel_alcanzado is None


def test_no_confirma_si_no_hay_tareas_para_ese_nivel():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 6)])

    with pytest.raises(ValueError, match="No hay tareas para llegar al nivel 4"):
        d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)


def test_las_tareas_no_compartidas_con_la_empresa_no_cuentan():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 4), tarea("Borrador", "pendiente", 4, visible=False)])

    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)

    assert d.nivel_alcanzado == 4


def test_solo_cuentan_las_tareas_del_nivel_que_sigue():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 4), tarea("Futura", "pendiente", 5)])

    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)

    assert d.nivel_alcanzado == 4


def test_las_tareas_antiguas_sin_nivel_cuentan_para_el_siguiente_del_diagnostico():
    d = diagnostico(nivel=3, recomendaciones=[tarea("Antigua", "completada")])

    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)

    assert d.nivel_alcanzado == 4


def test_para_el_siguiente_avance_hacen_falta_nuevas_tareas():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 4)])
    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)

    with pytest.raises(ValueError, match="nivel 5"):
        d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)

    d.recomendaciones.append(tarea("B", "completada", 5))
    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)
    assert d.nivel_alcanzado == 5


def test_no_se_avanza_mas_alla_del_nivel_maximo():
    d = diagnostico(nivel=10, recomendaciones=[tarea("A", "completada", 11)])

    with pytest.raises(ValueError, match="nivel máximo"):
        d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)


def test_un_diagnostico_cerrado_no_avanza():
    d = diagnostico(estado="cerrado", recomendaciones=[tarea("A", "completada", 4)])

    with pytest.raises(ValueError, match="cerrado"):
        d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)


# ---------- nuevo diagnóstico ----------


def test_con_dos_niveles_de_avance_se_recomienda_un_nuevo_diagnostico():
    d = diagnostico(nivel=3, recomendaciones=[tarea("A", "completada", 4), tarea("B", "completada", 5)])
    assert d.nuevo_diagnostico_recomendado() is False  # sin avances

    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)
    assert d.nuevo_diagnostico_recomendado() is False  # un nivel

    d.avanzar_nivel("c-1", "J", NIVEL_MAXIMO)
    assert d.nuevo_diagnostico_recomendado() is True  # dos niveles


def test_buscar_una_tarea_por_su_identificador():
    r = tarea()
    d = diagnostico(recomendaciones=[r, tarea("Otra")])

    assert d.recomendacion_por_id(r.id) is r
    assert d.recomendacion_por_id("no-existe") is None
