from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_roles import (AgregarPermisoARol,
                                                      PermisoNoExiste,
                                                      QuitarPermisoDeRol,
                                                      RolNoEncontrado)
from src.dominio.entidades.permiso import Permiso
from src.dominio.entidades.rol import RolCatalogo
from src.dominio.entidades.usuario import Rol, Usuario


def crear_rol_prueba():
    return RolCatalogo(id="rol-1", codigo="consultor", nombre="Consultor")


def crear_permiso_prueba():
    return Permiso(
        id="perm-1",
        codigo="diagnosticos.consultar",
        modulo="diagnosticos",
        descripcion="Consultar diagnósticos",
    )


def crear_usuario_con_rol(codigo_rol="consultor"):
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo=codigo_rol, permisos=[]),
    )


@pytest.mark.asyncio
async def test_agregar_permiso_a_rol_existente():
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = crear_rol_prueba()
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = crear_permiso_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.listar_por_rol.return_value = []
    repo_sesion = AsyncMock()

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso, repo_usuario, repo_sesion)
    rol = await caso_uso.ejecutar("consultor", "diagnosticos.consultar")

    assert "diagnosticos.consultar" in rol.permisos
    repo_rol.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_permiso_inexistente_falla():
    repo_rol = AsyncMock()
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = None
    repo_usuario = AsyncMock()
    repo_sesion = AsyncMock()

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso, repo_usuario, repo_sesion)

    with pytest.raises(PermisoNoExiste):
        await caso_uso.ejecutar("consultor", "permiso-inexistente")


@pytest.mark.asyncio
async def test_agregar_permiso_a_rol_inexistente_falla():
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = None
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = crear_permiso_prueba()
    repo_usuario = AsyncMock()
    repo_sesion = AsyncMock()

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso, repo_usuario, repo_sesion)

    with pytest.raises(RolNoEncontrado):
        await caso_uso.ejecutar("rol-inexistente", "diagnosticos.consultar")


# R-17: modificar los permisos de un rol revoca las sesiones de sus usuarios
# y sincroniza la copia embebida de permisos (R-16)
@pytest.mark.asyncio
async def test_agregar_permiso_revoca_sesiones_y_sincroniza_usuarios_afectados():
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = crear_rol_prueba()
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = crear_permiso_prueba()
    usuario = crear_usuario_con_rol()
    repo_usuario = AsyncMock()
    repo_usuario.listar_por_rol.return_value = [usuario]
    repo_sesion = AsyncMock()

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso, repo_usuario, repo_sesion)
    await caso_uso.ejecutar("consultor", "diagnosticos.consultar")

    repo_usuario.listar_por_rol.assert_called_once_with("consultor")
    assert "diagnosticos.consultar" in usuario.rol.permisos
    repo_usuario.actualizar.assert_called_once_with(usuario)
    repo_sesion.revocar_todas_de_usuario.assert_called_once_with("user-1")


@pytest.mark.asyncio
async def test_quitar_permiso_de_rol():
    rol = crear_rol_prueba()
    rol.agregar_permiso("diagnosticos.consultar")
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = rol
    repo_usuario = AsyncMock()
    repo_usuario.listar_por_rol.return_value = []
    repo_sesion = AsyncMock()

    caso_uso = QuitarPermisoDeRol(repo_rol, repo_usuario, repo_sesion)
    resultado = await caso_uso.ejecutar("consultor", "diagnosticos.consultar")

    assert "diagnosticos.consultar" not in resultado.permisos


@pytest.mark.asyncio
async def test_quitar_permiso_revoca_sesiones_de_usuarios_afectados():
    rol = crear_rol_prueba()
    rol.agregar_permiso("diagnosticos.consultar")
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = rol
    usuario = crear_usuario_con_rol()
    repo_usuario = AsyncMock()
    repo_usuario.listar_por_rol.return_value = [usuario]
    repo_sesion = AsyncMock()

    caso_uso = QuitarPermisoDeRol(repo_rol, repo_usuario, repo_sesion)
    await caso_uso.ejecutar("consultor", "diagnosticos.consultar")

    repo_sesion.revocar_todas_de_usuario.assert_called_once_with("user-1")
    assert "diagnosticos.consultar" not in usuario.rol.permisos


@pytest.mark.asyncio
async def test_quitar_permiso_critico_de_administrador_falla():
    rol_admin = RolCatalogo(
        id="rol-admin", codigo="administrador", nombre="Administrador"
    )
    rol_admin.agregar_permiso("roles.gestionar")
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = rol_admin
    repo_usuario = AsyncMock()
    repo_sesion = AsyncMock()

    caso_uso = QuitarPermisoDeRol(repo_rol, repo_usuario, repo_sesion)

    with pytest.raises(ValueError):
        await caso_uso.ejecutar("administrador", "roles.gestionar")
    repo_usuario.listar_por_rol.assert_not_called()
