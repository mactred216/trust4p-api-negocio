import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_cliente: AsyncIOMotorClient | None = None


def obtener_cliente() -> AsyncIOMotorClient:
    global _cliente
    if _cliente is None:
        _cliente = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    return _cliente


def obtener_base_datos() -> AsyncIOMotorDatabase:
    return obtener_cliente()["trust4p"]
