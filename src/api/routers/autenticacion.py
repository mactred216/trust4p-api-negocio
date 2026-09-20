from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr

from src.api.dependencias import obtener_caso_uso_iniciar_sesion
from src.aplicacion.casos_uso.iniciar_sesion import (CredencialesInvalidas,
                                                     CuentaBloqueada,
                                                     IniciarSesion)

router = APIRouter(prefix="/auth", tags=["autenticacion"])


class LoginRequest(BaseModel):
    correo: EmailStr
    clave: str


class LoginResponse(BaseModel):
    mensaje: str


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
