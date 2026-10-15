"""Rúbrica estándar de madurez de innovación: 10 niveles de igual amplitud sobre
la escala del modelo. El administrador puede partir de ella en un borrador y
ajustar nombres, descripciones y rangos; el cálculo del nivel de una empresa
siempre usa la rúbrica de la versión con que se evaluó."""

from decimal import Decimal

from src.dominio.entidades.modelo_madurez import Nivel

# (nombre, descripción) de cada nivel, del 1 (más bajo) al 10 (más alto).
NIVELES_ESTANDAR: list[tuple[str, str]] = [
    (
        "Inexistente",
        "No hay prácticas de innovación; si surge alguna iniciativa, es accidental.",
    ),
    (
        "Incipiente",
        "Aparecen esfuerzos aislados, sin responsables ni método.",
    ),
    (
        "Reactivo",
        "Se innova solo ante presiones externas o problemas puntuales.",
    ),
    (
        "Emergente",
        "Hay prácticas definidas en algunas áreas, pero sin continuidad.",
    ),
    (
        "Estructurado",
        "Existen procesos y responsables definidos; la práctica es periódica pero desigual.",
    ),
    (
        "Gestionado",
        "La innovación se planifica, cuenta con recursos y tiene seguimiento regular.",
    ),
    (
        "Integrado",
        "La innovación está conectada con la estrategia y se extiende a toda la organización.",
    ),
    (
        "Medido",
        "Se miden los resultados y el impacto, y las decisiones se apoyan en esos datos.",
    ),
    (
        "Optimizado",
        "La práctica se ajusta de forma continua con base en resultados y aprendizajes.",
    ),
    (
        "Referente",
        "La organización lidera en innovación y su práctica es referente en el sector.",
    ),
]


def rubrica_estandar(escala_min, escala_max) -> list[Nivel]:
    """Los 10 niveles estándar repartidos en bandas iguales de la escala (con
    escala 0 a 100: 0-10, 10-20, ..., 90-100). Un valor justo en el límite entre
    dos niveles pertenece al inferior (así lo resuelve el motor de cálculo)."""
    minimo, maximo = Decimal(escala_min), Decimal(escala_max)
    ancho = (maximo - minimo) / Decimal(len(NIVELES_ESTANDAR))
    niveles = []
    for i, (nombre, descripcion) in enumerate(NIVELES_ESTANDAR):
        es_ultimo = i == len(NIVELES_ESTANDAR) - 1
        niveles.append(
            Nivel(
                nivel=i + 1,
                nombre=nombre,
                descripcion=descripcion,
                umbral_min=minimo + ancho * i,
                umbral_max=maximo if es_ultimo else minimo + ancho * (i + 1),
            )
        )
    return niveles
