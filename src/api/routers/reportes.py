from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from src.api.dependencias import (
    obtener_caso_uso_generar_informe_de_empresa,
    obtener_caso_uso_listar_empresas_para_reporte,
    obtener_repositorio_auditoria, obtener_repositorio_modelo_madurez)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_algun_rol
from src.aplicacion.casos_uso.generar_informe import (DiagnosticoSinResultado,
                                                      nombres_de_dimensiones)
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.aplicacion.casos_uso.gestionar_reportes import (
    FiltroInvalido, GenerarInformeDeEmpresa, ListarEmpresasParaReporte)
from src.infraestructura.informes.generador_informe_pdf import \
    generar_informe_pdf

router = APIRouter(prefix="/reportes", tags=["reportes"])

# El administrador alcanza a todas las empresas; el consultor, a las que tiene
# asignadas (lo decide el caso de uso). Ambos necesitan el permiso.
acceso_reportes = requiere_algun_rol(
    {"administrador": "informes.descargar", "consultor": "informes.descargar"}
)


class DiagnosticoReporteResponse(BaseModel):
    id: str
    consecutivo: int
    estado: str
    nivel: int
    indice_global: Decimal
    evaluado_en: Optional[datetime]


class EmpresaReporteResponse(BaseModel):
    empresa_id: str
    nombre: str
    nit: Optional[str]
    sector_codigo: str
    sector_nombre: str
    numero_empleados: Optional[int]
    tamano: Optional[str]
    diagnosticos: list[DiagnosticoReporteResponse]


@router.get(
    "/empresas",
    response_model=list[EmpresaReporteResponse],
    summary="Empresas con informe disponible",
    description="El administrador ve todas las empresas; el consultor solo las "
    "que tiene asignadas. Filtros por nombre (contiene), sector y tamaño. Cada "
    "empresa trae los diagnósticos evaluados o cerrados de los que se puede "
    "descargar el informe.",
)
async def listar_empresas_para_reporte(
    nombre: Optional[str] = Query(default=None, max_length=100),
    sector: Optional[str] = Query(default=None, max_length=50),
    tamano: Optional[str] = Query(default=None),
    caso_uso: ListarEmpresasParaReporte = Depends(
        obtener_caso_uso_listar_empresas_para_reporte
    ),
    usuario_id: str = Depends(acceso_reportes),
):
    try:
        empresas = await caso_uso.ejecutar(
            usuario_id, nombre=nombre, sector_codigo=sector, tamano=tamano
        )
    except FiltroInvalido as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")
    return [
        EmpresaReporteResponse(
            empresa_id=e.empresa_id,
            nombre=e.nombre,
            nit=e.nit,
            sector_codigo=e.sector_codigo,
            sector_nombre=e.sector_nombre,
            numero_empleados=e.numero_empleados,
            tamano=e.tamano,
            diagnosticos=[
                DiagnosticoReporteResponse(**vars(d)) for d in e.diagnosticos
            ],
        )
        for e in empresas
    ]


@router.get(
    "/diagnosticos/{diagnostico_id}/informe",
    summary="Descargar el informe de un diagnóstico de una empresa",
    description="PDF del informe (nivel, desglose, perfil de cultura, lienzo y "
    "recomendaciones). El administrador puede de cualquier empresa; el "
    "consultor solo de empresas con asignación vigente. Cada descarga queda en "
    "la bitácora de auditoría.",
)
async def descargar_informe_de_empresa(
    diagnostico_id: str,
    caso_uso: GenerarInformeDeEmpresa = Depends(
        obtener_caso_uso_generar_informe_de_empresa
    ),
    usuario_id: str = Depends(acceso_reportes),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
    repo_modelo=Depends(obtener_repositorio_modelo_madurez),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        await registrar_accion(
            repo_auditoria,
            usuario_id,
            "diagnosticos",
            diagnostico_id,
            "consultar",
            valores_nuevos={"accion": "descargar_informe", "acceso": "denegado"},
        )
        raise HTTPException(
            status_code=403, detail="No tiene acceso al informe de esta empresa"
        )
    except DiagnosticoSinResultado:
        raise HTTPException(
            status_code=409,
            detail="El diagnóstico todavía no tiene un resultado evaluado",
        )

    contenido_pdf = generar_informe_pdf(
        diagnostico, await nombres_de_dimensiones(repo_modelo, diagnostico)
    )

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "diagnosticos",
        diagnostico_id,
        "consultar",
        valores_nuevos={
            "accion": "descargar_informe",
            "empresa_id": diagnostico.empresa_id,
        },
    )

    nombre_archivo = f"informe-{diagnostico.empresa_nombre}-diagnostico-{diagnostico.consecutivo}.pdf"
    nombre_seguro = "".join(
        c if c.isascii() and (c.isalnum() or c in "-._") else "-"
        for c in nombre_archivo
    )
    return Response(
        content=contenido_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_seguro}"'},
    )
