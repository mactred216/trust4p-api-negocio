from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from src.api.dependencias import (obtener_caso_uso_consultar_usuario,
                                  obtener_caso_uso_desactivar_usuario,
                                  obtener_caso_uso_editar_usuario,
                                  obtener_caso_uso_listar_usuarios,
                                  obtener_caso_uso_reactivar_usuario)
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.gestionar_usuarios import (ConsultarUsuario,
                                                         DesactivarUsuario,
                                                         EditarUsuario,
                                                         ListarUsuarios,
                                                         ReactivarUsuario,
                                                         UsuarioNoEncontrado)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

ROLES_VALIDOS = {"administrador", "consultor", "representante"}


class UsuarioResponse(BaseModel):
    id: str
    correo: str
    nombres: str
    apellidos: str
    rol_codigo: str
    empresa_id: Optional[str]
    activo: bool


class EditarUsuarioRequest(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    rol_codigo: Optional[str] = None

    @field_validator("nombres", "apellidos")
    @classmethod
    def si_viene_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Si se envía este campo, no puede estar vacío")
        return v

    @field_validator("rol_codigo")
    @classmethod
    def rol_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ROLES_VALIDOS:
            raise ValueError(
                f"Rol inválido. Debe ser uno de: {', '.join(ROLES_VALIDOS)}"
            )
        return v


def _a_response(usuario) -> UsuarioResponse:
    return UsuarioResponse(
        id=usuario.id,
        correo=usuario.correo,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        rol_codigo=usuario.rol.codigo,
        empresa_id=usuario.empresa_id,
        activo=usuario.activo,
    )


@router.get("", response_model=list[UsuarioResponse])
async def listar_usuarios(
    empresa_id: Optional[str] = Query(default=None),
    caso_uso: ListarUsuarios = Depends(obtener_caso_uso_listar_usuarios),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    usuarios = await caso_uso.ejecutar(empresa_id=empresa_id)
    return [_a_response(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def consultar_usuario(
    usuario_id: str,
    caso_uso: ConsultarUsuario = Depends(obtener_caso_uso_consultar_usuario),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    try:
        usuario = await caso_uso.ejecutar(usuario_id)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_response(usuario)


@router.patch("/{usuario_id}", response_model=UsuarioResponse)
async def editar_usuario(
    usuario_id: str,
    datos: EditarUsuarioRequest,
    caso_uso: EditarUsuario = Depends(obtener_caso_uso_editar_usuario),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    campos = datos.model_dump(exclude_unset=True)
    try:
        usuario = await caso_uso.ejecutar(usuario_id, **campos)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_response(usuario)


@router.post("/{usuario_id}/desactivar", status_code=204)
async def desactivar_usuario(
    usuario_id: str,
    caso_uso: DesactivarUsuario = Depends(obtener_caso_uso_desactivar_usuario),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    if usuario_id == usuario_actual_id:
        raise HTTPException(
            status_code=400, detail="No puede desactivar su propia cuenta"
        )
    try:
        await caso_uso.ejecutar(usuario_id)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")


@router.post("/{usuario_id}/reactivar", status_code=204)
async def reactivar_usuario(
    usuario_id: str,
    caso_uso: ReactivarUsuario = Depends(obtener_caso_uso_reactivar_usuario),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    try:
        await caso_uso.ejecutar(usuario_id)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
