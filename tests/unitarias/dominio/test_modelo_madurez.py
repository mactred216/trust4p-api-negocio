from decimal import Decimal

import pytest

from src.dominio.entidades.modelo_madurez import (EJES_PERFIL_CULTURAL_CODIGOS,
                                                  CondicionActivacion,
                                                  Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  OpcionPregunta, Pregunta)


def crear_eje_perfil_cultural(
    codigo, dimension_codigo="innovacion"
) -> EjePerfilCultural:
    return EjePerfilCultural(
        codigo=codigo,
        nombre=codigo,
        polo_alto_codigo="A",
        polo_alto_nombre=f"{codigo} alto",
        polo_bajo_codigo="B",
        polo_bajo_nombre=f"{codigo} bajo",
        dimension_codigo=dimension_codigo,
        umbral=Decimal("5"),
    )


def agregar_ejes_perfil_cultural_completos(
    modelo: ModeloMadurez, dimension_codigo="innovacion"
) -> None:
    for codigo in EJES_PERFIL_CULTURAL_CODIGOS:
        modelo.agregar_eje_perfil_cultural(
            crear_eje_perfil_cultural(codigo, dimension_codigo)
        )


def crear_modelo_prueba(publicado: bool = False) -> ModeloMadurez:
    return ModeloMadurez(
        id="modelo-1", version="v1", nombre="Modelo inicial", publicado=publicado
    )


def crear_dimension(codigo="innovacion", peso="0.5", orden=1) -> Dimension:
    return Dimension(
        codigo=codigo, nombre="Innovación", peso=Decimal(peso), orden=orden
    )


def crear_pregunta(
    codigo="p1", dimension_codigo="innovacion", peso="1", orden=1
) -> Pregunta:
    return Pregunta(
        codigo=codigo,
        dimension_codigo=dimension_codigo,
        enunciado="¿Su empresa invierte en I+D?",
        tipo="escala",
        obligatoria=True,
        peso=Decimal(peso),
        en_demo=False,
        orden=orden,
    )


def test_agregar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    assert len(modelo.dimensiones) == 1


def test_agregar_dimension_con_codigo_duplicado_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    with pytest.raises(ValueError):
        modelo.agregar_dimension(crear_dimension())


def test_editar_dimension_actualiza_solo_campos_enviados():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    modelo.editar_dimension("innovacion", peso=Decimal("0.7"))
    assert modelo.dimensiones[0].peso == Decimal("0.7")
    assert modelo.dimensiones[0].nombre == "Innovación"


def test_editar_dimension_inexistente_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.editar_dimension("no-existe", peso=Decimal("0.5"))


def test_quitar_dimension():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    modelo.quitar_dimension("innovacion")
    assert modelo.dimensiones == []


def test_no_se_puede_quitar_una_dimension_con_preguntas_activas():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    modelo.agregar_pregunta(crear_pregunta())

    with pytest.raises(ValueError, match="preguntas activas"):
        modelo.quitar_dimension("innovacion")

    assert [d.codigo for d in modelo.dimensiones] == ["innovacion"]


def test_se_puede_quitar_una_dimension_cuando_sus_preguntas_estan_desactivadas():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension())
    modelo.agregar_pregunta(crear_pregunta())
    modelo.desactivar_pregunta("p1")

    modelo.quitar_dimension("innovacion")

    assert modelo.dimensiones == []


def test_no_se_puede_modificar_una_version_publicada():
    modelo = crear_modelo_prueba(publicado=True)
    with pytest.raises(ValueError):
        modelo.agregar_dimension(crear_dimension())


# R-02: la suma de los pesos de las dimensiones debe totalizar 1 (RF-30, HU-031 CA-01)
def test_validar_pesos_dimensiones_correctos_no_lanza():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "0.5", 1))
    modelo.agregar_dimension(crear_dimension("cultura", "0.5", 2))
    modelo.validar_pesos_dimensiones()  # no debe lanzar


def test_validar_pesos_dimensiones_que_no_suman_uno_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "0.5", 1))
    modelo.agregar_dimension(crear_dimension("cultura", "0.3", 2))
    with pytest.raises(ValueError):
        modelo.validar_pesos_dimensiones()


def test_validar_pesos_sin_dimensiones_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.validar_pesos_dimensiones()


# HU-032: asociar preguntas a dimensiones
def crear_modelo_con_dimension() -> ModeloMadurez:
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    return modelo


def test_agregar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    assert len(modelo.preguntas) == 1


def test_agregar_pregunta_a_dimension_inexistente_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(crear_pregunta(dimension_codigo="no-existe"))


def test_agregar_pregunta_con_codigo_duplicado_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1"))
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(crear_pregunta("p1"))


def test_agregar_pregunta_con_condicion_a_pregunta_inexistente_falla():
    modelo = crear_modelo_con_dimension()
    pregunta = crear_pregunta("p2")
    pregunta.condicion = CondicionActivacion(
        pregunta_codigo="no-existe", operador="igual", valor="si"
    )
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(pregunta)


def test_agregar_pregunta_con_condicion_a_pregunta_existente():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1"))
    pregunta_condicionada = crear_pregunta("p2")
    pregunta_condicionada.condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="igual", valor="si"
    )
    modelo.agregar_pregunta(pregunta_condicionada)
    assert len(modelo.preguntas) == 2


def test_editar_pregunta_actualiza_solo_campos_enviados():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    modelo.editar_pregunta("p1", peso=Decimal("0.5"))
    assert modelo.preguntas[0].peso == Decimal("0.5")
    assert modelo.preguntas[0].enunciado == "¿Su empresa invierte en I+D?"


def test_editar_pregunta_inexistente_falla():
    modelo = crear_modelo_con_dimension()
    with pytest.raises(ValueError):
        modelo.editar_pregunta("no-existe", peso=Decimal("0.5"))


def test_editar_pregunta_reemplaza_opciones():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    nuevas_opciones = [OpcionPregunta(codigo="si", etiqueta="Sí", valor=Decimal("1"))]
    modelo.editar_pregunta("p1", opciones=nuevas_opciones)
    assert modelo.preguntas[0].opciones == nuevas_opciones


# RF-28 paso 3: pregunta obligatoria de tipo cerrado exige al menos una opción
def test_agregar_pregunta_obligatoria_cerrada_sin_opciones_falla():
    modelo = crear_modelo_con_dimension()
    pregunta = crear_pregunta()
    pregunta.tipo = "seleccion_unica"
    pregunta.obligatoria = True
    pregunta.opciones = []
    with pytest.raises(ValueError):
        modelo.agregar_pregunta(pregunta)


def test_agregar_pregunta_obligatoria_cerrada_con_opciones_no_lanza():
    modelo = crear_modelo_con_dimension()
    pregunta = crear_pregunta()
    pregunta.tipo = "seleccion_unica"
    pregunta.obligatoria = True
    pregunta.opciones = [OpcionPregunta(codigo="si", etiqueta="Sí", valor=Decimal("1"))]
    modelo.agregar_pregunta(pregunta)  # no debe lanzar


def test_agregar_pregunta_no_obligatoria_cerrada_sin_opciones_no_lanza():
    modelo = crear_modelo_con_dimension()
    pregunta = crear_pregunta()
    pregunta.tipo = "seleccion_unica"
    pregunta.obligatoria = False
    pregunta.opciones = []
    modelo.agregar_pregunta(pregunta)  # no debe lanzar


def test_editar_pregunta_a_obligatoria_cerrada_sin_opciones_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())  # tipo escala, sin opciones
    with pytest.raises(ValueError):
        modelo.editar_pregunta("p1", tipo="seleccion_unica", obligatoria=True)


# RF-28: desactivar/reactivar (baja lógica, no eliminación física)
def test_desactivar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    modelo.desactivar_pregunta("p1")
    assert modelo.preguntas[0].activo is False
    assert len(modelo.preguntas) == 1  # sigue en el histórico


def test_desactivar_pregunta_ya_inactiva_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    modelo.desactivar_pregunta("p1")
    with pytest.raises(ValueError):
        modelo.desactivar_pregunta("p1")


def test_desactivar_pregunta_referenciada_por_condicion_activa_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1"))
    pregunta_condicionada = crear_pregunta("p2")
    pregunta_condicionada.condicion = CondicionActivacion(
        pregunta_codigo="p1", operador="igual", valor="si"
    )
    modelo.agregar_pregunta(pregunta_condicionada)
    with pytest.raises(ValueError):
        modelo.desactivar_pregunta("p1")


def test_reactivar_pregunta():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    modelo.desactivar_pregunta("p1")
    modelo.reactivar_pregunta("p1")
    assert modelo.preguntas[0].activo is True


def test_reactivar_pregunta_ya_activa_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta())
    with pytest.raises(ValueError):
        modelo.reactivar_pregunta("p1")


# R-03: la suma de los pesos de las preguntas de cada dimensión debe totalizar 1 (RF-31)
def test_validar_pesos_preguntas_correctos_no_lanza():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1", peso="0.6"))
    modelo.agregar_pregunta(crear_pregunta("p2", peso="0.4"))
    modelo.validar_pesos_preguntas()  # no debe lanzar


def test_validar_pesos_preguntas_que_no_suman_uno_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1", peso="0.5"))
    with pytest.raises(ValueError):
        modelo.validar_pesos_preguntas()


def test_validar_pesos_dimension_sin_preguntas_falla():
    modelo = crear_modelo_con_dimension()
    with pytest.raises(ValueError):
        modelo.validar_pesos_preguntas()


def test_validar_pesos_preguntas_ignora_preguntas_inactivas():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1", peso="1"))
    modelo.agregar_pregunta(crear_pregunta("p2", peso="0.5"))
    modelo.desactivar_pregunta("p2")
    modelo.validar_pesos_preguntas()  # p2 inactiva no cuenta; p1 sola ya suma 1


def test_validar_pesos_preguntas_dimension_solo_con_preguntas_inactivas_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_pregunta(crear_pregunta("p1", peso="1"))
    modelo.desactivar_pregunta("p1")
    with pytest.raises(ValueError):
        modelo.validar_pesos_preguntas()


# HU-033: definir rúbrica de la escala
def crear_nivel(numero=1, umbral_min="1", umbral_max="5") -> Nivel:
    return Nivel(
        nivel=numero,
        nombre=f"Nivel {numero}",
        descripcion="Descripción del nivel",
        umbral_min=Decimal(umbral_min),
        umbral_max=Decimal(umbral_max),
    )


def test_agregar_nivel():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel())
    assert len(modelo.niveles) == 1


def test_agregar_nivel_fuera_de_la_escala_falla():
    modelo = crear_modelo_prueba()  # escala_min=1, escala_max=10
    with pytest.raises(ValueError):
        modelo.agregar_nivel(crear_nivel(numero=99))


def test_agregar_nivel_con_umbrales_invertidos_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.agregar_nivel(crear_nivel(umbral_min="5", umbral_max="1"))


def test_agregar_nivel_duplicado_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel(1))
    with pytest.raises(ValueError):
        modelo.agregar_nivel(crear_nivel(1, umbral_min="5", umbral_max="8"))


def test_editar_nivel_actualiza_solo_campos_enviados():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel())
    modelo.editar_nivel(1, umbral_max=Decimal("6"))
    assert modelo.niveles[0].umbral_max == Decimal("6")
    assert modelo.niveles[0].umbral_min == Decimal("1")


def test_editar_nivel_inexistente_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.editar_nivel(1, umbral_max=Decimal("6"))


def test_quitar_nivel():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel())
    modelo.quitar_nivel(1)
    assert modelo.niveles == []


# R-04: los umbrales deben cubrir la escala completa sin solapamiento (RF-32, HU-033 CA-01)
def test_validar_niveles_que_cubren_la_escala_no_lanza():
    modelo = crear_modelo_prueba()  # escala 1-10
    modelo.agregar_nivel(crear_nivel(1, "1", "5"))
    modelo.agregar_nivel(crear_nivel(2, "5", "10"))
    modelo.validar_niveles()  # no debe lanzar


def test_validar_niveles_con_solapamiento_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel(1, "1", "6"))
    modelo.agregar_nivel(crear_nivel(2, "5", "10"))
    with pytest.raises(ValueError):
        modelo.validar_niveles()


def test_validar_niveles_con_vacio_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel(1, "1", "4"))
    modelo.agregar_nivel(crear_nivel(2, "5", "10"))
    with pytest.raises(ValueError):
        modelo.validar_niveles()


def test_validar_niveles_que_no_empiezan_en_escala_min_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_nivel(crear_nivel(1, "2", "10"))
    with pytest.raises(ValueError):
        modelo.validar_niveles()


def test_validar_niveles_sin_niveles_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.validar_niveles()


# HU-034: versionar modelo (publicar)
def crear_modelo_publicable() -> ModeloMadurez:
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    modelo.agregar_pregunta(crear_pregunta("p1", "innovacion", "1", 1))
    modelo.agregar_nivel(crear_nivel(1, "1", "10"))
    agregar_ejes_perfil_cultural_completos(modelo)
    return modelo


def test_publicar_modelo_completo_no_lanza():
    modelo = crear_modelo_publicable()
    modelo.publicar("admin-1")
    assert modelo.publicado is True
    assert modelo.publicado_por == "admin-1"
    assert modelo.publicado_en is not None


def test_publicar_sin_dimensiones_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.publicar("admin-1")


def test_publicar_sin_ejes_perfil_cultural_completos_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    modelo.agregar_pregunta(crear_pregunta("p1", "innovacion", "1", 1))
    modelo.agregar_nivel(crear_nivel(1, "1", "10"))
    modelo.agregar_eje_perfil_cultural(crear_eje_perfil_cultural("extroversion"))
    with pytest.raises(ValueError):
        modelo.publicar("admin-1")


def test_no_se_puede_quitar_una_dimension_que_usa_un_eje_del_perfil_de_cultura():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    agregar_ejes_perfil_cultural_completos(modelo)

    with pytest.raises(ValueError, match="perfil de cultura"):
        modelo.quitar_dimension("innovacion")

    assert [d.codigo for d in modelo.dimensiones] == ["innovacion"]


def test_publicar_falla_si_un_eje_usa_una_dimension_que_ya_no_existe():
    modelo = crear_modelo_publicable()
    # Un eje queda apuntando a una dimensión que no está en la versión (p. ej. el
    # borrador se clonó y la dimensión se retiró por otra vía).
    modelo.ejes_perfil_cultural[0].dimension_codigo = "fantasma"

    with pytest.raises(ValueError, match="no existe en esta versión"):
        modelo.publicar("admin-1")


def test_agregar_eje_perfil_cultural_codigo_invalido_falla():
    modelo = crear_modelo_con_dimension()
    with pytest.raises(ValueError):
        modelo.agregar_eje_perfil_cultural(
            crear_eje_perfil_cultural("no-es-un-eje-valido")
        )


def test_agregar_eje_perfil_cultural_dimension_inexistente_falla():
    modelo = crear_modelo_prueba()
    with pytest.raises(ValueError):
        modelo.agregar_eje_perfil_cultural(
            crear_eje_perfil_cultural("extroversion", dimension_codigo="no-existe")
        )


def test_agregar_eje_perfil_cultural_duplicado_falla():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_eje_perfil_cultural(crear_eje_perfil_cultural("extroversion"))
    with pytest.raises(ValueError):
        modelo.agregar_eje_perfil_cultural(crear_eje_perfil_cultural("extroversion"))


def test_editar_eje_perfil_cultural():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_eje_perfil_cultural(crear_eje_perfil_cultural("extroversion"))
    modelo.editar_eje_perfil_cultural("extroversion", umbral=Decimal("7"))
    assert modelo._buscar_eje_perfil_cultural("extroversion").umbral == Decimal("7")


def test_quitar_eje_perfil_cultural():
    modelo = crear_modelo_con_dimension()
    modelo.agregar_eje_perfil_cultural(crear_eje_perfil_cultural("extroversion"))
    modelo.quitar_eje_perfil_cultural("extroversion")
    assert modelo.ejes_perfil_cultural == []


def test_publicar_con_pesos_de_dimensiones_incorrectos_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "0.5", 1))
    modelo.agregar_pregunta(crear_pregunta("p1", "innovacion", "1", 1))
    modelo.agregar_nivel(crear_nivel(1, "1", "10"))
    with pytest.raises(ValueError):
        modelo.publicar("admin-1")


def test_publicar_sin_preguntas_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    modelo.agregar_nivel(crear_nivel(1, "1", "10"))
    with pytest.raises(ValueError):
        modelo.publicar("admin-1")


def test_publicar_sin_niveles_falla():
    modelo = crear_modelo_prueba()
    modelo.agregar_dimension(crear_dimension("innovacion", "1", 1))
    modelo.agregar_pregunta(crear_pregunta("p1", "innovacion", "1", 1))
    with pytest.raises(ValueError):
        modelo.publicar("admin-1")


def test_publicar_una_version_ya_publicada_falla():
    modelo = crear_modelo_publicable()
    modelo.publicar("admin-1")
    with pytest.raises(ValueError):
        modelo.publicar("admin-1")


def test_no_se_puede_editar_tras_publicar():
    modelo = crear_modelo_publicable()
    modelo.publicar("admin-1")
    with pytest.raises(ValueError):
        modelo.agregar_dimension(crear_dimension("cultura", "1", 2))
