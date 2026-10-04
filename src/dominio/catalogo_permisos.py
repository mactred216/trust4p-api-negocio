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
    ],
    "administrador": [
        "empresas.gestionar",
        "usuarios.gestionar",
        "roles.gestionar",
        "solicitudes.gestionar",
        "auditoria.consultar",
        "datos.exportar",
        "modelo.gestionar",
        "modelo.simular",
    ],
}

NOMBRES_ROLES = {
    "representante": "Representante de empresa",
    "consultor": "Consultor",
    "administrador": "Administrador",
}
