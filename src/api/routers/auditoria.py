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
    description="Exclusivo del administrador. Permite filtrar por entidad, id del recurso o usuario.",
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
    limite: int = Query(default=50, le=200),
    caso_uso: ConsultarAuditoria = Depends(obtener_caso_uso_consultar_auditoria),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    registros = await caso_uso.ejecutar(
        entidad=entidad, entidad_id=entidad_id, usuario_id=usuario_id, limite=limite
    )
    return [
        RegistroAuditoriaResponse(
            id=r.id,
            usuario_id=r.usuario_id,
            entidad=r.entidad,
            entidad_id=r.entidad_id,
            accion=r.accion,
            valores_anteriores=r.valores_anteriores,
            valores_nuevos=r.valores_nuevos,
            registrado_en=r.registrado_en,
        )
        for r in registros
    ]
