from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, model_validator

from src.api.dependencias import (obtener_caso_uso_agregar_dimension,
                                  obtener_caso_uso_agregar_pregunta,
                                  obtener_caso_uso_consultar_modelo,
                                  obtener_caso_uso_crear_modelo_madurez,
                                  obtener_caso_uso_editar_dimension,
                                  obtener_caso_uso_editar_pregunta,
                                  obtener_caso_uso_listar_modelos,
                                  obtener_caso_uso_quitar_dimension,
                                  obtener_caso_uso_quitar_pregunta,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion
from src.api.middleware.autorizacion import requiere_rol
from src.api.validadores_comunes import (descripcion_opcional, entero_positivo,
                                         entero_positivo_opcional,
                                         peso_opcional_valido, peso_valido,
                                         texto_no_vacio,
                                         texto_opcional_no_vacio)
from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarDimension, AgregarPregunta, ConsultarModelo, CrearModeloMadurez,
    EditarDimension, EditarPregunta, ListarModelos, ModeloNoEncontrado,
    QuitarDimension, QuitarPregunta, VersionDuplicada)

TipoPregunta = Literal[
    "seleccion_unica", "seleccion_multiple", "escala", "numerica", "texto_libre"
]
OperadorCondicion = Literal["igual", "diferente", "mayor_que", "menor_que", "contiene"]

router = APIRouter(prefix="/modelos-madurez", tags=["modelos-madurez"])


class DimensionResponse(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str]
    peso: Decimal
    orden: int


class OpcionResponse(BaseModel):
    codigo: str
    etiqueta: str
    valor: Decimal


class CondicionResponse(BaseModel):
    pregunta_codigo: str
    operador: str
    valor: str


class PreguntaResponse(BaseModel):
    codigo: str
    dimension_codigo: str
    enunciado: str
    ayuda: Optional[str]
    tipo: str
    obligatoria: bool
    peso: Decimal
    en_demo: bool
    orden: int
    opciones: list[OpcionResponse]
    condicion: Optional[CondicionResponse]


class ModeloMadurezResponse(BaseModel):
    id: str
    version: str
    nombre: str
    descripcion: Optional[str]
    escala_min: int
    escala_max: int
    publicado: bool
    dimensiones: list[DimensionResponse]
    preguntas: list[PreguntaResponse]


class CrearModeloRequest(BaseModel):
    version: str
    nombre: str
    descripcion: Optional[str] = None
    escala_min: int = 1
    escala_max: int = 10

    @field_validator("version", "nombre")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=200)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_valida(cls, v: Optional[str]) -> Optional[str]:
        return descripcion_opcional(v)

    @model_validator(mode="after")
    def escala_coherente(self) -> "CrearModeloRequest":
        if self.escala_min < 1 or self.escala_max < 1:
            raise ValueError("La escala debe ser positiva")
        if self.escala_min >= self.escala_max:
            raise ValueError("escala_min debe ser menor que escala_max")
        return self


class DimensionRequest(BaseModel):
    codigo: str
    nombre: str
    peso: Decimal
    orden: int
    descripcion: Optional[str] = None

    @field_validator("codigo")
    @classmethod
    def _codigo_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=50)

    @field_validator("nombre")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=200)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_valida(cls, v: Optional[str]) -> Optional[str]:
        return descripcion_opcional(v)

    @field_validator("peso")
    @classmethod
    def _peso_valido(cls, v: Decimal) -> Decimal:
        return peso_valido(v)

    @field_validator("orden")
    @classmethod
    def _orden_valido(cls, v: int) -> int:
        return entero_positivo(v)


class EditarDimensionRequest(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    peso: Optional[Decimal] = None
    orden: Optional[int] = None

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=200)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_valida(cls, v: Optional[str]) -> Optional[str]:
        return descripcion_opcional(v)

    @field_validator("peso")
    @classmethod
    def _peso_valido(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return peso_opcional_valido(v)

    @field_validator("orden")
    @classmethod
    def _orden_valido(cls, v: Optional[int]) -> Optional[int]:
        return entero_positivo_opcional(v)


class OpcionRequest(BaseModel):
    codigo: str
    etiqueta: str
    valor: Decimal

    @field_validator("codigo", "etiqueta")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=200)


class CondicionRequest(BaseModel):
    pregunta_codigo: str
    operador: OperadorCondicion
    valor: str

    @field_validator("pregunta_codigo", "valor")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v)


class PreguntaRequest(BaseModel):
    codigo: str
    dimension_codigo: str
    enunciado: str
    tipo: TipoPregunta
    obligatoria: bool = True
    peso: Decimal
    en_demo: bool = False
    orden: int
    ayuda: Optional[str] = None
    opciones: list[OpcionRequest] = []
    condicion: Optional[CondicionRequest] = None

    @field_validator("codigo")
    @classmethod
    def _codigo_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=50)

    @field_validator("dimension_codigo")
    @classmethod
    def _dimension_codigo_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v)

    @field_validator("enunciado")
    @classmethod
    def _enunciado_valido(cls, v: str) -> str:
        return texto_no_vacio(v, maximo=1000)

    @field_validator("ayuda")
    @classmethod
    def _ayuda_valida(cls, v: Optional[str]) -> Optional[str]:
        return descripcion_opcional(v)

    @field_validator("peso")
    @classmethod
    def _peso_valido(cls, v: Decimal) -> Decimal:
        return peso_valido(v)

    @field_validator("orden")
    @classmethod
    def _orden_valido(cls, v: int) -> int:
        return entero_positivo(v)


class EditarPreguntaRequest(BaseModel):
    dimension_codigo: Optional[str] = None
    enunciado: Optional[str] = None
    ayuda: Optional[str] = None
    tipo: Optional[TipoPregunta] = None
    obligatoria: Optional[bool] = None
    peso: Optional[Decimal] = None
    en_demo: Optional[bool] = None
    orden: Optional[int] = None

    @field_validator("dimension_codigo", "enunciado")
    @classmethod
    def _texto_no_vacio_si_viene(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v)

    @field_validator("ayuda")
    @classmethod
    def _ayuda_valida(cls, v: Optional[str]) -> Optional[str]:
        return descripcion_opcional(v)

    @field_validator("peso")
    @classmethod
    def _peso_valido(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return peso_opcional_valido(v)

    @field_validator("orden")
    @classmethod
    def _orden_valido(cls, v: Optional[int]) -> Optional[int]:
        return entero_positivo_opcional(v)


def _a_response(modelo) -> ModeloMadurezResponse:
    return ModeloMadurezResponse(
        id=modelo.id,
        version=modelo.version,
        nombre=modelo.nombre,
        descripcion=modelo.descripcion,
        escala_min=modelo.escala_min,
        escala_max=modelo.escala_max,
        publicado=modelo.publicado,
        dimensiones=[
            DimensionResponse(
                codigo=d.codigo,
                nombre=d.nombre,
                descripcion=d.descripcion,
                peso=d.peso,
                orden=d.orden,
            )
            for d in modelo.dimensiones
        ],
        preguntas=[
            PreguntaResponse(
                codigo=p.codigo,
                dimension_codigo=p.dimension_codigo,
                enunciado=p.enunciado,
                ayuda=p.ayuda,
                tipo=p.tipo,
                obligatoria=p.obligatoria,
                peso=p.peso,
                en_demo=p.en_demo,
                orden=p.orden,
                opciones=[
                    OpcionResponse(codigo=o.codigo, etiqueta=o.etiqueta, valor=o.valor)
                    for o in p.opciones
                ],
                condicion=(
                    CondicionResponse(
                        pregunta_codigo=p.condicion.pregunta_codigo,
                        operador=p.condicion.operador,
                        valor=p.condicion.valor,
                    )
                    if p.condicion
                    else None
                ),
            )
            for p in modelo.preguntas
        ],
    )


@router.get("", response_model=list[ModeloMadurezResponse])
async def listar_modelos(
    caso_uso: ListarModelos = Depends(obtener_caso_uso_listar_modelos),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    modelos = await caso_uso.ejecutar()
    return [_a_response(m) for m in modelos]


@router.post("", response_model=ModeloMadurezResponse, status_code=201)
async def crear_modelo(
    datos: CrearModeloRequest,
    caso_uso: CrearModeloMadurez = Depends(obtener_caso_uso_crear_modelo_madurez),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(
            version=datos.version,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            escala_min=datos.escala_min,
            escala_max=datos.escala_max,
        )
    except VersionDuplicada:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una versión del modelo con este identificador",
        )

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo.id,
        "crear",
        valores_nuevos={"version": modelo.version, "nombre": modelo.nombre},
    )
    return _a_response(modelo)


@router.get("/{modelo_id}", response_model=ModeloMadurezResponse)
async def consultar_modelo(
    modelo_id: str,
    caso_uso: ConsultarModelo = Depends(obtener_caso_uso_consultar_modelo),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    try:
        modelo = await caso_uso.ejecutar(modelo_id)
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    return _a_response(modelo)


@router.post(
    "/{modelo_id}/dimensiones", response_model=ModeloMadurezResponse, status_code=201
)
async def agregar_dimension(
    modelo_id: str,
    datos: DimensionRequest,
    caso_uso: AgregarDimension = Depends(obtener_caso_uso_agregar_dimension),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(
            modelo_id,
            codigo=datos.codigo,
            nombre=datos.nombre,
            peso=datos.peso,
            orden=datos.orden,
            descripcion=datos.descripcion,
        )
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo_id,
        "actualizar",
        valores_nuevos={
            "dimension_agregada": datos.codigo,
            "peso": str(datos.peso),
        },
    )
    return _a_response(modelo)


@router.patch("/{modelo_id}/dimensiones/{codigo}", response_model=ModeloMadurezResponse)
async def editar_dimension(
    modelo_id: str,
    codigo: str,
    datos: EditarDimensionRequest,
    caso_uso: EditarDimension = Depends(obtener_caso_uso_editar_dimension),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(
            modelo_id,
            codigo,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            peso=datos.peso,
            orden=datos.orden,
        )
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo_id,
        "actualizar",
        valores_nuevos={"dimension_editada": codigo},
    )
    return _a_response(modelo)


@router.delete(
    "/{modelo_id}/dimensiones/{codigo}", response_model=ModeloMadurezResponse
)
async def quitar_dimension(
    modelo_id: str,
    codigo: str,
    caso_uso: QuitarDimension = Depends(obtener_caso_uso_quitar_dimension),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(modelo_id, codigo)
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo_id,
        "actualizar",
        valores_nuevos={"dimension_quitada": codigo},
    )
    return _a_response(modelo)


@router.post(
    "/{modelo_id}/preguntas", response_model=ModeloMadurezResponse, status_code=201
)
async def agregar_pregunta(
    modelo_id: str,
    datos: PreguntaRequest,
    caso_uso: AgregarPregunta = Depends(obtener_caso_uso_agregar_pregunta),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(
            modelo_id,
            codigo=datos.codigo,
            dimension_codigo=datos.dimension_codigo,
            enunciado=datos.enunciado,
            tipo=datos.tipo,
            obligatoria=datos.obligatoria,
            peso=datos.peso,
            en_demo=datos.en_demo,
            orden=datos.orden,
            ayuda=datos.ayuda,
            opciones=[o.model_dump() for o in datos.opciones],
            condicion=datos.condicion.model_dump() if datos.condicion else None,
        )
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo_id,
        "actualizar",
        valores_nuevos={
            "pregunta_agregada": datos.codigo,
            "dimension_codigo": datos.dimension_codigo,
            "peso": str(datos.peso),
        },
    )
    return _a_response(modelo)


@router.patch("/{modelo_id}/preguntas/{codigo}", response_model=ModeloMadurezResponse)
async def editar_pregunta(
    modelo_id: str,
    codigo: str,
    datos: EditarPreguntaRequest,
    caso_uso: EditarPregunta = Depends(obtener_caso_uso_editar_pregunta),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(
            modelo_id,
            codigo,
            dimension_codigo=datos.dimension_codigo,
            enunciado=datos.enunciado,
            ayuda=datos.ayuda,
            tipo=datos.tipo,
            obligatoria=datos.obligatoria,
            peso=datos.peso,
            en_demo=datos.en_demo,
            orden=datos.orden,
        )
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo_id,
        "actualizar",
        valores_nuevos={"pregunta_editada": codigo},
    )
    return _a_response(modelo)


@router.delete("/{modelo_id}/preguntas/{codigo}", response_model=ModeloMadurezResponse)
async def quitar_pregunta(
    modelo_id: str,
    codigo: str,
    caso_uso: QuitarPregunta = Depends(obtener_caso_uso_quitar_pregunta),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        modelo = await caso_uso.ejecutar(modelo_id, codigo)
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "modelos_madurez",
        modelo_id,
        "actualizar",
        valores_nuevos={"pregunta_quitada": codigo},
    )
    return _a_response(modelo)
