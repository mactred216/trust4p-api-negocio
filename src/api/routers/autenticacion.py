from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, field_validator

from src.api.dependencias import (obtener_caso_uso_completar_registro,
                                  obtener_caso_uso_iniciar_sesion)
from src.api.middleware.limites import (limite_envio_correo, limite_login,
                                        limite_token)
from src.api.validadores_comunes import clave_cumple_politica, texto_no_vacio
from src.aplicacion.casos_uso.completar_registro import (AutorizacionRequerida,
                                                         CompletarRegistro,
                                                         TokenInvalido)
from src.aplicacion.casos_uso.iniciar_sesion import (CredencialesInvalidas,
                                                     CuentaBloqueada,
                                                     CuentaInactiva,
                                                     IniciarSesion)

router = APIRouter(prefix="/auth", tags=["autenticacion"])

from src.api.dependencias import (obtener_caso_uso_restablecer_contrasena,
                                  obtener_caso_uso_solicitar_restablecimiento)
from src.aplicacion.casos_uso.recuperar_contrasena import (
    ClaveReutilizada, RestablecerContrasena, SolicitarRestablecimiento)
from src.aplicacion.casos_uso.recuperar_contrasena import \
    TokenInvalido as TokenRestablecimientoInvalido


class LoginRequest(BaseModel):
    correo: EmailStr
    clave: str

    @field_validator("clave")
    @classmethod
    def clave_no_vacia(cls, v: str) -> str:
        if not v:
            raise ValueError("La contraseña es obligatoria")
        return v


class LoginResponse(BaseModel):
    mensaje: str


class CompletarRegistroRequest(BaseModel):
    codigo_token: str
    clave: str
    nombres: str
    apellidos: str
    acepto_tratamiento: bool

    @field_validator("codigo_token")
    @classmethod
    def codigo_token_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v)

    @field_validator("clave")
    @classmethod
    def _clave_cumple_politica(cls, v: str) -> str:
        return clave_cumple_politica(v)

    @field_validator("nombres", "apellidos")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v, minimo=2)


class UsuarioResponse(BaseModel):
    id: str
    correo: str
    nombres: str
    apellidos: str


class SolicitarRestablecimientoRequest(BaseModel):
    correo: EmailStr


class RestablecerContrasenaRequest(BaseModel):
    codigo_token: str
    clave_nueva: str

    @field_validator("codigo_token")
    @classmethod
    def codigo_no_vacio(cls, v: str) -> str:
        return texto_no_vacio(v)

    @field_validator("clave_nueva")
    @classmethod
    def _clave_cumple_politica(cls, v: str) -> str:
        return clave_cumple_politica(v)


class MensajeResponse(BaseModel):
    mensaje: str


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(limite_login)],
    summary="Iniciar sesión",
    description="Autentica al usuario y establece la sesión mediante cookie HttpOnly.",
)
async def login(
    datos: LoginRequest,
    response: Response,
    caso_uso: IniciarSesion = Depends(obtener_caso_uso_iniciar_sesion),
):
    try:
        token = await caso_uso.ejecutar(datos.correo, datos.clave)
    except CredencialesInvalidas:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    except CuentaBloqueada:
        raise HTTPException(status_code=423, detail="Cuenta bloqueada temporalmente")
    except CuentaInactiva:
        raise HTTPException(
            status_code=403,
            detail="La empresa asociada a su cuenta está inactiva",
        )

    response.set_cookie(
        key="sesion",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800,  # RF-49: 30 minutos, coincide con DURACION_SESION_MINUTOS
    )
    return LoginResponse(mensaje="Sesión iniciada correctamente")


@router.post(
    "/completar-registro",
    response_model=UsuarioResponse,
    dependencies=[Depends(limite_token)],
    status_code=201,
    summary="Completar registro por invitación",
    description="Crea la cuenta del usuario a partir de un token de invitación vigente.",
)
async def completar_registro(
    datos: CompletarRegistroRequest,
    caso_uso: CompletarRegistro = Depends(obtener_caso_uso_completar_registro),
):
    try:
        usuario = await caso_uso.ejecutar(
            codigo_token=datos.codigo_token,
            clave=datos.clave,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            acepto_tratamiento=datos.acepto_tratamiento,
        )
    except TokenInvalido:
        raise HTTPException(
            status_code=401, detail="Token inválido, expirado o ya utilizado"
        )
    except AutorizacionRequerida:
        raise HTTPException(
            status_code=400,
            detail="Debe aceptar el tratamiento de datos personales para completar el registro",
        )

    return UsuarioResponse(
        id=usuario.id,
        correo=usuario.correo,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
    )


@router.post(
    "/solicitar-restablecimiento",
    response_model=MensajeResponse,
    dependencies=[Depends(limite_envio_correo)],
    summary="Solicitar restablecimiento de contraseña",
    description="Por seguridad, responde el mismo mensaje exista o no el correo registrado.",
)
async def solicitar_restablecimiento(
    datos: SolicitarRestablecimientoRequest,
    caso_uso: SolicitarRestablecimiento = Depends(
        obtener_caso_uso_solicitar_restablecimiento
    ),
):
    await caso_uso.ejecutar(datos.correo)
    return MensajeResponse(
        mensaje="Si el correo está registrado, recibirá un enlace de restablecimiento."
    )


@router.post(
    "/restablecer-contrasena",
    response_model=MensajeResponse,
    dependencies=[Depends(limite_token)],
    summary="Restablecer contraseña",
    description="Consume el token de restablecimiento y revoca todas las sesiones activas.",
)
async def restablecer_contrasena(
    datos: RestablecerContrasenaRequest,
    caso_uso: RestablecerContrasena = Depends(obtener_caso_uso_restablecer_contrasena),
):
    try:
        await caso_uso.ejecutar(datos.codigo_token, datos.clave_nueva)
    except TokenRestablecimientoInvalido:
        raise HTTPException(
            status_code=401, detail="Token inválido, expirado o ya utilizado"
        )
    except ClaveReutilizada:
        raise HTTPException(
            status_code=400,
            detail="No puede reutilizar una de sus últimas 5 contraseñas",
        )

    return MensajeResponse(mensaje="Contraseña actualizada correctamente")
