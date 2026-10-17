"""RF-27 / HU-028: catálogo de permisos del sistema y asignación inicial para
los roles de sistema. Cada endpoint protegido exige el rol y el permiso que le
corresponde (ver requiere_rol); retirar un permiso a un rol lo deniega de
inmediato para sus usuarios (R-16, R-17)."""

PERMISOS_SISTEMA: list[tuple[str, str, str, str]] = [
    # (código, módulo, nombre para mostrar, descripción)
    (
        "diagnosticos.responder",
        "diagnosticos",
        "Responder el diagnóstico",
        "Iniciar, responder y completar el diagnóstico de su empresa",
    ),
    (
        "resultados.consultar",
        "diagnosticos",
        "Ver resultados e informe de la empresa",
        "Consultar resultados, informe y evolución de su empresa",
    ),
    (
        "diagnosticos.consultar",
        "diagnosticos",
        "Ver diagnósticos",
        "Consultar diagnósticos",
    ),
    (
        "recomendaciones.registrar",
        "consultoria",
        "Registrar recomendaciones",
        "Registrar recomendaciones sobre los diagnósticos de empresas asignadas",
    ),
    (
        "diagnosticos.cerrar",
        "consultoria",
        "Cerrar diagnósticos",
        "Cerrar diagnósticos de empresas asignadas (el administrador, de cualquier empresa)",
    ),
    (
        "indicadores.consultar",
        "consultoria",
        "Ver el tablero de indicadores",
        "Consultar el tablero de indicadores agregados",
    ),
    (
        "informes.descargar",
        "consultoria",
        "Descargar informes por empresa",
        "Consultar y descargar el informe de las empresas dentro de su alcance",
    ),
    (
        "empresas.gestionar",
        "empresas",
        "Gestionar empresas",
        "Crear, editar, desactivar y reactivar empresas",
    ),
    (
        "usuarios.gestionar",
        "administracion",
        "Gestionar usuarios",
        "Gestionar usuarios y asignaciones de consultores",
    ),
    (
        "roles.gestionar",
        "administracion",
        "Gestionar roles y permisos",
        "Conceder o retirar permisos a cada rol",
    ),
    (
        "solicitudes.gestionar",
        "administracion",
        "Gestionar solicitudes de acceso",
        "Aprobar o rechazar solicitudes de acceso",
    ),
    (
        "auditoria.consultar",
        "administracion",
        "Consultar la auditoría",
        "Consultar la bitácora de auditoría",
    ),
    (
        "datos.exportar",
        "administracion",
        "Exportar datos",
        "Exportar los indicadores agregados y anonimizados en CSV",
    ),
    (
        "modelo.gestionar",
        "modelo",
        "Gestionar el modelo de madurez",
        "Gestionar el modelo de madurez (dimensiones, preguntas, rúbrica, versiones)",
    ),
    (
        "modelo.simular",
        "modelo",
        "Simular cambios de pesos",
        "Simular cambios de pesos del modelo",
    ),
]

# Nombre con que se muestra cada módulo de permisos (el código es interno).
NOMBRES_MODULOS_PERMISOS: dict[str, str] = {
    "diagnosticos": "Diagnósticos",
    "consultoria": "Consultoría",
    "empresas": "Empresas",
    "administracion": "Administración",
    "modelo": "Modelo de madurez",
}


def nombre_modulo_permiso(modulo: str) -> str:
    """Nombre legible del módulo; para uno que no esté en el catálogo, el
    código con la primera letra en mayúscula."""
    return NOMBRES_MODULOS_PERMISOS.get(modulo, modulo.capitalize())


PERMISOS_POR_ROL: dict[str, list[str]] = {
    "representante": ["diagnosticos.responder", "resultados.consultar"],
    "consultor": [
        "diagnosticos.consultar",
        "recomendaciones.registrar",
        "diagnosticos.cerrar",
        "indicadores.consultar",
        "informes.descargar",
    ],
    "administrador": [
        "empresas.gestionar",
        "usuarios.gestionar",
        "roles.gestionar",
        "solicitudes.gestionar",
        "auditoria.consultar",
        "datos.exportar",
        "indicadores.consultar",
        "informes.descargar",
        "diagnosticos.cerrar",
        "modelo.gestionar",
        "modelo.simular",
    ],
}

# El producto se enfoca en el sector servicios: el catalogo son sus
# desagregaciones. El administrador puede ampliarlo.
SECTORES_INICIALES: list[tuple[str, str]] = [
    # (codigo, nombre)
    ("servicios", "Servicios profesionales"),
    ("tecnologia", "Tecnología y Software"),
    ("fintech", "Fintech y Servicios financieros"),
    ("logistica", "Cadena de suministro / Logística"),
    ("salud", "Salud y bienestar"),
    ("educacion", "Educación y formación"),
    ("turismo", "Turismo, hotelería y restaurantes"),
    ("comercio", "Comercio y retail"),
    ("telecom_medios", "Telecomunicaciones y medios"),
    ("marketing", "Marketing, publicidad y comunicaciones"),
    ("otros_servicios", "Otros servicios"),
]

# Sectores del catalogo anterior que no son servicios: se desactivan una sola
# vez (las empresas que ya los tienen conservan su dato).
SECTORES_RETIRADOS: list[str] = ["biotecnologia", "alimentos", "manufactura", "otro"]

NOMBRES_ROLES = {
    "representante": "Representante de empresa",
    "consultor": "Consultor",
    "administrador": "Administrador",
}
