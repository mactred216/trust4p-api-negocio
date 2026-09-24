from unittest.mock import AsyncMock

import bcrypt
import pytest

from src.aplicacion.casos_uso.gestionar_perfil import (ActualizarPerfil,
                                                       CambiarContrasena,
                                                       CerrarSesion,
                                                       ClaveActualIncorrecta,
                                                       ClaveReutilizada,
                                                       EliminarDatosPersonales,
                                                       UsuarioNoEncontrado)
from src.dominio.entidades.usuario import Rol, Usuario


def _hash(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def crear_usuario_prueba(clave_actual: str = "ClaveActualSegura123") -> Usuario:
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash=_hash(clave_actual),
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
    )


@pytest.mark.asyncio
async def test_cerrar_sesion_revoca_el_token():
    repo_sesion = AsyncMock()

    caso_uso = CerrarSesion(repo_sesion)
    await caso_uso.ejecutar("token-abc")

    repo_sesion.revocar.assert_called_once_with("token-abc")


@pytest.mark.asyncio
async def test_actualizar_perfil():
    usuario = crear_usuario_prueba()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario

    caso_uso = ActualizarPerfil(repo)
    resultado = await caso_uso.ejecutar(
        "user-1", cargo="Gerente", telefono="3001234567"
    )

    assert resultado.cargo == "Gerente"
    assert resultado.telefono == "3001234567"
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_actualizar_perfil_de_usuario_inexistente_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = ActualizarPerfil(repo)
    with pytest.raises(UsuarioNoEncontrado):
        await caso_uso.ejecutar("no-existe", cargo="Gerente")


@pytest.mark.asyncio
async def test_cambiar_contrasena_exitoso():
    usuario = crear_usuario_prueba("ClaveActualSegura123")
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_sesion = AsyncMock()

    caso_uso = CambiarContrasena(repo_usuario, repo_sesion)
    await caso_uso.ejecutar("user-1", "ClaveActualSegura123", "ClaveNuevaSegura456")

    repo_usuario.actualizar.assert_called_once()
    repo_sesion.revocar_todas_de_usuario.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_cambiar_contrasena_con_clave_actual_incorrecta_falla():
    usuario = crear_usuario_prueba("ClaveActualSegura123")
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_sesion = AsyncMock()

    caso_uso = CambiarContrasena(repo_usuario, repo_sesion)
    with pytest.raises(ClaveActualIncorrecta):
        await caso_uso.ejecutar("user-1", "ClaveIncorrecta999", "ClaveNuevaSegura456")

    repo_usuario.actualizar.assert_not_called()
    repo_sesion.revocar_todas_de_usuario.assert_not_called()


@pytest.mark.asyncio
async def test_cambiar_contrasena_reutilizada_falla():
    usuario = crear_usuario_prueba("ClaveActualSegura123")
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_sesion = AsyncMock()

    caso_uso = CambiarContrasena(repo_usuario, repo_sesion)
    with pytest.raises(ClaveReutilizada):
        await caso_uso.ejecutar(
            "user-1", "ClaveActualSegura123", "ClaveActualSegura123"
        )


@pytest.mark.asyncio
async def test_cambiar_contrasena_usuario_inexistente_falla():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = None
    repo_sesion = AsyncMock()

    caso_uso = CambiarContrasena(repo_usuario, repo_sesion)
    with pytest.raises(UsuarioNoEncontrado):
        await caso_uso.ejecutar("no-existe", "x", "ClaveNuevaSegura456")


@pytest.mark.asyncio
async def test_eliminar_datos_personales():
    usuario = crear_usuario_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_sesion = AsyncMock()
    servicio_correo = AsyncMock()

    caso_uso = EliminarDatosPersonales(repo_usuario, repo_sesion, servicio_correo)
    await caso_uso.ejecutar("user-1")

    assert usuario.activo is False
    servicio_correo.enviar.assert_called_once()
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"] == "ana@innovatech.com"
    )
    repo_usuario.actualizar.assert_called_once()
    repo_sesion.revocar_todas_de_usuario.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_eliminar_datos_personales_de_cuenta_ya_inactiva_falla():
    usuario = crear_usuario_prueba()
    usuario.activo = False
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_sesion = AsyncMock()
    servicio_correo = AsyncMock()

    caso_uso = EliminarDatosPersonales(repo_usuario, repo_sesion, servicio_correo)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-1")
    servicio_correo.enviar.assert_not_called()


@pytest.mark.asyncio
async def test_eliminar_datos_personales_usuario_inexistente_falla():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = None
    repo_sesion = AsyncMock()
    servicio_correo = AsyncMock()

    caso_uso = EliminarDatosPersonales(repo_usuario, repo_sesion, servicio_correo)
    with pytest.raises(UsuarioNoEncontrado):
        await caso_uso.ejecutar("no-existe")
