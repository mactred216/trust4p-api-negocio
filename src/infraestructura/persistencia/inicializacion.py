from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.catalogo_permisos import (NOMBRES_ROLES, PERMISOS_POR_ROL,
                                           PERMISOS_SISTEMA)


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


async def inicializar_base_datos(db: AsyncIOMotorDatabase) -> None:
    await sembrar_permisos(db)
