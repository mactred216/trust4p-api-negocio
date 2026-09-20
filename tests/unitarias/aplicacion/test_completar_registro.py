from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.completar_registro import (AutorizacionRequerida,
                                                         CompletarRegistro,
                                                         TokenInvalido)
from src.dominio.entidades.solicitud_acceso import SolicitudAcceso
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_token_prueba():
    return TokenVerificacion(
        id="tok-1",
        tipo=TipoToken.INVITACION,
        correo_destino="ana@innovatech.com",
        solicitud_id="sol-1",
    )


def crear_solicitud_aprobada():
    solicitud = SolicitudAcceso(
        id="sol-1",
        nombre_empresa="InnovaTech",
        correo_solicitante="ana@innovatech.com",
        nombre_solicitante="Ana Pérez",
    )
    solicitud.aprobar(empresa_id="emp-1")
    return solicitud


@pytest.mark.asyncio
async def test_completar_registro_exitoso():
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = crear_token_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.guardar.side_effect = lambda u: u
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = crear_solicitud_aprobada()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)
    usuario = await caso_uso.ejecutar(
        codigo_token="codigo-valido",
        clave="ClaveSegura123",
        nombres="Ana",
        apellidos="Pérez",
        acepto_tratamiento=True,
    )

    assert usuario.correo == "ana@innovatech.com"
    assert usuario.empresa_id == "emp-1"
    assert usuario.rol.codigo == "representante"
    repo_token.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_sin_autorizacion_tratamiento_falla():
    repo_token = AsyncMock()
    repo_usuario = AsyncMock()
    repo_solicitud = AsyncMock()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)

    with pytest.raises(AutorizacionRequerida):
        await caso_uso.ejecutar(
            codigo_token="cualquiera",
            clave="clave",
            nombres="A",
            apellidos="B",
            acepto_tratamiento=False,
        )
    repo_usuario.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_token_inexistente_falla():
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = None
    repo_usuario = AsyncMock()
    repo_solicitud = AsyncMock()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar(
            codigo_token="codigo-invalido",
            clave="clave",
            nombres="A",
            apellidos="B",
            acepto_tratamiento=True,
        )


@pytest.mark.asyncio
async def test_token_ya_usado_falla():
    token = crear_token_prueba()
    token.marcar_usado()
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_usuario = AsyncMock()
    repo_solicitud = AsyncMock()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar(
            codigo_token="codigo-usado",
            clave="clave",
            nombres="A",
            apellidos="B",
            acepto_tratamiento=True,
        )
