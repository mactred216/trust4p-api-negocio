import csv
import io
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from src.api.dependencias import (obtener_caso_uso_consultar_indicadores,
                                  obtener_caso_uso_exportar_datos_agregados,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.gestionar_indicadores import (
    ConsultarIndicadoresAgregados, ExportarDatosAgregados, FiltroInvalido)

router = APIRouter(prefix="/indicadores", tags=["indicadores"])

COLUMNAS_EXPORTACION = [
    "sector_codigo",
    "sector_nombre",
    "tamano",
    "nivel",
    "empresas",
    "indice_promedio",
]


class GrupoIndicadorResponse(BaseModel):
    clave: str
    etiqueta: str
    empresas: int
    porcentaje: Decimal
    indice_promedio: Decimal


class IndicadoresResponse(BaseModel):
    detalle_disponible: bool
    mensaje: Optional[str] = None
    total_empresas: Optional[int] = None
    indice_promedio: Optional[Decimal] = None
    por_nivel: list[GrupoIndicadorResponse] = []
    por_sector: list[GrupoIndicadorResponse] = []
    por_tamano: list[GrupoIndicadorResponse] = []
    promedio_por_dimension: dict[str, Decimal] = {}


@router.get(
    "/agregados",
    response_model=IndicadoresResponse,
    summary="Tablero de indicadores agregados",
    description="RF-22/HU-023: indicadores por sector, tamaño de empresa "
    "(micro, pequena, mediana, grande) y nivel de madurez sobre las empresas "
    "asignadas al consultor. Si el filtro agrupa menos de tres empresas no se "
    "presenta el detalle (detalle_disponible=false).",
)
async def consultar_indicadores(
    sector: Optional[str] = Query(default=None, description="Código del sector"),
    tamano: Optional[str] = Query(default=None),
    caso_uso: ConsultarIndicadoresAgregados = Depends(
        obtener_caso_uso_consultar_indicadores
    ),
    usuario_id: str = Depends(requiere_rol("consultor")),
):
    try:
        indicadores = await caso_uso.ejecutar(
            usuario_id, sector_codigo=sector, tamano=tamano
        )
    except FiltroInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    return IndicadoresResponse(**asdict(indicadores))


@router.get(
    "/exportacion",
    summary="Exportar datos agregados (CSV)",
    description="RF-46/HU-023: exclusivo del administrador. CSV anonimizado por "
    "sector x tamaño x nivel; las celdas con menos de tres empresas se omiten. "
    "El evento queda en la bitácora.",
    response_class=Response,
)
async def exportar_datos_agregados(
    sector: Optional[str] = Query(default=None),
    tamano: Optional[str] = Query(default=None),
    fecha_desde: Optional[datetime] = Query(default=None),
    fecha_hasta: Optional[datetime] = Query(default=None),
    caso_uso: ExportarDatosAgregados = Depends(
        obtener_caso_uso_exportar_datos_agregados
    ),
    usuario_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        filas = await caso_uso.ejecutar(
            sector_codigo=sector,
            tamano=tamano,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
    except FiltroInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))

    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS_EXPORTACION)
    for f in filas:
        escritor.writerow(
            [
                f.sector_codigo,
                f.sector_nombre,
                f.tamano,
                f.nivel,
                f.empresas,
                f.indice_promedio,
            ]
        )

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "diagnosticos",
        None,
        "exportar",
        valores_nuevos={
            "filtros": {
                "sector": sector,
                "tamano": tamano,
                "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
            },
            "filas": len(filas),
        },
    )
    return Response(
        content="﻿" + salida.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="indicadores_agregados.csv"'
        },
    )
