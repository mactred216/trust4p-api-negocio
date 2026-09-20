from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from src.api.dependencias import obtener_caso_uso_radicar_solicitud
from src.aplicacion.casos_uso.radicar_solicitud import (RadicarSolicitud,
                                                        SolicitudDuplicada)

router = APIRouter(prefix="/solicitudes-acceso", tags=["solicitudes"])


class RadicarSolicitudRequest(BaseModel):
    nombre_empresa: str
    correo_solicitante: EmailStr
    nombre_solicitante: str


class SolicitudResponse(BaseModel):
    id: str
    nombre_empresa: str
    estado: str


@router.post("", response_model=SolicitudResponse, status_code=201)
async def radicar_solicitud(
    datos: RadicarSolicitudRequest,
    caso_uso: RadicarSolicitud = Depends(obtener_caso_uso_radicar_solicitud),
):
    try:
        solicitud = await caso_uso.ejecutar(
            nombre_empresa=datos.nombre_empresa,
            correo_solicitante=datos.correo_solicitante,
            nombre_solicitante=datos.nombre_solicitante,
        )
    except SolicitudDuplicada:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una solicitud pendiente con este correo",
        )

    return SolicitudResponse(
        id=solicitud.id,
        nombre_empresa=solicitud.nombre_empresa,
        estado=solicitud.estado.value,
    )
