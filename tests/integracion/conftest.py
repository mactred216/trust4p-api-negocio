import os

import pytest_asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

NOMBRE_BASE_DATOS_PRUEBA = "trust4p_test"


@pytest_asyncio.fixture
async def db():
    """Base de datos MongoDB real y separada de la de desarrollo, para
    verificar que los adaptadores de persistencia funcionan contra el motor
    real (no solo contra mocks). Requiere MONGO_URI en .env. Cada prueba
    limpia las colecciones que usó al terminar."""
    cliente = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    base_datos = cliente[NOMBRE_BASE_DATOS_PRUEBA]
    yield base_datos
    for nombre_coleccion in await base_datos.list_collection_names():
        await base_datos[nombre_coleccion].drop()
    cliente.close()
