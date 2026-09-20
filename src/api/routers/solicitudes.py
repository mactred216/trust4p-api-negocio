from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from src.api.dependencias import (obtener_caso_uso_radicar_solicitud,
                                  obtener_caso_uso_resolver_solicitud,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.radicar_solicitud import (RadicarSolicitud,
                                                        SolicitudDuplicada)
from src.aplicacion.casos_uso.resolver_solicitud import (ResolverSolicitud,
                                                         SolicitudNoEncontrada)
from src.dominio.entidades.empresa import Sector

router = APIRouter(prefix="/solicitudes-acceso", tags=["solicitudes"])


class RadicarSolicitudRequest(BaseModel):
    nombre_empresa: str
    correo_solicitante: EmailStr
    nombre_solicitante: str

    @field_validator("nombre_empresa", "nombre_solicitante")
    @classmethod
    def texto_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo no puede estar vacío")
        if len(v) < 2:
            raise ValueError("Debe tener al menos 2 caracteres")
        if len(v) > 200:
            raise ValueError("No puede exceder 200 caracteres")
        return v


class SolicitudResponse(BaseModel):
    id: str
    nombre_empresa: str
    estado: str


class AprobarSolicitudRequest(BaseModel):
    sector_id: str
    sector_codigo: str
    sector_nombre: str

    @field_validator("sector_id", "sector_codigo", "sector_nombre")
    @classmethod
    def texto_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo no puede estar vacío")
        return v


class RechazarSolicitudRequest(BaseModel):
    motivo: str

    @field_validator("motivo")
    @classmethod
    def motivo_valido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El motivo de rechazo es obligatorio")
        if len(v) < 10:
            raise ValueError(
                "El motivo debe ser suficientemente descriptivo (mínimo 10 caracteres)"
            )
        if len(v) > 500:
            raise ValueError("El motivo no puede exceder 500 caracteres")
        return v


class EmpresaResponse(BaseModel):
    id: str
    nombre: str


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


@router.post(
    "/{solicitud_id}/aprobar",
    response_model=EmpresaResponse,
    summary="Aprobar una solicitud de acceso",
    description="Exclusivo del administrador. Crea la empresa y marca la solicitud como aprobada.",
)
async def aprobar_solicitud(
    solicitud_id: str,
    datos: AprobarSolicitudRequest,
    caso_uso: ResolverSolicitud = Depends(obtener_caso_uso_resolver_solicitud),
    usuario_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    sector = Sector(
        id=datos.sector_id, codigo=datos.sector_codigo, nombre=datos.sector_nombre
    )
    try:
        empresa, codigo = await caso_uso.aprobar(solicitud_id, sector)
        print(f"CÓDIGO DE INVITACIÓN (temporal, solo para pruebas): {codigo}")
    except SolicitudNoEncontrada:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "solicitudes_acceso",
        solicitud_id,
        "actualizar",
        valores_nuevos={"estado": "aprobada", "empresa_id": empresa.id},
    )

    return EmpresaResponse(id=empresa.id, nombre=empresa.nombre)


@router.post(
    "/{solicitud_id}/rechazar",
    status_code=204,
    summary="Rechazar una solicitud de acceso",
    description="Exclusivo del administrador. Exige un motivo explícito.",
)
async def rechazar_solicitud(
    solicitud_id: str,
    datos: RechazarSolicitudRequest,
    caso_uso: ResolverSolicitud = Depends(obtener_caso_uso_resolver_solicitud),
    usuario_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        await caso_uso.rechazar(solicitud_id, datos.motivo)
    except SolicitudNoEncontrada:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "solicitudes_acceso",
        solicitud_id,
        "actualizar",
        valores_nuevos={"estado": "rechazada", "motivo": datos.motivo},
    )
