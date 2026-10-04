from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, field_validator

from src.api.dependencias import (obtener_caso_uso_asignar_consultor,
                                  obtener_caso_uso_consultar_usuario,
                                  obtener_caso_uso_crear_usuario,
                                  obtener_caso_uso_desactivar_usuario,
                                  obtener_caso_uso_desbloquear_usuario,
                                  obtener_caso_uso_editar_usuario,
                                  obtener_caso_uso_listar_usuarios,
                                  obtener_caso_uso_reactivar_usuario)
from src.api.middleware.autorizacion import requiere_rol
from src.api.validadores_comunes import texto_no_vacio, texto_opcional_no_vacio
from src.aplicacion.casos_uso.asignar_consultor import (AsignarConsultor,
                                                        ConsultorInactivo,
                                                        ConsultorNoEncontrado,
                                                        EmpresaInactiva,
                                                        EmpresaNoEncontrada)
from src.aplicacion.casos_uso.gestionar_usuarios import (ConsultarUsuario,
                                                         CorreoYaRegistrado,
                                                         CrearUsuario,
                                                         DesactivarUsuario,
                                                         DesbloquearUsuario,
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
    registro_pendiente: bool = False


class CrearUsuarioRequest(BaseModel):
    correo: EmailStr
    nombres: str
    apellidos: str
    rol_codigo: str
    empresa_id: Optional[str] = None

    @field_validator("nombres", "apellidos")
    @classmethod
    def _nombre_valido(cls, v: str) -> str:
        return texto_no_vacio(v, minimo=2, maximo=200)

    @field_validator("rol_codigo")
    @classmethod
    def _rol_valido(cls, v: str) -> str:
        if v not in ROLES_VALIDOS:
            raise ValueError(
                f"Rol inválido. Debe ser uno de: {', '.join(sorted(ROLES_VALIDOS))}"
            )
        return v

    @field_validator("empresa_id")
    @classmethod
    def _empresa_valida(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=50)


class EditarUsuarioRequest(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    rol_codigo: Optional[str] = None
    empresa_id: Optional[str] = None

    @field_validator("empresa_id")
    @classmethod
    def _empresa_si_viene(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=50)

    @field_validator("nombres", "apellidos")
    @classmethod
    def si_viene_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v)

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
        return texto_no_vacio(v)


def _a_response(usuario) -> UsuarioResponse:
    return UsuarioResponse(
        id=usuario.id,
        correo=usuario.correo,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        rol_codigo=usuario.rol.codigo,
        empresa_id=usuario.empresa_id,
        activo=usuario.activo,
        registro_pendiente=usuario.registro_pendiente,
    )


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=201,
    summary="Crear un usuario",
    description="RF-25/HU-026: el administrador crea un usuario con rol y, si es "
    "representante, empresa. Se valida que el correo no esté registrado y se "
    "envía una invitación para que la persona defina su contraseña.",
)
async def crear_usuario(
    datos: CrearUsuarioRequest,
    caso_uso: CrearUsuario = Depends(obtener_caso_uso_crear_usuario),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        usuario = await caso_uso.ejecutar(
            correo=datos.correo,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            rol_codigo=datos.rol_codigo,
            empresa_id=datos.empresa_id,
        )
    except CorreoYaRegistrado:
        raise HTTPException(
            status_code=409, detail="Ya existe un usuario con ese correo"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await registrar_accion(
        repo_auditoria,
        usuario_actual_id,
        "usuarios",
        usuario.id,
        "crear",
        valores_nuevos={
            "correo": usuario.correo,
            "rol": usuario.rol.codigo,
            "empresa_id": usuario.empresa_id,
        },
    )
    return _a_response(usuario)


@router.get("", response_model=list[UsuarioResponse])
async def listar_usuarios(
    empresa_id: Optional[str] = Query(default=None),
    caso_uso: ListarUsuarios = Depends(obtener_caso_uso_listar_usuarios),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
):
    usuarios = await caso_uso.ejecutar(empresa_id=empresa_id)
    return [_a_response(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def consultar_usuario(
    usuario_id: str,
    caso_uso: ConsultarUsuario = Depends(obtener_caso_uso_consultar_usuario),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
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
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
):
    campos = datos.model_dump(exclude_unset=True)
    try:
        usuario = await caso_uso.ejecutar(usuario_id, **campos)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _a_response(usuario)


@router.post("/{usuario_id}/desactivar", status_code=204)
async def desactivar_usuario(
    usuario_id: str,
    caso_uso: DesactivarUsuario = Depends(obtener_caso_uso_desactivar_usuario),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
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
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
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
    "/{usuario_id}/desbloquear",
    status_code=204,
    summary="Desbloquear manualmente una cuenta bloqueada",
    description="Exclusivo del administrador. Reinicia el contador de intentos "
    "fallidos y levanta el bloqueo temporal (RF-04).",
)
async def desbloquear_usuario(
    usuario_id: str,
    caso_uso: DesbloquearUsuario = Depends(obtener_caso_uso_desbloquear_usuario),
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
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
        valores_nuevos={"bloqueado_hasta": None},
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
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
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
    usuario_actual_id: str = Depends(
        requiere_rol("administrador", "usuarios.gestionar")
    ),
):
    try:
        await caso_uso.finalizar(consultor_id, empresa_id)
    except ConsultorNoEncontrado:
        raise HTTPException(status_code=404, detail="Consultor no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
