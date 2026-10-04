from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator, model_validator

from src.api.dependencias import (obtener_caso_uso_actualizar_perfil,
                                  obtener_caso_uso_cambiar_contrasena,
                                  obtener_caso_uso_cerrar_sesion,
                                  obtener_caso_uso_consultar_usuario,
                                  obtener_caso_uso_eliminar_datos_personales,
                                  obtener_repositorio_auditoria)
from src.api.middleware.auditoria import registrar_accion, registrar_cambio
from src.api.middleware.autorizacion import obtener_usuario_autenticado
from src.api.validadores_comunes import (clave_cumple_politica,
                                         telefono_valido,
                                         texto_opcional_no_vacio)
from src.aplicacion.casos_uso.gestionar_perfil import (ActualizarPerfil,
                                                       CambiarContrasena,
                                                       CerrarSesion,
                                                       ClaveActualIncorrecta,
                                                       ClaveReutilizada,
                                                       EliminarDatosPersonales,
                                                       UsuarioNoEncontrado)
from src.aplicacion.casos_uso.gestionar_usuarios import ConsultarUsuario
from src.aplicacion.casos_uso.gestionar_usuarios import \
    UsuarioNoEncontrado as UsuarioNoEncontradoConsulta

router = APIRouter(prefix="/mi-perfil", tags=["perfil"])


class PerfilResponse(BaseModel):
    id: str
    correo: str
    nombres: str
    apellidos: str
    cargo: Optional[str]
    telefono: Optional[str]
    rol_codigo: str
    empresa_id: Optional[str]


class ActualizarPerfilRequest(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None

    @field_validator("nombres", "apellidos", "cargo")
    @classmethod
    def _si_viene_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        return texto_opcional_no_vacio(v, maximo=200)

    @field_validator("telefono")
    @classmethod
    def _telefono_valido(cls, v: Optional[str]) -> Optional[str]:
        return telefono_valido(v)


class CambiarContrasenaRequest(BaseModel):
    clave_actual: str
    clave_nueva: str
    confirmar_clave: str

    @field_validator("clave_actual")
    @classmethod
    def _clave_actual_no_vacia(cls, v: str) -> str:
        if not v:
            raise ValueError("La contraseña actual es obligatoria")
        return v

    @field_validator("clave_nueva")
    @classmethod
    def _clave_cumple_politica(cls, v: str) -> str:
        return clave_cumple_politica(v)

    @model_validator(mode="after")
    def _confirmacion_coincide(self) -> "CambiarContrasenaRequest":
        if self.clave_nueva != self.confirmar_clave:
            raise ValueError("La confirmación no coincide con la nueva contraseña")
        return self


class EliminarDatosRequest(BaseModel):
    confirmar: bool

    @field_validator("confirmar")
    @classmethod
    def _debe_confirmar(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Debe confirmar explícitamente la eliminación de sus datos"
            )
        return v


def _resumen_auditoria(usuario) -> dict:
    return {
        "nombres": usuario.nombres,
        "apellidos": usuario.apellidos,
        "cargo": usuario.cargo,
        "telefono": usuario.telefono,
    }


def _a_response(usuario) -> PerfilResponse:
    return PerfilResponse(
        id=usuario.id,
        correo=usuario.correo,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        cargo=usuario.cargo,
        telefono=usuario.telefono,
        rol_codigo=usuario.rol.codigo,
        empresa_id=usuario.empresa_id,
    )


@router.get("", response_model=PerfilResponse)
async def consultar_mi_perfil(
    caso_uso: ConsultarUsuario = Depends(obtener_caso_uso_consultar_usuario),
    usuario_id: str = Depends(obtener_usuario_autenticado),
):
    try:
        usuario = await caso_uso.ejecutar(usuario_id)
    except UsuarioNoEncontradoConsulta:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _a_response(usuario)


@router.patch("", response_model=PerfilResponse)
async def actualizar_mi_perfil(
    datos: ActualizarPerfilRequest,
    caso_uso: ActualizarPerfil = Depends(obtener_caso_uso_actualizar_perfil),
    consulta: ConsultarUsuario = Depends(obtener_caso_uso_consultar_usuario),
    usuario_id: str = Depends(obtener_usuario_autenticado),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        antes = _resumen_auditoria(await consulta.ejecutar(usuario_id))
        usuario = await caso_uso.ejecutar(
            usuario_id,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            cargo=datos.cargo,
            telefono=datos.telefono,
        )
    except (UsuarioNoEncontrado, UsuarioNoEncontradoConsulta):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await registrar_cambio(
        repo_auditoria,
        usuario_id,
        "usuarios",
        usuario_id,
        antes,
        _resumen_auditoria(usuario),
    )
    return _a_response(usuario)


@router.post(
    "/cambiar-contrasena",
    status_code=204,
    summary="Cambiar la propia contraseña",
    description="Requiere la contraseña actual. No reutiliza ninguna de las "
    "últimas 5 contraseñas (RF-48) y revoca todas las sesiones activas.",
)
async def cambiar_mi_contrasena(
    datos: CambiarContrasenaRequest,
    caso_uso: CambiarContrasena = Depends(obtener_caso_uso_cambiar_contrasena),
    usuario_id: str = Depends(obtener_usuario_autenticado),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    try:
        await caso_uso.ejecutar(usuario_id, datos.clave_actual, datos.clave_nueva)
    except UsuarioNoEncontrado:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except ClaveActualIncorrecta:
        raise HTTPException(
            status_code=400, detail="La contraseña actual es incorrecta"
        )
    except ClaveReutilizada:
        raise HTTPException(
            status_code=400,
            detail="No puede reutilizar una de sus últimas 5 contraseñas",
        )

    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "usuarios",
        usuario_id,
        "actualizar",
        valores_nuevos={"clave": "cambiada"},
    )


@router.post(
    "/cerrar-sesion",
    status_code=204,
    summary="Cerrar la sesión activa",
)
async def cerrar_mi_sesion(
    request: Request,
    response: Response,
    caso_uso: CerrarSesion = Depends(obtener_caso_uso_cerrar_sesion),
    usuario_id: str = Depends(obtener_usuario_autenticado),
    repo_auditoria=Depends(obtener_repositorio_auditoria),
):
    token = request.cookies.get("sesion")
    if token is not None:
        await caso_uso.ejecutar(token)
    response.delete_cookie("sesion")
    await registrar_accion(
        repo_auditoria,
        usuario_id,
        "usuarios",
        usuario_id,
        "autenticar",
        valores_nuevos={"resultado": "cierre_sesion"},
    )


@router.post(
    "/eliminar",
    status_code=204,
    summary="Solicitar la eliminación de mis datos personales",
    description="RF-44. Desactiva la cuenta y elimina los datos identificables "
    "(nombre, correo, teléfono); conserva los resultados de diagnósticos de "
    "forma agregada y anonimizada. Revoca todas las sesiones activas.",
)
async def eliminar_mis_datos(
    datos: EliminarDatosRequest,
    caso_uso: EliminarDatosPersonales = Depends(
        obtener_caso_uso_eliminar_datos_personales
    ),
    usuario_id: str = Depends(obtener_usuario_autenticado),
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
        usuario_id,
        "usuarios",
        usuario_id,
        "eliminar",
        valores_nuevos={"datos_personales": "anonimizados"},
    )
