import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencias import plazo_evaluacion
from src.api.middleware.cabeceras_seguridad import CabecerasSeguridad
from src.api.routers import (auditoria, autenticacion, consultoria, demo,
                             diagnosticos, empresas, indicadores,
                             modelo_publico, modelos_madurez, perfil, reportes,
                             roles, sectores, simulaciones, solicitudes,
                             usuarios)
from src.aplicacion.casos_uso.evaluar_diagnostico import \
    RecuperarEvaluacionesInterrumpidas
from src.infraestructura.persistencia.conexion import (obtener_base_datos,
                                                       obtener_cliente)
from src.infraestructura.persistencia.inicializacion import \
    inicializar_base_datos
from src.infraestructura.persistencia.repositorio_mongo_diagnostico import \
    RepositorioMongoDiagnostico

load_dotenv()

registro = logging.getLogger("trust4p.arranque")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Arranque: asegura el catálogo de permisos y los roles de sistema
    (idempotente). Si la base no responde no se detiene el proceso: /salud lo
    reportará."""
    try:
        await inicializar_base_datos(obtener_base_datos())
    except Exception:
        registro.exception("No se pudo inicializar la base de datos")
    # C7: una instancia que terminó a mitad de una evaluación la deja
    # 'completado' sin dueño; al arrancar se pasa a 'fallido' para reprocesarla.
    try:
        await RecuperarEvaluacionesInterrumpidas(
            RepositorioMongoDiagnostico(obtener_base_datos()), plazo_evaluacion()
        ).ejecutar()
    except Exception:
        registro.exception("No se pudieron revisar las evaluaciones interrumpidas")
    yield


app = FastAPI(title="Trust 4P - API de Negocio", lifespan=ciclo_de_vida)

# RNF-05 / integración con el frontend: orígenes permitidos por variable de
# entorno (la sesión viaja en cookie, por eso allow_credentials y orígenes
# explícitos, nunca "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.getenv(
            "CORS_ORIGENES", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if o.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["Content-Disposition", "Retry-After"],
)
app.add_middleware(CabecerasSeguridad)

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
app.include_router(demo.router, prefix="/v1")
app.include_router(sectores.router, prefix="/v1")
app.include_router(modelo_publico.router, prefix="/v1")
app.include_router(reportes.router, prefix="/v1")


@app.get("/salud")
async def salud():
    cliente = obtener_cliente()
    await cliente.admin.command("ping")
    return {"estado": "operativo", "base_datos": "conectada"}
