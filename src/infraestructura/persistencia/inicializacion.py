import logging
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.catalogo_permisos import (NOMBRES_ROLES, PERMISOS_POR_ROL,
                                           PERMISOS_SISTEMA,
                                           SECTORES_INICIALES,
                                           SECTORES_RETIRADOS)


async def sembrar_permisos(db: AsyncIOMotorDatabase) -> None:
    """Idempotente. Garantiza que existan los permisos del catálogo y los roles
    de sistema, y asigna los permisos por defecto UNA sola vez: el campo
    `permisos_sembrados` del rol recuerda lo ya sembrado, de modo que un
    permiso que el administrador retiró no se vuelve a conceder al reiniciar."""
    ahora = datetime.now(timezone.utc)
    for codigo, modulo, descripcion in PERMISOS_SISTEMA:
        await db["permisos"].update_one(
            {"codigo": codigo},
            {
                "$setOnInsert": {
                    "modulo": modulo,
                    "descripcion": descripcion,
                    "activo": True,
                    "creado_en": ahora,
                }
            },
            upsert=True,
        )
    for rol, permisos in PERMISOS_POR_ROL.items():
        await db["roles"].update_one(
            {"codigo": rol},
            {
                "$setOnInsert": {
                    "nombre": NOMBRES_ROLES[rol],
                    "descripcion": "",
                    "es_sistema": True,
                    "permisos": [],
                    "activo": True,
                    "creado_en": ahora,
                    "permisos_sembrados": [],
                }
            },
            upsert=True,
        )
        doc = await db["roles"].find_one({"codigo": rol})
        sembrados = set(doc.get("permisos_sembrados", []))
        vigentes = list(doc.get("permisos", []))
        nuevos = [p for p in permisos if p not in sembrados]
        if nuevos:
            for p in nuevos:
                if p not in vigentes:
                    vigentes.append(p)
            await db["roles"].update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "permisos": vigentes,
                        "permisos_sembrados": sorted(sembrados | set(nuevos)),
                    }
                },
            )
            # R-17: las sesiones abiertas conservan los permisos anteriores;
            # se revocan para que el siguiente inicio de sesión los resuelva.
            await db["sesiones"].delete_many({"rol_codigo": rol})


registro = logging.getLogger("trust4p.indices")

ASC, DESC = 1, -1

# Diccionario de Datos, hoja 3 (indices). Solo las colecciones de api-negocio;
# las de servicio-agente (documentos, fragmentos, ejecuciones) las crea ese
# servicio. El token de invitacion/restablecimiento se guarda como codigo_hash.
INDICES: list[tuple[str, list[tuple[str, int]], dict]] = [
    ("sectores", [("codigo", ASC)], {"unique": True}),
    ("permisos", [("codigo", ASC)], {"unique": True}),
    ("roles", [("codigo", ASC)], {"unique": True}),
    ("usuarios", [("correo", ASC)], {"unique": True}),
    ("usuarios", [("empresa_id", ASC)], {}),
    ("usuarios", [("asignaciones.empresa_id", ASC)], {}),
    ("sesiones", [("token_hash", ASC)], {"unique": True}),
    ("sesiones", [("expira_en", ASC)], {"expireAfterSeconds": 0}),
    ("tokens_verificacion", [("codigo_hash", ASC)], {"unique": True}),
    ("tokens_verificacion", [("expira_en", ASC)], {"expireAfterSeconds": 0}),
    # unico "disperso": solo entre empresas que si tienen NIT (el campo puede
    # guardarse como null y un indice sparse trataria null como un valor)
    (
        "empresas",
        [("nit", ASC)],
        {"unique": True, "partialFilterExpression": {"nit": {"$type": "string"}}},
    ),
    ("empresas", [("sector.id", ASC), ("activo", ASC)], {}),
    ("solicitudes_acceso", [("estado", ASC), ("creado_en", DESC)], {}),
    ("solicitudes_acceso", [("correo_solicitante", ASC)], {}),
    ("modelos_madurez", [("version", ASC)], {"unique": True}),
    ("modelos_madurez", [("publicado", ASC), ("publicado_en", DESC)], {}),
    ("diagnosticos", [("empresa_id", ASC), ("consecutivo", ASC)], {"unique": True}),
    ("diagnosticos", [("empresa_id", ASC), ("estado", ASC)], {}),
    ("diagnosticos", [("resultado.nivel", ASC), ("empresa_id", ASC)], {}),
    ("diagnosticos", [("usuario_id", ASC)], {}),
    ("notificaciones", [("enviada_en", ASC)], {"sparse": True}),
    ("auditoria", [("entidad", ASC), ("entidad_id", ASC)], {}),
    ("auditoria", [("registrado_en", DESC)], {}),
]


async def crear_indices(db: AsyncIOMotorDatabase) -> list[str]:
    """Idempotente. Crea los indices del Diccionario de Datos. Un indice que no
    se pueda crear (p. ej. un unico sobre datos que ya tienen duplicados) se
    registra y devuelve en la lista de problemas, sin detener el arranque."""
    problemas = []
    for coleccion, claves, opciones in INDICES:
        try:
            await db[coleccion].create_index(claves, **opciones)
        except Exception as e:
            descripcion = f"{coleccion}{[c for c, _ in claves]}: {e}"
            registro.warning("No se pudo crear el indice %s", descripcion)
            problemas.append(descripcion)
    return problemas


async def sembrar_sectores(db: AsyncIOMotorDatabase) -> None:
    """Idempotente: crea los sectores del catalogo inicial que falten sin tocar
    los que el administrador haya renombrado o desactivado."""
    ahora = datetime.now(timezone.utc)
    for codigo, nombre in SECTORES_INICIALES:
        await db["sectores"].update_one(
            {"codigo": codigo},
            {"$setOnInsert": {"nombre": nombre, "activo": True, "creado_en": ahora}},
            upsert=True,
        )
    # Una sola vez por sector: si el administrador lo reactiva despues, no se
    # vuelve a desactivar.
    await db["sectores"].update_many(
        {"codigo": {"$in": SECTORES_RETIRADOS}, "retirado_por_catalogo": {"$ne": True}},
        {"$set": {"activo": False, "retirado_por_catalogo": True}},
    )


async def inicializar_base_datos(db: AsyncIOMotorDatabase) -> None:
    await sembrar_permisos(db)
    await sembrar_sectores(db)
    await crear_indices(db)
