import asyncio

from dotenv import load_dotenv

load_dotenv()

from src.infraestructura.persistencia.conexion import \
    obtener_base_datos  # noqa: E402
from src.infraestructura.persistencia.sembrado_modelo_4p import (  # noqa: E402
    VERSION_MODELO_4P, sembrar_modelo_4p)


async def principal() -> None:
    creado = await sembrar_modelo_4p(obtener_base_datos())
    print(
        f"Modelo {VERSION_MODELO_4P} "
        + ("creado y publicado." if creado else "ya existia; sin cambios.")
    )


if __name__ == "__main__":
    asyncio.run(principal())
