from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_usuarios import (ConsultarUsuario,
                                                         DesactivarUsuario,
                                                         EditarUsuario,
                                                         ListarUsuarios,
                                                         ReactivarUsuario,
                                                         UsuarioNoEncontrado)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario_prueba():
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id="emp-1",
    )


@pytest.mark.asyncio
async def test_listar_usuarios_por_empresa():
    repo = AsyncMock()
    repo.listar_por_empresa.return_value = [crear_usuario_prueba()]

    caso_uso = ListarUsuarios(repo)
    resultado = await caso_uso.ejecutar(empresa_id="emp-1")

    assert len(resultado) == 1
    repo.listar_por_empresa.assert_called_once_with("emp-1")


@pytest.mark.asyncio
async def test_listar_todos_sin_filtro():
    repo = AsyncMock()
    repo.listar_todos.return_value = [crear_usuario_prueba()]

    caso_uso = ListarUsuarios(repo)
    await caso_uso.ejecutar()

    repo.listar_todos.assert_called_once()


@pytest.mark.asyncio
async def test_consultar_usuario_inexistente_lanza_excepcion():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = ConsultarUsuario(repo)

    with pytest.raises(UsuarioNoEncontrado):
        await caso_uso.ejecutar("user-inexistente")


@pytest.mark.asyncio
async def test_editar_usuario_actualiza_solo_campos_enviados():
    usuario = crear_usuario_prueba()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario

    caso_uso = EditarUsuario(repo)
    resultado = await caso_uso.ejecutar("user-1", apellidos="González")

    assert resultado.apellidos == "González"
    assert resultado.nombres == "Ana"  # no se tocó
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_editar_rol_de_usuario():
    usuario = crear_usuario_prueba()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario

    caso_uso = EditarUsuario(repo)
    resultado = await caso_uso.ejecutar("user-1", rol_codigo="consultor")

    assert resultado.rol.codigo == "consultor"


@pytest.mark.asyncio
async def test_desactivar_usuario():
    usuario = crear_usuario_prueba()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario

    caso_uso = DesactivarUsuario(repo)
    await caso_uso.ejecutar("user-1")

    assert usuario.activo is False


@pytest.mark.asyncio
async def test_reactivar_usuario():
    usuario = crear_usuario_prueba()
    usuario.activo = False
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario

    caso_uso = ReactivarUsuario(repo)
    await caso_uso.ejecutar("user-1")

    assert usuario.activo is True
