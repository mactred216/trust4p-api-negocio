from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.dependencias import (obtener_caso_uso_simular_pesos,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.api.validadores_comunes import peso_valido
from src.aplicacion.casos_uso.gestionar_modelo_madurez import \
    ModeloNoEncontrado
from src.aplicacion.casos_uso.simular_pesos import (SimularPesosModelo,
                                                    SinDiagnosticosParaSimular)

router = APIRouter(prefix="/modelos-madurez", tags=["simulaciones"])


class SimularPesosRequest(BaseModel):
    pesos: dict[str, Decimal] = Field(
        description="Peso propuesto por código de dimensión; debe cubrir todas "
        "las dimensiones del modelo y sumar exactamente 1."
    )
    diagnostico_ids: Optional[list[str]] = Field(
        default=None,
        max_length=500,
        description="Diagnósticos a incluir; si se omite, todos los históricos "
        "calculados con esta versión del modelo.",
    )

    @field_validator("pesos")
    @classmethod
    def _pesos_validos(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        if not v:
            raise ValueError("Debe informar los pesos por dimensión")
        return {codigo: peso_valido(peso) for codigo, peso in v.items()}


class ComparacionResponse(BaseModel):
    diagnostico_id: str
    empresa_id: str
    empresa_nombre: str
    consecutivo: int
    indice_original: Decimal
    nivel_original: int
    indice_simulado: Decimal
    nivel_simulado: int
    variacion_indice: Decimal
    cambia_de_nivel: bool


class NoSimulableResponse(BaseModel):
    diagnostico_id: str
    motivo: str


class SimulacionResponse(BaseModel):
    modelo_version: str
    total: int
    con_cambio_de_nivel: int
    variacion_promedio: Decimal
    comparaciones: list[ComparacionResponse]
    no_simulables: list[NoSimulableResponse]


@router.post(
    "/{modelo_id}/simulacion",
    response_model=SimulacionResponse,
    summary="Simular un cambio de pesos por dimensión",
    description="RF-35/HU-035: recalcula en memoria los diagnósticos históricos "
    "de la versión con los pesos propuestos y devuelve la comparación entre el "
    "resultado original y el simulado. No modifica ningún dato almacenado.",
)
async def simular_pesos(
    modelo_id: str,
    datos: SimularPesosRequest,
    caso_uso: SimularPesosModelo = Depends(obtener_caso_uso_simular_pesos),
    usuario_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        resultado = await caso_uso.ejecutar(
            modelo_id, datos.pesos, datos.diagnostico_ids
        )
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except (SinDiagnosticosParaSimular, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "modelos_madurez",
        modelo_id,
        "simular",
        valores_nuevos={
            "pesos": {codigo: str(p) for codigo, p in datos.pesos.items()},
            "diagnosticos_simulados": resultado.total,
        },
    )
    return SimulacionResponse(
        modelo_version=resultado.modelo_version,
        total=resultado.total,
        con_cambio_de_nivel=resultado.con_cambio_de_nivel,
        variacion_promedio=resultado.variacion_promedio,
        comparaciones=[ComparacionResponse(**vars(c)) for c in resultado.comparaciones],
        no_simulables=[NoSimulableResponse(**vars(n)) for n in resultado.no_simulables],
    )
