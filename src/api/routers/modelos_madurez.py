from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.api.dependencias import (obtener_caso_uso_agregar_dimension,
                                  obtener_caso_uso_consultar_modelo,
                                  obtener_caso_uso_crear_modelo_madurez,
                                  obtener_caso_uso_editar_dimension,
                                  obtener_caso_uso_listar_modelos,
                                  obtener_caso_uso_quitar_dimension)
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.gestionar_modelo_madurez import (
    AgregarDimension, ConsultarModelo, CrearModeloMadurez, EditarDimension,
    ListarModelos, ModeloNoEncontrado, QuitarDimension, VersionDuplicada)

router = APIRouter(prefix="/modelos-madurez", tags=["modelos-madurez"])


class DimensionResponse(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str]
    peso: Decimal
    orden: int


class ModeloMadurezResponse(BaseModel):
    id: str
    version: str
    nombre: str
    descripcion: Optional[str]
    escala_min: int
    escala_max: int
    publicado: bool
    dimensiones: list[DimensionResponse]


class CrearModeloRequest(BaseModel):
    version: str
    nombre: str
    descripcion: Optional[str] = None
    escala_min: int = 1
    escala_max: int = 10

    @field_validator("version", "nombre")
    @classmethod
    def texto_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo no puede estar vacío")
        return v


class DimensionRequest(BaseModel):
    codigo: str
    nombre: str
    peso: Decimal
    orden: int
    descripcion: Optional[str] = None

    @field_validator("codigo", "nombre")
    @classmethod
    def texto_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo no puede estar vacío")
        return v

    @field_validator("peso")
    @classmethod
    def peso_valido(cls, v: Decimal) -> Decimal:
        if v <= 0 or v > 1:
            raise ValueError("El peso debe ser mayor que 0 y menor o igual a 1")
        return v

    @field_validator("orden")
    @classmethod
    def orden_valido(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("El orden debe ser un entero positivo")
        return v


class EditarDimensionRequest(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    peso: Optional[Decimal] = None
    orden: Optional[int] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Si se envía este campo, no puede estar vacío")
        return v

    @field_validator("peso")
    @classmethod
    def peso_valido(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v <= 0 or v > 1:
            raise ValueError("El peso debe ser mayor que 0 y menor o igual a 1")
        return v

    @field_validator("orden")
    @classmethod
    def orden_valido(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v <= 0:
            raise ValueError("El orden debe ser un entero positivo")
        return v


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
    usuario_id: str = Depends(requiere_rol("administrador")),
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
    usuario_id: str = Depends(requiere_rol("administrador")),
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
    return _a_response(modelo)


@router.patch("/{modelo_id}/dimensiones/{codigo}", response_model=ModeloMadurezResponse)
async def editar_dimension(
    modelo_id: str,
    codigo: str,
    datos: EditarDimensionRequest,
    caso_uso: EditarDimension = Depends(obtener_caso_uso_editar_dimension),
    usuario_id: str = Depends(requiere_rol("administrador")),
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
    return _a_response(modelo)


@router.delete(
    "/{modelo_id}/dimensiones/{codigo}", response_model=ModeloMadurezResponse
)
async def quitar_dimension(
    modelo_id: str,
    codigo: str,
    caso_uso: QuitarDimension = Depends(obtener_caso_uso_quitar_dimension),
    usuario_id: str = Depends(requiere_rol("administrador")),
):
    try:
        modelo = await caso_uso.ejecutar(modelo_id, codigo)
    except ModeloNoEncontrado:
        raise HTTPException(status_code=404, detail="Modelo de madurez no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(modelo)
