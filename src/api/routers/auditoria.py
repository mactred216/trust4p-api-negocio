from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.dependencias import obtener_caso_uso_consultar_auditoria
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.consultar_auditoria import ConsultarAuditoria

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


class RegistroAuditoriaResponse(BaseModel):
    id: str
    usuario_id: Optional[str]
    usuario_nombre: Optional[str] = None
    usuario_correo: Optional[str] = None
    entidad: str
    entidad_id: Optional[str]
    accion: str
    valores_anteriores: Optional[dict]
    valores_nuevos: Optional[dict]
    registrado_en: datetime


@router.get(
    "",
    response_model=list[RegistroAuditoriaResponse],
    summary="Consultar bitácora de auditoría",
    description="Exclusivo del administrador. Permite filtrar por entidad, id del recurso o "
    "usuario (por nombre o correo, completo o parcial). Cada registro trae el nombre y el "
    "correo de quien ejecutó la acción.",
)
async def consultar_auditoria(
    entidad: Optional[str] = Query(
        default=None, description="Nombre de la colección, ej: usuarios"
    ),
    entidad_id: Optional[str] = Query(
        default=None, description="Id del recurso afectado"
    ),
    usuario_id: Optional[str] = Query(
        default=None, description="Id de quien ejecutó la acción"
    ),
    usuario: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Nombre o correo (completo o parcial) de quien ejecutó la acción",
    ),
    limite: int = Query(default=50, le=200),
    caso_uso: ConsultarAuditoria = Depends(obtener_caso_uso_consultar_auditoria),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "auditoria.consultar")
    ),
):
    entradas = await caso_uso.ejecutar(
        entidad=entidad,
        entidad_id=entidad_id,
        usuario_id=usuario_id,
        limite=limite,
        usuario=usuario,
    )
    return [
        RegistroAuditoriaResponse(
            id=e.registro.id,
            usuario_id=e.registro.usuario_id,
            usuario_nombre=e.usuario_nombre,
            usuario_correo=e.usuario_correo,
            entidad=e.registro.entidad,
            entidad_id=e.registro.entidad_id,
            accion=e.registro.accion,
            valores_anteriores=e.registro.valores_anteriores,
            valores_nuevos=e.registro.valores_nuevos,
            registrado_en=e.registro.registrado_en,
        )
        for e in entradas
    ]
