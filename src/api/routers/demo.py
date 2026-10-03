import os
from dataclasses import asdict
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.dependencias import (obtener_caso_uso_calcular_resultado_demo,
                                  obtener_caso_uso_obtener_preguntas_demo)
from src.api.middleware.limite_peticiones import (LimitadorPeticiones,
                                                  limitar_peticiones)
from src.api.routers.diagnosticos import (CondicionActivacionResponse,
                                          OpcionPreguntaResponse,
                                          PreguntaCuestionarioResponse)
from src.api.validadores_comunes import texto_no_vacio
from src.aplicacion.casos_uso.diagnostico_demo import (
    CalcularResultadoDemo, DemostracionNoDisponible, ObtenerPreguntasDemo)
from src.aplicacion.casos_uso.gestionar_diagnostico import NoHayVersionVigente
from src.dominio.servicios.diagnostico_demo import (AVISO_DEMOSTRACION,
                                                    RespuestaDemo)

router = APIRouter(prefix="/demo", tags=["demo"])

# RNF-09: endpoints públicos con tope estricto por origen. Ajustables por entorno.
limitador_preguntas = LimitadorPeticiones(
    maximo=int(os.getenv("DEMO_PREGUNTAS_MAX", "30")),
    ventana_segundos=int(os.getenv("DEMO_PREGUNTAS_VENTANA_SEGUNDOS", "60")),
)
limitador_resultado = LimitadorPeticiones(
    maximo=int(os.getenv("DEMO_RESULTADO_MAX", "10")),
    ventana_segundos=int(os.getenv("DEMO_RESULTADO_VENTANA_SEGUNDOS", "3600")),
)

SOLICITUD_ACCESO = "/v1/solicitudes"


class PreguntasDemoResponse(BaseModel):
    modelo_version: str
    aviso: str
    preguntas: list[PreguntaCuestionarioResponse]


class RespuestaDemoRequest(BaseModel):
    pregunta_codigo: str
    opciones_codigo: list[str] = Field(default=[], max_length=20)
    valor: Optional[Decimal] = None
    texto: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("pregunta_codigo")
    @classmethod
    def _codigo_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=50)


class ResultadoDemoRequest(BaseModel):
    respuestas: list[RespuestaDemoRequest] = Field(min_length=1, max_length=200)


class DimensionDemoResponse(BaseModel):
    codigo: str
    nombre: str
    puntaje: Decimal


class ResultadoDemoResponse(BaseModel):
    es_demostracion: bool = True
    aviso: str
    indice_global: Decimal
    nivel: int
    nivel_nombre: str
    nivel_descripcion: str
    dimensiones: list[DimensionDemoResponse]
    dimensiones_sin_evaluar: list[str]
    preguntas_respondidas: int
    total_preguntas: int
    radicar_solicitud_en: str = SOLICITUD_ACCESO


@router.get(
    "/preguntas",
    response_model=PreguntasDemoResponse,
    summary="Preguntas del diagnóstico de demostración",
    description="RF-49/HU-007: subconjunto público del modelo vigente. No exige "
    "autenticación y tiene límite de peticiones por origen.",
    dependencies=[Depends(limitar_peticiones(limitador_preguntas))],
)
async def obtener_preguntas_demo(
    caso_uso: ObtenerPreguntasDemo = Depends(obtener_caso_uso_obtener_preguntas_demo),
):
    try:
        version, preguntas = await caso_uso.ejecutar()
    except (NoHayVersionVigente, DemostracionNoDisponible):
        raise HTTPException(
            status_code=503, detail="El diagnóstico de demostración no está disponible"
        )
    return PreguntasDemoResponse(
        modelo_version=version,
        aviso=AVISO_DEMOSTRACION,
        preguntas=[
            PreguntaCuestionarioResponse(
                codigo=p.codigo,
                dimension_codigo=p.dimension_codigo,
                enunciado=p.enunciado,
                tipo=p.tipo,
                obligatoria=p.obligatoria,
                orden=p.orden,
                ayuda=p.ayuda,
                opciones=[
                    OpcionPreguntaResponse(
                        codigo=o.codigo, etiqueta=o.etiqueta, valor=o.valor
                    )
                    for o in p.opciones
                ],
                condicion=(
                    CondicionActivacionResponse(
                        pregunta_codigo=p.condicion.pregunta_codigo,
                        operador=p.condicion.operador,
                        valor=p.condicion.valor,
                    )
                    if p.condicion
                    else None
                ),
            )
            for p in preguntas
        ],
    )


@router.post(
    "/resultado",
    response_model=ResultadoDemoResponse,
    summary="Resultado orientativo del diagnóstico de demostración",
    description="RF-49/HU-007: calcula el resultado al vuelo. No persiste "
    "respuestas, no crea diagnóstico ni registra datos de la persona. Límite "
    "estricto de peticiones por origen.",
    dependencies=[Depends(limitar_peticiones(limitador_resultado))],
)
async def calcular_resultado_demo(
    datos: ResultadoDemoRequest,
    caso_uso: CalcularResultadoDemo = Depends(obtener_caso_uso_calcular_resultado_demo),
):
    try:
        resultado = await caso_uso.ejecutar(
            [
                RespuestaDemo(
                    pregunta_codigo=r.pregunta_codigo,
                    opciones_codigo=r.opciones_codigo,
                    valor=r.valor,
                    texto=r.texto,
                )
                for r in datos.respuestas
            ]
        )
    except (NoHayVersionVigente, DemostracionNoDisponible):
        raise HTTPException(
            status_code=503, detail="El diagnóstico de demostración no está disponible"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ResultadoDemoResponse(**asdict(resultado))
