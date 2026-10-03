from dotenv import load_dotenv
from fastapi import FastAPI

from src.api.routers import (auditoria, autenticacion, consultoria,
                             diagnosticos, empresas, indicadores,
                             modelos_madurez, perfil, roles, simulaciones,
                             solicitudes, usuarios)
from src.infraestructura.persistencia.conexion import obtener_cliente

load_dotenv()

app = FastAPI(title="Trust 4P - API de Negocio")

app.include_router(solicitudes.router, prefix="/v1")
app.include_router(autenticacion.router, prefix="/v1")
app.include_router(empresas.router, prefix="/v1")
app.include_router(usuarios.router, prefix="/v1")
app.include_router(roles.router, prefix="/v1")
app.include_router(auditoria.router, prefix="/v1")
app.include_router(modelos_madurez.router, prefix="/v1")
app.include_router(perfil.router, prefix="/v1")
app.include_router(diagnosticos.router, prefix="/v1")
app.include_router(consultoria.router, prefix="/v1")
app.include_router(indicadores.router, prefix="/v1")
app.include_router(simulaciones.router, prefix="/v1")


@app.get("/salud")
async def salud():
    cliente = obtener_cliente()
    await cliente.admin.command("ping")
    return {"estado": "operativo", "base_datos": "conectada"}
