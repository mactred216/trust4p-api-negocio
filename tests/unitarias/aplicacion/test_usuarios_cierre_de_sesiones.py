from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_usuarios import (DesactivarUsuario,
                                                         EditarUsuario)
from src.dominio.entidades.usuario import Rol, Usuario

# Cambiar el rol o la empresa, o desactivar, cierra las sesiones abiertas: la
# sesión guarda el rol y los permisos con que el usuario inició.


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
async def test_cambiar_el_rol_cierra_las_sesiones_del_usuario():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_usuario_prueba()
    repo_sesion = AsyncMock()

    await EditarUsuario(repo, AsyncMock(), repo_sesion).ejecutar(
        "user-1", rol_codigo="consultor"
    )

    repo_sesion.revocar_todas_de_usuario.assert_awaited_once_with("user-1")


@pytest.mark.asyncio
async def test_cambiar_la_empresa_cierra_las_sesiones_del_usuario():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_usuario_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = AsyncMock(activo=True)
    repo_sesion = AsyncMock()

    await EditarUsuario(repo, repo_empresa, repo_sesion).ejecutar(
        "user-1", empresa_id="emp-2"
    )

    repo_sesion.revocar_todas_de_usuario.assert_awaited_once_with("user-1")


@pytest.mark.asyncio
async def test_editar_solo_el_nombre_no_cierra_sesiones():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_usuario_prueba()
    repo_sesion = AsyncMock()

    await EditarUsuario(repo, AsyncMock(), repo_sesion).ejecutar(
        "user-1", nombres="Nuevo"
    )

    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()


@pytest.mark.asyncio
async def test_enviar_el_mismo_rol_y_la_misma_empresa_no_cierra_sesiones():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_usuario_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = AsyncMock(activo=True)
    repo_sesion = AsyncMock()

    await EditarUsuario(repo, repo_empresa, repo_sesion).ejecutar(
        "user-1", rol_codigo="representante", empresa_id="emp-1"
    )

    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()


@pytest.mark.asyncio
async def test_si_la_edicion_falla_no_se_cierran_sesiones():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_usuario_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = None
    repo_sesion = AsyncMock()

    with pytest.raises(ValueError):
        await EditarUsuario(repo, repo_empresa, repo_sesion).ejecutar(
            "user-1", empresa_id="no-existe"
        )

    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()


@pytest.mark.asyncio
async def test_desactivar_cierra_las_sesiones_del_usuario():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = crear_usuario_prueba()
    repo_sesion = AsyncMock()

    await DesactivarUsuario(repo, repo_sesion).ejecutar("user-1")

    repo_sesion.revocar_todas_de_usuario.assert_awaited_once_with("user-1")


@pytest.mark.asyncio
async def test_desactivar_a_uno_ya_inactivo_no_toca_sesiones():
    usuario = crear_usuario_prueba()
    usuario.activo = False
    repo = AsyncMock()
    repo.obtener_por_id.return_value = usuario
    repo_sesion = AsyncMock()

    with pytest.raises(ValueError):
        await DesactivarUsuario(repo, repo_sesion).ejecutar("user-1")

    repo_sesion.revocar_todas_de_usuario.assert_not_awaited()
