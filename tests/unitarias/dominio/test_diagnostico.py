from decimal import Decimal

import pytest

from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               Recomendacion, Respuesta,
                                               ResultadoDiagnostico)


def crear_resultado_calculado_prueba() -> ResultadoDiagnostico:
    """El resultado tal como queda justo después de
    registrar_resultado_calculado(): solo la parte determinística, sin
    contenido narrativo todavía (ASR-02)."""
    return ResultadoDiagnostico(
        indice_global=Decimal("7.2"),
        nivel=2,
        nivel_descripcion="...",
        dimensiones=[DimensionResultado(codigo="innovacion", puntaje=Decimal("8"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )


def crear_diagnostico_prueba(estado: str = "borrador") -> Diagnostico:
    return Diagnostico(
        id="diag-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="v1",
        consecutivo=1,
        estado=estado,
    )


def crear_respuesta(codigo="p1", dimension="innovacion") -> Respuesta:
    return Respuesta(
        pregunta_codigo=codigo, dimension_codigo=dimension, opciones_codigo=["alta"]
    )


def test_registrar_respuesta_la_agrega():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta(), {"p1", "p2"})
    assert len(diagnostico.respuestas) == 1


def test_registrar_respuesta_actualiza_avance():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), {"p1", "p2", "p3", "p4"})
    assert diagnostico.porcentaje_avance == 25


def test_registrar_respuesta_reemplaza_la_anterior_para_la_misma_pregunta():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), {"p1", "p2"})
    nueva = Respuesta(
        pregunta_codigo="p1", dimension_codigo="innovacion", opciones_codigo=["baja"]
    )
    diagnostico.registrar_respuesta(nueva, {"p1", "p2"})

    assert len(diagnostico.respuestas) == 1
    assert diagnostico.respuestas[0].opciones_codigo == ["baja"]


def test_registrar_respuesta_en_diagnostico_cerrado_falla():
    diagnostico = crear_diagnostico_prueba(estado="cerrado")
    with pytest.raises(ValueError):
        diagnostico.registrar_respuesta(crear_respuesta(), {"p1"})


def test_registrar_respuesta_en_diagnostico_completado_falla():
    """RF-07 paso 5: una vez completado, las respuestas quedan fijas para que
    el índice que se calcule sobre ellas sea reproducible (ASR-01)."""
    diagnostico = crear_diagnostico_prueba(estado="completado")
    with pytest.raises(ValueError):
        diagnostico.registrar_respuesta(crear_respuesta(), {"p1"})


def test_avance_no_supera_cien_por_ciento():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), {"p1"})
    assert diagnostico.porcentaje_avance == 100


def test_avance_con_cero_obligatorias_aplicables_es_cero():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), set())
    assert diagnostico.porcentaje_avance == 0


def test_avance_solo_cuenta_respuestas_de_preguntas_obligatorias_aplicables():
    """RF-10: responder una pregunta opcional (no incluida en el set de
    obligatorias aplicables) no debe mover el avance."""
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("opcional"), {"p1", "p2"})
    assert diagnostico.porcentaje_avance == 0


def test_respuesta_de_devuelve_la_respuesta_existente():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), {"p1", "p2"})
    assert diagnostico.respuesta_de("p1") is not None
    assert diagnostico.respuesta_de("no-existe") is None


def test_esta_cerrado():
    assert crear_diagnostico_prueba(estado="cerrado").esta_cerrado() is True
    assert crear_diagnostico_prueba(estado="borrador").esta_cerrado() is False


def test_marcar_completado_con_avance_completo():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), {"p1"})
    diagnostico.marcar_completado()
    assert diagnostico.estado == "completado"
    assert diagnostico.completado_en is not None


def test_marcar_completado_con_avance_incompleto_falla():
    diagnostico = crear_diagnostico_prueba()
    diagnostico.registrar_respuesta(crear_respuesta("p1"), {"p1", "p2"})
    with pytest.raises(ValueError):
        diagnostico.marcar_completado()


def test_marcar_completado_en_diagnostico_cerrado_falla():
    diagnostico = crear_diagnostico_prueba(estado="cerrado")
    with pytest.raises(ValueError):
        diagnostico.marcar_completado()


def test_marcar_completado_ya_completado_falla():
    diagnostico = crear_diagnostico_prueba(estado="completado")
    diagnostico.porcentaje_avance = 100
    with pytest.raises(ValueError):
        diagnostico.marcar_completado()


def test_registrar_resultado_calculado_desde_completado():
    diagnostico = crear_diagnostico_prueba(estado="completado")
    resultado = crear_resultado_calculado_prueba()

    diagnostico.registrar_resultado_calculado(resultado)

    assert diagnostico.resultado is resultado
    assert diagnostico.estado == "completado"


def test_registrar_resultado_calculado_sin_estar_completado_falla():
    diagnostico = crear_diagnostico_prueba(estado="borrador")
    with pytest.raises(ValueError):
        diagnostico.registrar_resultado_calculado(crear_resultado_calculado_prueba())


def test_marcar_evaluado_desde_completado_con_resultado_calculado():
    diagnostico = crear_diagnostico_prueba(estado="completado")
    diagnostico.registrar_resultado_calculado(crear_resultado_calculado_prueba())
    recomendaciones = [
        Recomendacion(
            origen="agente",
            dimension_codigo="innovacion",
            titulo="T",
            contenido="C",
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

    assert diagnostico.estado == "evaluado"
    assert diagnostico.recomendaciones == recomendaciones
    assert diagnostico.evaluado_en is not None
    # ASR-02: el resultado determinístico ya existía; marcar_evaluado solo
    # completa la parte narrativa sobre el mismo objeto.
    assert diagnostico.resultado.indice_global == Decimal("7.2")
    assert diagnostico.resultado.perfil_cultura.codigo == "ENFP"
    assert diagnostico.resultado.perfil_cultura.descripcion == "Descripción del perfil"
    assert diagnostico.resultado.dimensiones[0].observacion == "Observación"
    assert diagnostico.resultado.sintesis == "Síntesis"


def test_marcar_evaluado_sin_resultado_calculado_falla():
    diagnostico = crear_diagnostico_prueba(estado="completado")
    with pytest.raises(ValueError):
        diagnostico.marcar_evaluado(
            perfil_cultura_descripcion="...",
            dimensiones_observaciones={},
            lienzo_negocio={},
            sintesis="...",
            recomendaciones=[],
        )


def test_marcar_evaluado_sin_estar_completado_falla():
    diagnostico = crear_diagnostico_prueba(estado="borrador")
    with pytest.raises(ValueError):
        diagnostico.marcar_evaluado(
            perfil_cultura_descripcion="...",
            dimensiones_observaciones={},
            lienzo_negocio={},
            sintesis="...",
            recomendaciones=[],
        )


def test_marcar_fallido_desde_completado():
    diagnostico = crear_diagnostico_prueba(estado="completado")
    diagnostico.marcar_fallido("El servicio del agente no respondió")
    assert diagnostico.estado == "fallido"
    assert diagnostico.motivo_fallo == "El servicio del agente no respondió"


def test_marcar_fallido_conserva_el_resultado_calculado():
    """ASR-02: un diagnóstico fallido conserva el índice ya calculado antes
    de invocar al agente — solo falta la interpretación narrativa."""
    diagnostico = crear_diagnostico_prueba(estado="completado")
    diagnostico.registrar_resultado_calculado(crear_resultado_calculado_prueba())

    diagnostico.marcar_fallido("El servicio del agente no respondió")

    assert diagnostico.estado == "fallido"
    assert diagnostico.resultado is not None
    assert diagnostico.resultado.indice_global == Decimal("7.2")
    assert diagnostico.resultado.sintesis is None


def test_marcar_fallido_sin_estar_completado_falla():
    diagnostico = crear_diagnostico_prueba(estado="borrador")
    with pytest.raises(ValueError):
        diagnostico.marcar_fallido("motivo cualquiera")


def test_marcar_cerrado_desde_evaluado():
    diagnostico = crear_diagnostico_prueba(estado="evaluado")
    diagnostico.marcar_cerrado()
    assert diagnostico.estado == "cerrado"
    assert diagnostico.cerrado_en is not None


def test_marcar_cerrado_desde_fallido():
    diagnostico = crear_diagnostico_prueba(estado="fallido")
    diagnostico.marcar_cerrado()
    assert diagnostico.estado == "cerrado"


def test_marcar_cerrado_desde_completado_falla():
    diagnostico = crear_diagnostico_prueba(estado="completado")
    with pytest.raises(ValueError):
        diagnostico.marcar_cerrado()


def test_marcar_cerrado_desde_borrador_falla():
    diagnostico = crear_diagnostico_prueba(estado="borrador")
    with pytest.raises(ValueError):
        diagnostico.marcar_cerrado()
