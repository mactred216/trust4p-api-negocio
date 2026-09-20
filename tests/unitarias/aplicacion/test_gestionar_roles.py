from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_roles import (AgregarPermisoARol,
                                                      PermisoNoExiste,
                                                      QuitarPermisoDeRol,
                                                      RolNoEncontrado)
from src.dominio.entidades.permiso import Permiso
from src.dominio.entidades.rol import RolCatalogo


def crear_rol_prueba():
    return RolCatalogo(id="rol-1", codigo="consultor", nombre="Consultor")


def crear_permiso_prueba():
    return Permiso(
        id="perm-1",
        codigo="diagnosticos.consultar",
        modulo="diagnosticos",
        descripcion="Consultar diagnósticos",
    )


@pytest.mark.asyncio
async def test_agregar_permiso_a_rol_existente():
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = crear_rol_prueba()
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = crear_permiso_prueba()

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso)
    rol = await caso_uso.ejecutar("consultor", "diagnosticos.consultar")

    assert "diagnosticos.consultar" in rol.permisos
    repo_rol.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_agregar_permiso_inexistente_falla():
    repo_rol = AsyncMock()
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = None

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso)

    with pytest.raises(PermisoNoExiste):
        await caso_uso.ejecutar("consultor", "permiso-inexistente")


@pytest.mark.asyncio
async def test_agregar_permiso_a_rol_inexistente_falla():
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = None
    repo_permiso = AsyncMock()
    repo_permiso.obtener_por_codigo.return_value = crear_permiso_prueba()

    caso_uso = AgregarPermisoARol(repo_rol, repo_permiso)

    with pytest.raises(RolNoEncontrado):
        await caso_uso.ejecutar("rol-inexistente", "diagnosticos.consultar")


@pytest.mark.asyncio
async def test_quitar_permiso_de_rol():
    rol = crear_rol_prueba()
    rol.agregar_permiso("diagnosticos.consultar")
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = rol

    caso_uso = QuitarPermisoDeRol(repo_rol)
    resultado = await caso_uso.ejecutar("consultor", "diagnosticos.consultar")

    assert "diagnosticos.consultar" not in resultado.permisos


@pytest.mark.asyncio
async def test_quitar_permiso_critico_de_administrador_falla():
    rol_admin = RolCatalogo(
        id="rol-admin", codigo="administrador", nombre="Administrador"
    )
    rol_admin.agregar_permiso("roles.gestionar")
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = rol_admin

    caso_uso = QuitarPermisoDeRol(repo_rol)

    with pytest.raises(ValueError):
        await caso_uso.ejecutar("administrador", "roles.gestionar")
