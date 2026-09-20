from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from src.api.dependencias import (obtener_caso_uso_agregar_permiso,
                                  obtener_caso_uso_listar_permisos,
                                  obtener_caso_uso_listar_roles,
                                  obtener_caso_uso_quitar_permiso)
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.gestionar_roles import (AgregarPermisoARol,
                                                      ListarPermisos,
                                                      ListarRoles,
                                                      PermisoNoExiste,
                                                      QuitarPermisoDeRol,
                                                      RolNoEncontrado)

router = APIRouter(prefix="/roles", tags=["roles"])


class RolResponse(BaseModel):
    id: str
    codigo: str
    nombre: str
    es_sistema: bool
    permisos: list[str]


class PermisoResponse(BaseModel):
    id: str
    codigo: str
    modulo: str
    descripcion: str


class PermisoRequest(BaseModel):
    codigo_permiso: str

    @field_validator("codigo_permiso")
    @classmethod
    def codigo_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El código del permiso es obligatorio")
        return v


@router.get("", response_model=list[RolResponse])
async def listar_roles(
    caso_uso: ListarRoles = Depends(obtener_caso_uso_listar_roles),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    roles = await caso_uso.ejecutar()
    return [
        RolResponse(
            id=r.id,
            codigo=r.codigo,
            nombre=r.nombre,
            es_sistema=r.es_sistema,
            permisos=r.permisos,
        )
        for r in roles
    ]


@router.get("/permisos", response_model=list[PermisoResponse])
async def listar_permisos(
    caso_uso: ListarPermisos = Depends(obtener_caso_uso_listar_permisos),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    permisos = await caso_uso.ejecutar()
    return [
        PermisoResponse(
            id=p.id, codigo=p.codigo, modulo=p.modulo, descripcion=p.descripcion
        )
        for p in permisos
    ]


@router.post("/{codigo_rol}/permisos", response_model=RolResponse)
async def agregar_permiso(
    codigo_rol: str,
    datos: PermisoRequest,
    caso_uso: AgregarPermisoARol = Depends(obtener_caso_uso_agregar_permiso),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    try:
        rol = await caso_uso.ejecutar(codigo_rol, datos.codigo_permiso)
    except RolNoEncontrado:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    except PermisoNoExiste:
        raise HTTPException(
            status_code=404, detail="Permiso no encontrado en el catálogo"
        )
    return RolResponse(
        id=rol.id,
        codigo=rol.codigo,
        nombre=rol.nombre,
        es_sistema=rol.es_sistema,
        permisos=rol.permisos,
    )


@router.delete("/{codigo_rol}/permisos/{codigo_permiso}", response_model=RolResponse)
async def quitar_permiso(
    codigo_rol: str,
    codigo_permiso: str,
    caso_uso: QuitarPermisoDeRol = Depends(obtener_caso_uso_quitar_permiso),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    try:
        rol = await caso_uso.ejecutar(codigo_rol, codigo_permiso)
    except RolNoEncontrado:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RolResponse(
        id=rol.id,
        codigo=rol.codigo,
        nombre=rol.nombre,
        es_sistema=rol.es_sistema,
        permisos=rol.permisos,
    )
