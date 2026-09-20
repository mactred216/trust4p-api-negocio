from unittest.mock import AsyncMock

import bcrypt
import pytest

from src.aplicacion.casos_uso.iniciar_sesion import (CredencialesInvalidas,
                                                     CuentaBloqueada,
                                                     IniciarSesion)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario_prueba(clave_plana="claveSegura123"):
    clave_hash = bcrypt.hashpw(clave_plana.encode(), bcrypt.gensalt()).decode()
    return Usuario(
        id="1",
        correo="admin@trust4p.com",
        clave_hash=clave_hash,
        nombres="Admin",
        apellidos="Trust4P",
        rol=Rol(codigo="administrador"),
    )


@pytest.mark.asyncio
async def test_login_exitoso_devuelve_token():
    usuario = crear_usuario_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = usuario
    repo_sesion = AsyncMock()
    repo_sesion.crear.return_value = "token-generado"

    caso_uso = IniciarSesion(repo_usuario, repo_sesion)
    token = await caso_uso.ejecutar("admin@trust4p.com", "claveSegura123")

    assert token == "token-generado"


@pytest.mark.asyncio
async def test_clave_incorrecta_lanza_credenciales_invalidas():
    usuario = crear_usuario_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = usuario
    repo_sesion = AsyncMock()

    caso_uso = IniciarSesion(repo_usuario, repo_sesion)

    with pytest.raises(CredencialesInvalidas):
        await caso_uso.ejecutar("admin@trust4p.com", "claveIncorrecta")


@pytest.mark.asyncio
async def test_correo_inexistente_lanza_credenciales_invalidas():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = None
    repo_sesion = AsyncMock()

    caso_uso = IniciarSesion(repo_usuario, repo_sesion)

    with pytest.raises(CredencialesInvalidas):
        await caso_uso.ejecutar("noexiste@trust4p.com", "cualquiera")


@pytest.mark.asyncio
async def test_cuenta_bloqueada_lanza_excepcion():
    usuario = crear_usuario_prueba()
    for _ in range(5):
        usuario.registrar_intento_fallido()

    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = usuario
    repo_sesion = AsyncMock()

    caso_uso = IniciarSesion(repo_usuario, repo_sesion)

    with pytest.raises(CuentaBloqueada):
        await caso_uso.ejecutar("admin@trust4p.com", "claveSegura123")
