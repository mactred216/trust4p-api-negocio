from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from src.api.dependencias import (obtener_caso_uso_completar_diagnostico,
                                  obtener_caso_uso_consultar_diagnostico,
                                  obtener_caso_uso_diagnostico_en_curso,
                                  obtener_caso_uso_guardar_respuesta,
                                  obtener_caso_uso_iniciar_diagnostico,
                                  obtener_caso_uso_listar_diagnosticos_empresa)
from src.api.middleware.autorizacion import requiere_rol
from src.api.validadores_comunes import texto_no_vacio
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, CompletarDiagnostico, ConsultarDiagnostico,
    DiagnosticoEnCursoExistente, DiagnosticoNoEncontrado, GuardarRespuesta,
    IniciarDiagnostico, ListarDiagnosticosDeEmpresa, NoHayVersionVigente,
    ObtenerDiagnosticoEnCurso)

router = APIRouter(prefix="/diagnosticos", tags=["diagnosticos"])


class RespuestaResponse(BaseModel):
    pregunta_codigo: str
    dimension_codigo: str
    opcion_codigo: Optional[str]
    valor: Optional[Decimal]
    texto: Optional[str]
    respondida_en: datetime


class DiagnosticoResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nombre: str
    usuario_id: str
    modelo_version: str
    consecutivo: int
    estado: str
    porcentaje_avance: int
    respuestas: list[RespuestaResponse]
    iniciado_en: datetime
    completado_en: Optional[datetime]
    evaluado_en: Optional[datetime]
    cerrado_en: Optional[datetime]


class GuardarRespuestaRequest(BaseModel):
    pregunta_codigo: str
    opcion_codigo: Optional[str] = None
    valor: Optional[Decimal] = None
    texto: Optional[str] = None

    @field_validator("pregunta_codigo")
    @classmethod
    def _pregunta_codigo_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=50)

    @model_validator(mode="after")
    def _al_menos_un_contenido(self) -> "GuardarRespuestaRequest":
        if self.opcion_codigo is None and self.valor is None and self.texto is None:
            raise ValueError(
                "Debe enviar opcion_codigo, valor o texto según el tipo de pregunta"
            )
        return self


def _a_response(diagnostico) -> DiagnosticoResponse:
    return DiagnosticoResponse(
        id=diagnostico.id,
        empresa_id=diagnostico.empresa_id,
        empresa_nombre=diagnostico.empresa_nombre,
        usuario_id=diagnostico.usuario_id,
        modelo_version=diagnostico.modelo_version,
        consecutivo=diagnostico.consecutivo,
        estado=diagnostico.estado,
        porcentaje_avance=diagnostico.porcentaje_avance,
        respuestas=[
            RespuestaResponse(
                pregunta_codigo=r.pregunta_codigo,
                dimension_codigo=r.dimension_codigo,
                opcion_codigo=r.opcion_codigo,
                valor=r.valor,
                texto=r.texto,
                respondida_en=r.respondida_en,
            )
            for r in diagnostico.respuestas
        ],
        iniciado_en=diagnostico.iniciado_en,
        completado_en=diagnostico.completado_en,
        evaluado_en=diagnostico.evaluado_en,
        cerrado_en=diagnostico.cerrado_en,
    )


@router.post(
    "",
    response_model=DiagnosticoResponse,
    status_code=201,
    summary="Iniciar un nuevo diagnóstico",
    description="Exclusivo del representante de empresa. RF-11/HU-12: exige "
    "que no haya un diagnóstico sin cerrar para la empresa y que exista una "
    "versión publicada del modelo de madurez.",
)
async def iniciar_diagnostico(
    caso_uso: IniciarDiagnostico = Depends(obtener_caso_uso_iniciar_diagnostico),
    usuario_id: str = Depends(requiere_rol("representante")),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id)
    except DiagnosticoEnCursoExistente:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un diagnóstico sin cerrar para su empresa; debe concluirlo antes de iniciar uno nuevo",
        )
    except NoHayVersionVigente:
        raise HTTPException(
            status_code=409,
            detail="No hay ninguna versión publicada del modelo de madurez todavía",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(diagnostico)


@router.get(
    "/en-curso",
    response_model=DiagnosticoResponse,
    summary="Recuperar el diagnóstico en curso de mi empresa",
    description="RF-09/HU-10: permite reanudar el cuestionario donde quedó.",
)
async def obtener_diagnostico_en_curso(
    caso_uso: ObtenerDiagnosticoEnCurso = Depends(
        obtener_caso_uso_diagnostico_en_curso
    ),
    usuario_id: str = Depends(requiere_rol("representante")),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(
            status_code=404, detail="No hay ningún diagnóstico en curso para su empresa"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(diagnostico)


@router.get(
    "",
    response_model=list[DiagnosticoResponse],
    summary="Histórico de diagnósticos de mi empresa",
)
async def listar_mis_diagnosticos(
    caso_uso: ListarDiagnosticosDeEmpresa = Depends(
        obtener_caso_uso_listar_diagnosticos_empresa
    ),
    usuario_id: str = Depends(requiere_rol("representante")),
):
    try:
        diagnosticos = await caso_uso.ejecutar(usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_a_response(d) for d in diagnosticos]


@router.get("/{diagnostico_id}", response_model=DiagnosticoResponse)
async def consultar_diagnostico(
    diagnostico_id: str,
    caso_uso: ConsultarDiagnostico = Depends(obtener_caso_uso_consultar_diagnostico),
    usuario_id: str = Depends(requiere_rol("representante")),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403, detail="Este diagnóstico no pertenece a su empresa"
        )
    return _a_response(diagnostico)


@router.post(
    "/{diagnostico_id}/respuestas",
    response_model=DiagnosticoResponse,
    summary="Registrar la respuesta a una pregunta",
    description="RF-09/HU-10: se guarda de inmediato, sin acción explícita "
    "de 'guardar'. Si la pregunta ya tenía respuesta, la reemplaza.",
)
async def guardar_respuesta(
    diagnostico_id: str,
    datos: GuardarRespuestaRequest,
    caso_uso: GuardarRespuesta = Depends(obtener_caso_uso_guardar_respuesta),
    usuario_id: str = Depends(requiere_rol("representante")),
):
    try:
        diagnostico = await caso_uso.ejecutar(
            usuario_id,
            diagnostico_id,
            pregunta_codigo=datos.pregunta_codigo,
            opcion_codigo=datos.opcion_codigo,
            valor=datos.valor,
            texto=datos.texto,
        )
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403, detail="Este diagnóstico no pertenece a su empresa"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(diagnostico)


@router.post(
    "/{diagnostico_id}/completar",
    response_model=DiagnosticoResponse,
    summary="Completar el diagnóstico (cerrar la captura de respuestas)",
    description="RF-07 paso 5: pasa el diagnóstico de 'borrador' a "
    "'completado'; exige que todas las preguntas obligatorias aplicables "
    "ya tengan respuesta.",
)
async def completar_diagnostico(
    diagnostico_id: str,
    caso_uso: CompletarDiagnostico = Depends(obtener_caso_uso_completar_diagnostico),
    usuario_id: str = Depends(requiere_rol("representante")),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403, detail="Este diagnóstico no pertenece a su empresa"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(diagnostico)
