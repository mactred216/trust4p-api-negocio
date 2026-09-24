from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.recuperar_contrasena import (
    RestablecerContrasena, SolicitarRestablecimiento, TokenInvalido)
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario_prueba():
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash-viejo",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
    )


@pytest.mark.asyncio
async def test_solicitar_restablecimiento_con_correo_existente_crea_token():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = crear_usuario_prueba()
    repo_token = AsyncMock()
    servicio_correo = AsyncMock()

    caso_uso = SolicitarRestablecimiento(repo_usuario, repo_token, servicio_correo)
    await caso_uso.ejecutar("ana@innovatech.com")

    repo_token.guardar.assert_called_once()
    servicio_correo.enviar.assert_called_once()
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"] == "ana@innovatech.com"
    )


@pytest.mark.asyncio
async def test_solicitar_restablecimiento_con_correo_inexistente_no_falla():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = None
    repo_token = AsyncMock()
    servicio_correo = AsyncMock()

    caso_uso = SolicitarRestablecimiento(repo_usuario, repo_token, servicio_correo)
    await caso_uso.ejecutar("noexiste@correo.com")  # no debe lanzar excepción

    repo_token.guardar.assert_not_called()
    servicio_correo.enviar.assert_not_called()


@pytest.mark.asyncio
async def test_restablecer_contrasena_exitoso():
    usuario = crear_usuario_prueba()
    token = TokenVerificacion(
        id="tok-1",
        tipo=TipoToken.RESTABLECER_CLAVE,
        correo_destino="ana@innovatech.com",
        usuario_id="user-1",
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = usuario
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_sesion = AsyncMock()

    caso_uso = RestablecerContrasena(repo_usuario, repo_token, repo_sesion)
    await caso_uso.ejecutar("codigo-valido", "NuevaClaveSegura123")

    repo_usuario.actualizar.assert_called_once()
    repo_token.actualizar.assert_called_once()
    repo_sesion.revocar_todas_de_usuario.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_restablecer_con_token_inexistente_falla():
    repo_usuario = AsyncMock()
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = None
    repo_sesion = AsyncMock()

    caso_uso = RestablecerContrasena(repo_usuario, repo_token, repo_sesion)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("codigo-invalido", "NuevaClaveSegura123")


@pytest.mark.asyncio
async def test_restablecer_con_token_de_tipo_incorrecto_falla():
    token_invitacion = TokenVerificacion(
        id="tok-1",
        tipo=TipoToken.INVITACION,
        correo_destino="ana@innovatech.com",
    )
    repo_usuario = AsyncMock()
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token_invitacion
    repo_sesion = AsyncMock()

    caso_uso = RestablecerContrasena(repo_usuario, repo_token, repo_sesion)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("codigo-de-invitacion", "NuevaClaveSegura123")
