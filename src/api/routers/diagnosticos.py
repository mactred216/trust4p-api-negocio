from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import (APIRouter, BackgroundTasks, Depends, HTTPException,
                     Response)
from pydantic import BaseModel, field_validator, model_validator

from src.api.dependencias import (obtener_caso_uso_cerrar_diagnostico,
                                  obtener_caso_uso_completar_diagnostico,
                                  obtener_caso_uso_consultar_diagnostico,
                                  obtener_caso_uso_consultar_evolucion,
                                  obtener_caso_uso_diagnostico_en_curso,
                                  obtener_caso_uso_evaluar_diagnostico,
                                  obtener_caso_uso_generar_informe,
                                  obtener_caso_uso_guardar_respuesta,
                                  obtener_caso_uso_iniciar_diagnostico,
                                  obtener_caso_uso_listar_diagnosticos_empresa,
                                  obtener_caso_uso_obtener_cuestionario,
                                  obtener_caso_uso_reprocesar_diagnostico,
                                  obtener_caso_uso_reprocesar_pendientes,
                                  obtener_repositorio_auditoria,
                                  obtener_repositorio_modelo_madurez)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_algun_rol, requiere_rol
from src.api.validadores_comunes import texto_no_vacio
from src.aplicacion.casos_uso.consultar_evolucion import \
    ConsultarEvolucionDiagnosticos
from src.aplicacion.casos_uso.evaluar_diagnostico import EvaluarDiagnostico
from src.aplicacion.casos_uso.generar_informe import (
    DiagnosticoSinResultado, GenerarInformeDiagnostico, nombres_de_dimensiones)
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, CerrarDiagnostico, CompletarDiagnostico,
    ConsultarDiagnostico, DiagnosticoEnCursoExistente, DiagnosticoNoEncontrado,
    GuardarRespuesta, IniciarDiagnostico, ListarDiagnosticosDeEmpresa,
    NoHayVersionVigente, ObtenerCuestionario, ObtenerDiagnosticoEnCurso,
    PreguntasPendientes)
from src.aplicacion.casos_uso.reprocesar_diagnostico import (
    ReprocesarDiagnostico, ReprocesarPendientes)
from src.dominio.entidades.diagnostico import NIVELES_PARA_NUEVO_DIAGNOSTICO
from src.infraestructura.informes.generador_informe_pdf import \
    generar_informe_pdf

router = APIRouter(prefix="/diagnosticos", tags=["diagnosticos"])


class RespuestaResponse(BaseModel):
    pregunta_codigo: str
    dimension_codigo: str
    opciones_codigo: list[str]
    valor: Optional[Decimal]
    texto: Optional[str]
    respondida_en: datetime


class DimensionResultadoResponse(BaseModel):
    codigo: str
    puntaje: Decimal
    observacion: Optional[str]


class PerfilCulturaResponse(BaseModel):
    codigo: str
    descripcion: Optional[str]
    nombre: Optional[str] = None


class ResultadoDiagnosticoResponse(BaseModel):
    """RF-12 a RF-16 (HU-013 a HU-017), ASR-02: resultado determinístico del
    motor de cálculo (índice, nivel, puntaje por dimensión, código de
    perfil cultural) junto con el contenido narrativo que redacta
    trust4p-servicio-agente a partir de ese resultado. Los campos
    narrativos (observacion, descripcion, lienzo_negocio, sintesis) son
    null si el agente todavía no respondió o agotó sus reintentos — el
    resultado numérico sigue disponible de todas formas."""

    indice_global: Decimal
    nivel: int
    nivel_descripcion: str
    dimensiones: list[DimensionResultadoResponse]
    perfil_cultura: PerfilCulturaResponse
    lienzo_negocio: Optional[dict[str, str]]
    sintesis: Optional[str]
    generado_en: datetime


class RecomendacionResponse(BaseModel):
    """Una recomendación es una tarea del plan de mejora: tiene estado, fecha
    límite y el nivel de madurez que ayuda a alcanzar."""

    id: str
    origen: str
    dimension_codigo: Optional[str]
    titulo: str
    contenido: str
    prioridad: Optional[int]
    visible: bool
    autor_id: Optional[str]
    autor_nombre: Optional[str] = None
    creado_en: datetime
    estado: str = "pendiente"
    fecha_limite: Optional[date] = None
    nivel_objetivo: Optional[int] = None
    actualizado_en: Optional[datetime] = None
    completada_en: Optional[datetime] = None


class AvanceNivelResponse(BaseModel):
    nivel: int
    alcanzado_en: datetime
    consultor_nombre: Optional[str] = None


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
    resultado: Optional[ResultadoDiagnosticoResponse]
    recomendaciones: list[RecomendacionResponse]
    motivo_fallo: Optional[str]
    iniciado_en: datetime
    completado_en: Optional[datetime]
    evaluado_en: Optional[datetime]
    cerrado_en: Optional[datetime]
    # Plan de mejora: nivel confirmado por el consultor y avances registrados.
    nivel_alcanzado: Optional[int] = None
    avances_de_nivel: list[AvanceNivelResponse] = []
    nuevo_diagnostico_recomendado: bool = False
    niveles_para_nuevo_diagnostico: int = NIVELES_PARA_NUEVO_DIAGNOSTICO


class GuardarRespuestaRequest(BaseModel):
    pregunta_codigo: str
    opciones_codigo: list[str] = []
    valor: Optional[Decimal] = None
    texto: Optional[str] = None

    @field_validator("pregunta_codigo")
    @classmethod
    def _pregunta_codigo_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=50)

    @model_validator(mode="after")
    def _al_menos_un_contenido(self) -> "GuardarRespuestaRequest":
        if not self.opciones_codigo and self.valor is None and self.texto is None:
            raise ValueError(
                "Debe enviar opciones_codigo, valor o texto según el tipo de pregunta"
            )
        return self


class OpcionPreguntaResponse(BaseModel):
    codigo: str
    etiqueta: str
    valor: Decimal


class CondicionActivacionResponse(BaseModel):
    pregunta_codigo: str
    operador: str
    valor: str


class PreguntaCuestionarioResponse(BaseModel):
    codigo: str
    dimension_codigo: str
    enunciado: str
    tipo: str
    obligatoria: bool
    orden: int
    ayuda: Optional[str]
    opciones: list[OpcionPreguntaResponse]
    condicion: Optional[CondicionActivacionResponse]


class DimensionCuestionarioResponse(BaseModel):
    codigo: str
    nombre: str
    orden: int
    descripcion: Optional[str]


class NivelCuestionarioResponse(BaseModel):
    numero: int
    nombre: str
    descripcion: str
    umbral_min: Decimal
    umbral_max: Decimal


class CuestionarioResponse(BaseModel):
    modelo_version: str
    escala_min: int
    escala_max: int
    niveles: list[NivelCuestionarioResponse]
    dimensiones: list[DimensionCuestionarioResponse]
    preguntas: list[PreguntaCuestionarioResponse]


class PuntoEvolucionResponse(BaseModel):
    diagnostico_id: str
    consecutivo: int
    modelo_version: str
    generado_en: datetime
    indice_global: Decimal
    nivel: int
    dimensiones: dict[str, Decimal]


class VariacionDimensionResponse(BaseModel):
    codigo: str
    puntaje_anterior: Decimal
    puntaje_actual: Decimal
    variacion: Decimal


class ComparacionEvolucionResponse(BaseModel):
    diagnostico_anterior_id: str
    diagnostico_actual_id: str
    indice_global_anterior: Decimal
    indice_global_actual: Decimal
    variacion_indice_global: Decimal
    variaciones_por_dimension: list[VariacionDimensionResponse]
    versiones_equivalentes: bool
    advertencia: Optional[str]


class EvolucionResponse(BaseModel):
    historial: list[PuntoEvolucionResponse]
    comparacion: Optional[ComparacionEvolucionResponse]


def _evolucion_a_response(evolucion) -> EvolucionResponse:
    return EvolucionResponse(
        historial=[
            PuntoEvolucionResponse(
                diagnostico_id=p.diagnostico_id,
                consecutivo=p.consecutivo,
                modelo_version=p.modelo_version,
                generado_en=p.generado_en,
                indice_global=p.indice_global,
                nivel=p.nivel,
                dimensiones=p.dimensiones,
            )
            for p in evolucion.historial
        ],
        comparacion=(
            ComparacionEvolucionResponse(
                diagnostico_anterior_id=evolucion.comparacion.diagnostico_anterior_id,
                diagnostico_actual_id=evolucion.comparacion.diagnostico_actual_id,
                indice_global_anterior=evolucion.comparacion.indice_global_anterior,
                indice_global_actual=evolucion.comparacion.indice_global_actual,
                variacion_indice_global=evolucion.comparacion.variacion_indice_global,
                variaciones_por_dimension=[
                    VariacionDimensionResponse(
                        codigo=v.codigo,
                        puntaje_anterior=v.puntaje_anterior,
                        puntaje_actual=v.puntaje_actual,
                        variacion=v.variacion,
                    )
                    for v in evolucion.comparacion.variaciones_por_dimension
                ],
                versiones_equivalentes=evolucion.comparacion.versiones_equivalentes,
                advertencia=evolucion.comparacion.advertencia,
            )
            if evolucion.comparacion is not None
            else None
        ),
    )


def _cuestionario_a_response(modelo) -> CuestionarioResponse:
    return CuestionarioResponse(
        modelo_version=modelo.version,
        escala_min=modelo.escala_min,
        escala_max=modelo.escala_max,
        niveles=[
            NivelCuestionarioResponse(
                numero=n.nivel,
                nombre=n.nombre,
                descripcion=n.descripcion,
                umbral_min=n.umbral_min,
                umbral_max=n.umbral_max,
            )
            for n in sorted(modelo.niveles, key=lambda n: n.nivel)
        ],
        dimensiones=[
            DimensionCuestionarioResponse(
                codigo=d.codigo,
                nombre=d.nombre,
                orden=d.orden,
                descripcion=d.descripcion,
            )
            for d in modelo.dimensiones
        ],
        preguntas=[
            PreguntaCuestionarioResponse(
                codigo=p.codigo,
                dimension_codigo=p.dimension_codigo,
                enunciado=p.enunciado,
                tipo=p.tipo,
                obligatoria=p.obligatoria,
                orden=p.orden,
                ayuda=p.ayuda,
                opciones=[
                    OpcionPreguntaResponse(
                        codigo=o.codigo, etiqueta=o.etiqueta, valor=o.valor
                    )
                    for o in p.opciones
                ],
                condicion=(
                    CondicionActivacionResponse(
                        pregunta_codigo=p.condicion.pregunta_codigo,
                        operador=p.condicion.operador,
                        valor=p.condicion.valor,
                    )
                    if p.condicion
                    else None
                ),
            )
            for p in modelo.preguntas
            if p.activo
        ],
    )


def _a_response(diagnostico, incluir_ocultas: bool = False) -> DiagnosticoResponse:
    """RF-16/RF-21: el representante solo ve las recomendaciones marcadas
    visibles; el consultor (incluir_ocultas=True) ve también las que aún no
    ha compartido con la empresa."""
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
                opciones_codigo=r.opciones_codigo,
                valor=r.valor,
                texto=r.texto,
                respondida_en=r.respondida_en,
            )
            for r in diagnostico.respuestas
        ],
        resultado=_resultado_a_response(diagnostico.resultado),
        recomendaciones=[
            _recomendacion_a_response(r, diagnostico)
            for r in diagnostico.recomendaciones
            if incluir_ocultas or r.visible
        ],
        motivo_fallo=diagnostico.motivo_fallo,
        iniciado_en=diagnostico.iniciado_en,
        completado_en=diagnostico.completado_en,
        evaluado_en=diagnostico.evaluado_en,
        cerrado_en=diagnostico.cerrado_en,
        nivel_alcanzado=diagnostico.nivel_actual(),
        avances_de_nivel=[
            AvanceNivelResponse(
                nivel=a.nivel,
                alcanzado_en=a.alcanzado_en,
                consultor_nombre=a.consultor_nombre,
            )
            for a in diagnostico.avances_de_nivel
        ],
        nuevo_diagnostico_recomendado=diagnostico.nuevo_diagnostico_recomendado(),
    )


def _recomendacion_a_response(recomendacion, diagnostico=None) -> RecomendacionResponse:
    """`diagnostico` permite resolver el nivel objetivo de las tareas que no lo
    guardaron (las anteriores al plan de mejora)."""
    return RecomendacionResponse(
        id=recomendacion.id,
        origen=recomendacion.origen,
        dimension_codigo=recomendacion.dimension_codigo,
        titulo=recomendacion.titulo,
        contenido=recomendacion.contenido,
        prioridad=recomendacion.prioridad,
        visible=recomendacion.visible,
        autor_id=recomendacion.autor_id,
        autor_nombre=recomendacion.autor_nombre,
        creado_en=recomendacion.creado_en,
        estado=recomendacion.estado,
        fecha_limite=recomendacion.fecha_limite,
        nivel_objetivo=(
            diagnostico.nivel_objetivo_de(recomendacion)
            if diagnostico is not None
            else recomendacion.nivel_objetivo
        ),
        actualizado_en=recomendacion.actualizado_en,
        completada_en=recomendacion.completada_en,
    )


def _resultado_a_response(resultado) -> Optional[ResultadoDiagnosticoResponse]:
    if resultado is None:
        return None
    return ResultadoDiagnosticoResponse(
        indice_global=resultado.indice_global,
        nivel=resultado.nivel,
        nivel_descripcion=resultado.nivel_descripcion,
        dimensiones=[
            DimensionResultadoResponse(
                codigo=d.codigo, puntaje=d.puntaje, observacion=d.observacion
            )
            for d in resultado.dimensiones
        ],
        perfil_cultura=PerfilCulturaResponse(
            codigo=resultado.perfil_cultura.codigo,
            descripcion=resultado.perfil_cultura.descripcion,
            nombre=resultado.perfil_cultura.nombre,
        ),
        lienzo_negocio=resultado.lienzo_negocio,
        sintesis=resultado.sintesis,
        generado_en=resultado.generado_en,
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
    usuario_id: str = Depends(requiere_rol("representante", "diagnosticos.responder")),
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
    usuario_id: str = Depends(requiere_rol("representante", "resultados.consultar")),
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
    usuario_id: str = Depends(requiere_rol("representante", "resultados.consultar")),
):
    try:
        diagnosticos = await caso_uso.ejecutar(usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [_a_response(d) for d in diagnosticos]


@router.get(
    "/evolucion",
    response_model=EvolucionResponse,
    summary="Evolución del nivel de madurez en el tiempo",
    description="RF-18/HU-019: compara el índice global y el puntaje por "
    "dimensión entre los diagnósticos de mi empresa que ya tienen un "
    "resultado calculado. Advierte si los dos últimos comparados usan "
    "versiones distintas del modelo de madurez.",
)
async def obtener_evolucion(
    caso_uso: ConsultarEvolucionDiagnosticos = Depends(
        obtener_caso_uso_consultar_evolucion
    ),
    usuario_id: str = Depends(requiere_rol("representante", "resultados.consultar")),
):
    try:
        evolucion = await caso_uso.ejecutar(usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _evolucion_a_response(evolucion)


@router.get("/{diagnostico_id}", response_model=DiagnosticoResponse)
async def consultar_diagnostico(
    diagnostico_id: str,
    caso_uso: ConsultarDiagnostico = Depends(obtener_caso_uso_consultar_diagnostico),
    usuario_id: str = Depends(requiere_rol("representante", "resultados.consultar")),
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


@router.get(
    "/{diagnostico_id}/cuestionario",
    response_model=CuestionarioResponse,
    summary="Obtener el cuestionario del diagnóstico",
    description="RF-07/HU-08: dimensiones y preguntas activas de la versión "
    "del modelo fijada al diagnóstico, para que el representante lo responda.",
)
async def obtener_cuestionario(
    diagnostico_id: str,
    caso_uso: ObtenerCuestionario = Depends(obtener_caso_uso_obtener_cuestionario),
    usuario_id: str = Depends(requiere_rol("representante", "resultados.consultar")),
):
    try:
        modelo = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403, detail="Este diagnóstico no pertenece a su empresa"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _cuestionario_a_response(modelo)


@router.get(
    "/{diagnostico_id}/informe",
    summary="Descargar el informe del diagnóstico",
    description="RF-17/HU-018: PDF con el nivel de madurez, el desglose por "
    "dimensión, el perfil de cultura, el lienzo de modelo de negocio y las "
    "recomendaciones. Exige que el diagnóstico ya tenga un resultado "
    "evaluado.",
)
async def descargar_informe(
    diagnostico_id: str,
    caso_uso: GenerarInformeDiagnostico = Depends(obtener_caso_uso_generar_informe),
    usuario_id: str = Depends(requiere_rol("representante", "resultados.consultar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
    repo_modelo=Depends(obtener_repositorio_modelo_madurez),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403, detail="Este diagnóstico no pertenece a su empresa"
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
        valores_nuevos={"accion": "descargar_informe"},
    )

    nombre_archivo = f"informe-diagnostico-{diagnostico.consecutivo}.pdf"
    return Response(
        content=contenido_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


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
    usuario_id: str = Depends(requiere_rol("representante", "diagnosticos.responder")),
):
    try:
        diagnostico = await caso_uso.ejecutar(
            usuario_id,
            diagnostico_id,
            pregunta_codigo=datos.pregunta_codigo,
            opciones_codigo=datos.opciones_codigo,
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
    "ya tengan respuesta. RF-36/ASR-02 (HU-038): dispara la evaluación del "
    "agente en segundo plano, sin bloquear la respuesta.",
)
async def completar_diagnostico(
    diagnostico_id: str,
    background_tasks: BackgroundTasks,
    caso_uso: CompletarDiagnostico = Depends(obtener_caso_uso_completar_diagnostico),
    caso_uso_evaluar: EvaluarDiagnostico = Depends(
        obtener_caso_uso_evaluar_diagnostico
    ),
    usuario_id: str = Depends(requiere_rol("representante", "diagnosticos.responder")),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403, detail="Este diagnóstico no pertenece a su empresa"
        )
    except PreguntasPendientes as e:
        raise HTTPException(
            status_code=400,
            detail={"mensaje": str(e), "preguntas_pendientes": e.codigos},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    background_tasks.add_task(caso_uso_evaluar.ejecutar, diagnostico.id)
    return _a_response(diagnostico)


@router.post(
    "/{diagnostico_id}/cerrar",
    response_model=DiagnosticoResponse,
    summary="Cerrar el diagnóstico",
    description="RF-23/HU-024: exclusivo del consultor con la empresa "
    "asignada vigente. Pasa el diagnóstico de 'evaluado' o 'fallido' a "
    "'cerrado'; a partir de ahí no admite nuevas recomendaciones.",
)
async def cerrar_diagnostico(
    diagnostico_id: str,
    caso_uso: CerrarDiagnostico = Depends(obtener_caso_uso_cerrar_diagnostico),
    usuario_id: str = Depends(requiere_rol("consultor", "diagnosticos.cerrar")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403,
            detail="No tiene una asignación vigente con la empresa de este diagnóstico",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "diagnosticos",
        diagnostico_id,
        "actualizar",
        valores_nuevos={"estado": "cerrado"},
    )
    return _a_response(diagnostico)


@router.post(
    "/{diagnostico_id}/reprocesar",
    response_model=DiagnosticoResponse,
    summary="Reprocesar la evaluación de un diagnóstico fallido",
    description="RF-40/ASR-02: vuelve a evaluar un diagnóstico que quedó "
    "'fallido' (el servicio de evaluación asistida no respondió). El "
    "administrador puede hacerlo con cualquier empresa; el consultor, con las "
    "que tiene asignadas. El índice se recalcula y la interpretación se genera "
    "en segundo plano; las recomendaciones que el consultor ya hubiera "
    "registrado se conservan.",
)
async def reprocesar_diagnostico(
    diagnostico_id: str,
    background_tasks: BackgroundTasks,
    caso_uso: ReprocesarDiagnostico = Depends(obtener_caso_uso_reprocesar_diagnostico),
    caso_uso_evaluar: EvaluarDiagnostico = Depends(
        obtener_caso_uso_evaluar_diagnostico
    ),
    usuario_id: str = Depends(
        requiere_algun_rol(
            {
                "consultor": "diagnosticos.reprocesar",
                "administrador": "diagnosticos.reprocesar",
            }
        )
    ),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        diagnostico = await caso_uso.ejecutar(usuario_id, diagnostico_id)
    except DiagnosticoNoEncontrado:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    except AccesoNoAutorizado:
        raise HTTPException(
            status_code=403,
            detail="No tiene una asignación vigente con la empresa de este diagnóstico",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "diagnosticos",
        diagnostico_id,
        "actualizar",
        valores_anteriores={"estado": "fallido"},
        valores_nuevos={"estado": "completado", "motivo": "reproceso de la evaluación"},
    )
    background_tasks.add_task(caso_uso_evaluar.ejecutar, diagnostico.id)
    return _a_response(diagnostico)


class ReprocesoPendientesResponse(BaseModel):
    en_cola: int
    diagnosticos: list[str]


@router.post(
    "/reprocesar-pendientes",
    response_model=ReprocesoPendientesResponse,
    summary="Reprocesar todos los diagnósticos fallidos",
    description="RF-40/ASR-02: reanudación diferida, exclusiva del "
    "administrador. Vuelve a evaluar, uno tras otro y en segundo plano, todos "
    "los diagnósticos 'fallido'. No notifica cada fallo; si el servicio de "
    "evaluación sigue caído, el cortocircuito los deja otra vez 'fallido' al "
    "instante y pueden reprocesarse más tarde.",
)
async def reprocesar_pendientes(
    background_tasks: BackgroundTasks,
    caso_uso: ReprocesarPendientes = Depends(obtener_caso_uso_reprocesar_pendientes),
    caso_uso_evaluar: EvaluarDiagnostico = Depends(
        obtener_caso_uso_evaluar_diagnostico
    ),
    usuario_id: str = Depends(
        requiere_rol("administrador", "diagnosticos.reprocesar")
    ),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    ids = await caso_uso.ejecutar()
    if ids:
        await registrar_accion(
            repo_auditoria,
            usuario_id,
            "diagnosticos",
            None,
            "actualizar",
            valores_nuevos={"reproceso_de": ids},
        )
        background_tasks.add_task(caso_uso_evaluar.ejecutar_en_serie, ids)
    return ReprocesoPendientesResponse(en_cola=len(ids), diagnosticos=ids)
