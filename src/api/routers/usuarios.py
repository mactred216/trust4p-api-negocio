from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from src.api.dependencias import (obtener_caso_uso_asignar_consultor,
                                  obtener_caso_uso_consultar_usuario,
                                  obtener_caso_uso_desactivar_usuario,
                                  obtener_caso_uso_editar_usuario,
                                  obtener_caso_uso_listar_usuarios,
                                  obtener_caso_uso_reactivar_usuario)
from src.api.middleware.autorizacion import requiere_rol
from src.aplicacion.casos_uso.asignar_consultor import (AsignarConsultor,
                                                        ConsultorInactivo,
                                                        ConsultorNoEncontrado,
                                                        EmpresaInactiva,
                                                        EmpresaNoEncontrada)
from src.aplicacion.casos_uso.gestionar_usuarios import (ConsultarUsuario,
                                                         DesactivarUsuario,
                                                         EditarUsuario,
                                                         ListarUsuarios,
                                                         ReactivarUsuario,
                                                         UsuarioNoEncontrado)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
from src.api.dependencias import obtener_repositorio_auditoria
from src.api.middleware.auditoria import registrar_accion

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


class AsignacionRequest(BaseModel):
    empresa_id: str

    @field_validator("empresa_id")
    @classmethod
    def empresa_id_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El id de la empresa es obligatorio")
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
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    if usuario_id == usuario_actual_id:
        raise HTTPException(
            status_code=400, detail="No puede desactivar su propia cuenta"
        )
    try:
        await caso_uso.ejecutar(usuario_id)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "usuarios",
        usuario_id,
        "actualizar",
        valores_nuevos={"activo": False},
    )


@router.post("/{usuario_id}/reactivar", status_code=204)
async def reactivar_usuario(
    usuario_id: str,
    caso_uso: ReactivarUsuario = Depends(obtener_caso_uso_reactivar_usuario),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        await caso_uso.ejecutar(usuario_id)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "usuarios",
        usuario_id,
        "actualizar",
        valores_nuevos={"activo": True},
    )


@router.post(
    "/{consultor_id}/asignaciones",
    status_code=204,
    summary="Asignar una empresa a un consultor",
    description="Exclusivo del administrador. El usuario objetivo debe tener rol consultor.",
)
async def asignar_empresa_a_consultor(
    consultor_id: str,
    datos: AsignacionRequest,
    caso_uso: AsignarConsultor = Depends(obtener_caso_uso_asignar_consultor),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    try:
        await caso_uso.asignar(consultor_id, datos.empresa_id)
    except ConsultorNoEncontrado:
        raise HTTPException(status_code=404, detail="Consultor no encontrado")
    except EmpresaNoEncontrada:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    except ConsultorInactivo:
        raise HTTPException(status_code=400, detail="El consultor está inactivo")
    except EmpresaInactiva:
        raise HTTPException(status_code=400, detail="La empresa está inactiva")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{consultor_id}/asignaciones/{empresa_id}",
    status_code=204,
    summary="Finalizar la asignación de un consultor a una empresa",
)
async def finalizar_asignacion(
    consultor_id: str,
    empresa_id: str,
    caso_uso: AsignarConsultor = Depends(obtener_caso_uso_asignar_consultor),
    usuario_actual_id: str = Depends(requiere_rol("administrador")),
):
    try:
        await caso_uso.finalizar(consultor_id, empresa_id)
    except ConsultorNoEncontrado:
        raise HTTPException(status_code=404, detail="Consultor no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
