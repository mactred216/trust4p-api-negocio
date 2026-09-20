from dotenv import load_dotenv
from fastapi import FastAPI

from src.api.routers import solicitudes
from src.infraestructura.persistencia.conexion import obtener_cliente

load_dotenv()

app = FastAPI(title="Trust 4P - API de Negocio")

app.include_router(solicitudes.router)


@app.get("/salud")
async def salud():
    cliente = obtener_cliente()
    await cliente.admin.command("ping")
    return {"estado": "operativo", "base_datos": "conectada"}
