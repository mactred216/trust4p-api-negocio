"""RF-27 / HU-028: catálogo de permisos del sistema y asignación inicial para
los roles de sistema. Cada endpoint protegido exige el rol y el permiso que le
corresponde (ver requiere_rol); retirar un permiso a un rol lo deniega de
inmediato para sus usuarios (R-16, R-17)."""

PERMISOS_SISTEMA: list[tuple[str, str, str]] = [
    # (código, módulo, descripción)
    (
        "diagnosticos.responder",
        "diagnosticos",
        "Iniciar, responder y completar el diagnóstico de su empresa",
    ),
    (
        "resultados.consultar",
        "diagnosticos",
        "Consultar resultados, informe y evolución de su empresa",
    ),
    ("diagnosticos.consultar", "diagnosticos", "Consultar diagnósticos"),
    (
        "recomendaciones.registrar",
        "consultoria",
        "Registrar recomendaciones sobre los diagnósticos de empresas asignadas",
    ),
    ("diagnosticos.cerrar", "consultoria", "Cerrar diagnósticos de empresas asignadas"),
    (
        "indicadores.consultar",
        "consultoria",
        "Consultar el tablero de indicadores agregados",
    ),
    (
        "informes.descargar",
        "consultoria",
        "Consultar y descargar el informe de las empresas dentro de su alcance",
    ),
    ("empresas.gestionar", "empresas", "Gestionar empresas"),
    (
        "usuarios.gestionar",
        "administracion",
        "Gestionar usuarios y asignaciones de consultores",
    ),
    ("roles.gestionar", "administracion", "Gestionar roles y permisos"),
    (
        "solicitudes.gestionar",
        "administracion",
        "Aprobar o rechazar solicitudes de acceso",
    ),
    ("auditoria.consultar", "administracion", "Consultar la bitácora de auditoría"),
    ("datos.exportar", "administracion", "Exportar datos agregados"),
    (
        "modelo.gestionar",
        "modelo",
        "Gestionar el modelo de madurez (dimensiones, preguntas, rúbrica, versiones)",
    ),
    ("modelo.simular", "modelo", "Simular cambios de pesos del modelo"),
]

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
