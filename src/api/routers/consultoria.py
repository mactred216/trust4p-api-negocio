from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from src.api.dependencias import (
    obtener_caso_uso_consultar_diagnostico_asignado,
    obtener_caso_uso_listar_diagnosticos_empresa_asignada,
    obtener_caso_uso_listar_empresas_asignadas,
    obtener_caso_uso_obtener_cuestionario_asignado,
    obtener_caso_uso_registrar_recomendacion, obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.api.routers.diagnosticos import (CuestionarioResponse,
                                          DiagnosticoResponse,
                                          RecomendacionResponse, _a_response,
                                          _cuestionario_a_response)
from src.api.validadores_comunes import texto_no_vacio, texto_opcional_no_vacio
from src.aplicacion.casos_uso.gestionar_consultoria import (
    ConsultarDiagnosticoAsignado, ListarDiagnosticosDeEmpresaAsignada,
    ListarEmpresasAsignadas, ObtenerCuestionarioAsignado,
    RegistrarRecomendacion)
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)

router = APIRouter(prefix="/consultoria", tags=["consultoria"])

MENSAJE_SIN_ASIGNACION = "No tiene una asignación vigente con esta empresa"


class EmpresaAsignadaResponse(BaseModel):
    empresa_id: str
    empresa_nombre: str
    diagnostico_id: Optional[str]
    consecutivo: Optional[int]
    estado: Optional[str]
    iniciado_en: Optional[datetime]
    nivel: Optional[int]
    indice_global: Optional[Decimal]


class RegistrarRecomendacionRequest(BaseModel):
    titulo: str
    contenido: str
    dimension_codigo: Optional[str] = None
    visible: bool = True

    @field_validator("titulo")
    @classmethod
    def _titulo_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=200)

    @field_validator("contenido")
    @classmethod
    def _contenido_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=2000)

    @field_validator("dimension_codigo")
    @classmethod
    def _dimension_valida(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=50)


@router.get(
    "/empresas",
    response_model=list[EmpresaAsignadaResponse],
    summary="Empresas asignadas al consultor",
    description="RF-19/HU-020: empresas con asignación vigente, con el estado "
    "y el nivel de su diagnóstico más reciente. Filtros opcionales por "
    "estado del diagnóstico y por rango de fecha de inicio.",
)
async def listar_empresas_asignadas(
    estado: Optional[str] = Query(default=None),
    fecha_desde: Optional[datetime] = Query(default=None),
    fecha_hasta: Optional[datetime] = Query(default=None),
    caso_uso: ListarEmpresasAsignadas = Depends(
        obtener_caso_uso_listar_empresas_asignadas
    ),
    usuario_id: str = Depends(requiere_rol("consultor", "diagnosticos.consultar")),
):
    try:
        resumenes = await caso_uso.ejecutar(
            usuario_id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
    except AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="Usuario no autorizado")
    return [
        EmpresaAsignadaResponse(
            empresa_id=r.empresa_id,
            empresa_nombre=r.empresa_nombre,
            diagnostico_id=r.diagnostico_id,
            consecutivo=r.consecutivo,
            estado=r.estado,
            iniciado_en=r.iniciado_en,
            nivel=r.nivel,
            indice_global=r.indice_global,
        )
        for r in resumenes
    ]


@router.get(
    "/empresas/{empresa_id}/diagnosticos",
    response_model=list[DiagnosticoResponse],
    summary="Diagnósticos de una empresa asignada",
    description="RF-20/HU-021: solo de empresas con asignación vigente; un "
    "intento sobre una empresa ajena se deniega y queda en la bitácora.",
)
async def listar_diagnosticos_de_empresa(
    empresa_id: str,
    caso_uso: ListarDiagnosticosDeEmpresaAsignada = Depends(
        obtener_caso_uso_listar_diagnosticos_empresa_asignada
    ),
    usuario_id: str = Depends(requiere_rol("consultor", "diagnosticos.consultar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        diagnosticos = await caso_uso.ejecutar(usuario_id, empresa_id)
    except AccesoNoAutorizado:
        await registrar_accion(
            repo_auditoria,
            usuario_id,
            "empresas",
            empresa_id,
            "consultar",
            valores_nuevos={"acceso": "denegado"},
        )
        raise HTTPException(status_code=403, detail=MENSAJE_SIN_ASIGNACION)
    return [_a_response(d, incluir_ocultas=True) for d in diagnosticos]


@router.get(
    "/diagnosticos/{diagnostico_id}",
    response_model=DiagnosticoResponse,
    summary="Detalle de un diagnóstico de una empresa asignada",
    description="RF-20/HU-021: respuestas y resultados (nivel, puntaje por "
    "dimensión, perfil de cultura, lienzo, recomendaciones incluidas las aún "
    "no compartidas con la empresa).",
)
async def consultar_diagnostico_asignado(
    diagnostico_id: str,
    caso_uso: ConsultarDiagnosticoAsignado = Depends(
        obtener_caso_uso_consultar_diagnostico_asignado
    ),
    usuario_id: str = Depends(requiere_rol("consultor", "diagnosticos.consultar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
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
            valores_nuevos={"acceso": "denegado"},
        )
        raise HTTPException(status_code=403, detail=MENSAJE_SIN_ASIGNACION)
    return _a_response(diagnostico, incluir_ocultas=True)


@router.get(
    "/diagnosticos/{diagnostico_id}/cuestionario",
    response_model=CuestionarioResponse,
    summary="Cuestionario del diagnóstico de una empresa asignada",
    description="HU-021: enunciados, opciones y rúbrica de la versión del "
    "modelo aplicada, para leer las respuestas con su contexto.",
)
async def obtener_cuestionario_asignado(
    diagnostico_id: str,
    caso_uso: ObtenerCuestionarioAsignado = Depends(
        obtener_caso_uso_obtener_cuestionario_asignado
    ),
    usuario_id: str = Depends(requiere_rol("consultor", "diagnosticos.consultar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        await registrar_accion(
            repo_auditoria,
            usuario_id,
            "diagnosticos",
            diagnostico_id,
            "consultar",
            valores_nuevos={"acceso": "denegado"},
        )
        raise HTTPException(status_code=403, detail=MENSAJE_SIN_ASIGNACION)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _cuestionario_a_response(modelo)


@router.post(
    "/diagnosticos/{diagnostico_id}/recomendaciones",
    response_model=RecomendacionResponse,
    status_code=201,
    summary="Registrar una recomendación sobre un diagnóstico",
    description="RF-21/HU-022: exclusivo del consultor con la empresa "
    "asignada. Queda con su autor y fecha, y notifica al representante si "
    "es visible. No admite diagnósticos cerrados.",
)
async def registrar_recomendacion(
    diagnostico_id: str,
    datos: RegistrarRecomendacionRequest,
    caso_uso: RegistrarRecomendacion = Depends(
        obtener_caso_uso_registrar_recomendacion
    ),
    usuario_id: str = Depends(requiere_rol("consultor", "recomendaciones.registrar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        recomendacion = await caso_uso.ejecutar(
            usuario_id,
            diagnostico_id,
            titulo=datos.titulo,
            contenido=datos.contenido,
            dimension_codigo=datos.dimension_codigo,
            visible=datos.visible,
        )
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        await registrar_accion(
            repo_auditoria,
            usuario_id,
            "diagnosticos",
            diagnostico_id,
            "actualizar",
            valores_nuevos={"acceso": "denegado"},
        )
        raise HTTPException(status_code=403, detail=MENSAJE_SIN_ASIGNACION)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "diagnosticos",
        diagnostico_id,
        "actualizar",
        valores_nuevos={"recomendacion_registrada": recomendacion.titulo},
    )
    return RecomendacionResponse(
        origen=recomendacion.origen,
        dimension_codigo=recomendacion.dimension_codigo,
        titulo=recomendacion.titulo,
        contenido=recomendacion.contenido,
        prioridad=recomendacion.prioridad,
        visible=recomendacion.visible,
        autor_id=recomendacion.autor_id,
        autor_nombre=recomendacion.autor_nombre,
        creado_en=recomendacion.creado_en,
    )
