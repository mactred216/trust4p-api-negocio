from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencias import obtener_caso_uso_obtener_version_vigente
from src.api.middleware.limites import limite_modelo_publico
from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    ModeloNoEncontrado, ObtenerVersionVigente)

router = APIRouter(prefix="/modelo-vigente", tags=["modelo"])


class DimensionPublicaResponse(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str]
    orden: int
    peso: Decimal


class NivelPublicoResponse(BaseModel):
    numero: int
    nombre: str
    descripcion: str
    umbral_min: Decimal
    umbral_max: Decimal


class ModeloPublicoResponse(BaseModel):
    version: str
    nombre: str
    escala_min: int
    escala_max: int
    dimensiones: list[DimensionPublicaResponse]
    niveles: list[NivelPublicoResponse]


@router.get(
    "",
    response_model=ModeloPublicoResponse,
    dependencies=[Depends(limite_modelo_publico)],
    summary="Estructura pública del modelo de madurez vigente",
    description="Público: dimensiones y niveles de la versión vigente, sin "
    "preguntas ni configuración interna. Alimenta la página de inicio para que "
    "refleje siempre el modelo publicado.",
)
async def obtener_modelo_publico(
    caso_uso: ObtenerVersionVigente = Depends(obtener_caso_uso_obtener_version_vigente),
):
    try:
        modelo = await caso_uso.ejecutar()
    except ModeloNoEncontrado:
        raise HTTPException(
            status_code=404, detail="No hay ninguna versión publicada del modelo"
        )
    return ModeloPublicoResponse(
        version=modelo.version,
        nombre=modelo.nombre,
        escala_min=modelo.escala_min,
        escala_max=modelo.escala_max,
        dimensiones=[
            DimensionPublicaResponse(
                codigo=d.codigo,
                nombre=d.nombre,
                descripcion=d.descripcion,
                orden=d.orden,
                peso=d.peso,
            )
            for d in sorted(modelo.dimensiones, key=lambda d: d.orden)
        ],
        niveles=[
            NivelPublicoResponse(
                numero=n.nivel,
                nombre=n.nombre,
                descripcion=n.descripcion,
                umbral_min=n.umbral_min,
                umbral_max=n.umbral_max,
            )
            for n in sorted(modelo.niveles, key=lambda n: n.nivel)
        ],
    )
