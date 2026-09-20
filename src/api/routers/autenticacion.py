import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, field_validator

from src.api.dependencias import (obtener_caso_uso_completar_registro,
                                  obtener_caso_uso_iniciar_sesion)
from src.aplicacion.casos_uso.completar_registro import (AutorizacionRequerida,
                                                         CompletarRegistro,
                                                         TokenInvalido)
from src.aplicacion.casos_uso.iniciar_sesion import (CredencialesInvalidas,
                                                     CuentaBloqueada,
                                                     IniciarSesion)

router = APIRouter(prefix="/auth", tags=["autenticacion"])


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
        if not v or not v.strip():
            raise ValueError("El código de invitación es obligatorio")
        return v

    @field_validator("clave")
    @classmethod
    def clave_cumple_politica(cls, v: str) -> str:
        if len(v) < 12:
            raise ValueError("La contraseña debe tener al menos 12 caracteres")

        tiene_mayuscula = re.search(r"[A-Z]", v) is not None
        tiene_minuscula = re.search(r"[a-z]", v) is not None
        tiene_numero = re.search(r"\d", v) is not None
        tiene_especial = re.search(r"[^A-Za-z0-9]", v) is not None

        tipos_presentes = sum(
            [tiene_mayuscula, tiene_minuscula, tiene_numero, tiene_especial]
        )
        if tipos_presentes < 3:
            raise ValueError(
                "La contraseña debe combinar al menos tres de los siguientes: "
                "mayúsculas, minúsculas, números y caracteres especiales"
            )
        return v

    @field_validator("nombres", "apellidos")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Este campo no puede estar vacío")
        if len(v.strip()) < 2:
            raise ValueError("Debe tener al menos 2 caracteres")
        return v.strip()


class UsuarioResponse(BaseModel):
    id: str
    correo: str
    nombres: str
    apellidos: str


@router.post(
    "/login",
    response_model=LoginResponse,
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
