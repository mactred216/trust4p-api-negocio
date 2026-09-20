from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.asignar_consultor import (AsignarConsultor,
                                                        ConsultorInactivo,
                                                        ConsultorNoEncontrado,
                                                        EmpresaInactiva,
                                                        EmpresaNoEncontrada)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.usuario import Rol, Usuario


def crear_consultor_prueba():
    return Usuario(
        id="cons-1",
        correo="carlos@trust4p.com",
        clave_hash="hash",
        nombres="Carlos",
        apellidos="Gómez",
        rol=Rol(codigo="consultor"),
    )


def crear_empresa_prueba():
    return Empresa(
        id="emp-1",
        nombre="InnovaTech",
        sector=Sector(id="1", codigo="J62", nombre="Software"),
    )


@pytest.mark.asyncio
async def test_asignar_consultor_a_empresa_existente():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = crear_empresa_prueba()

    caso_uso = AsignarConsultor(repo_usuario, repo_empresa)
    await caso_uso.asignar("cons-1", "emp-1")

    repo_usuario.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_asignar_a_consultor_inexistente_falla():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = None
    repo_empresa = AsyncMock()

    caso_uso = AsignarConsultor(repo_usuario, repo_empresa)

    with pytest.raises(ConsultorNoEncontrado):
        await caso_uso.asignar("cons-inexistente", "emp-1")


@pytest.mark.asyncio
async def test_asignar_a_empresa_inexistente_falla():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = None

    caso_uso = AsignarConsultor(repo_usuario, repo_empresa)

    with pytest.raises(EmpresaNoEncontrada):
        await caso_uso.asignar("cons-1", "emp-inexistente")


@pytest.mark.asyncio
async def test_finalizar_asignacion():
    consultor = crear_consultor_prueba()
    consultor.asignar_empresa("emp-1")
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = consultor
    repo_empresa = AsyncMock()

    caso_uso = AsignarConsultor(repo_usuario, repo_empresa)
    await caso_uso.finalizar("cons-1", "emp-1")

    assert "emp-1" not in consultor.empresas_asignadas_vigentes()


@pytest.mark.asyncio
async def test_no_se_puede_asignar_consultor_inactivo():
    consultor = crear_consultor_prueba()
    consultor.activo = False
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = consultor
    repo_empresa = AsyncMock()

    caso_uso = AsignarConsultor(repo_usuario, repo_empresa)

    with pytest.raises(ConsultorInactivo):
        await caso_uso.asignar("cons-1", "emp-1")


@pytest.mark.asyncio
async def test_no_se_puede_asignar_empresa_inactiva():
    empresa = crear_empresa_prueba()
    empresa.activo = False
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor_prueba()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = empresa

    caso_uso = AsignarConsultor(repo_usuario, repo_empresa)

    with pytest.raises(EmpresaInactiva):
        await caso_uso.asignar("cons-1", "emp-1")
