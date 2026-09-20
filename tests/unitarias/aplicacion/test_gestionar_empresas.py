from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_empresas import (ConsultarEmpresa,
                                                         DesactivarEmpresa,
                                                         EditarEmpresa,
                                                         EmpresaNoEncontrada,
                                                         ListarEmpresas,
                                                         ReactivarEmpresa)
from src.dominio.entidades.empresa import Empresa, Sector


def crear_empresa_prueba():
    return Empresa(
        id="emp-1",
        nombre="InnovaTech",
        sector=Sector(id="1", codigo="J62", nombre="Software"),
    )


@pytest.mark.asyncio
async def test_listar_solo_activas_por_defecto():
    repo = AsyncMock()
    repo.listar_activas.return_value = [crear_empresa_prueba()]

    caso_uso = ListarEmpresas(repo)
    resultado = await caso_uso.ejecutar()

    assert len(resultado) == 1
    repo.listar_activas.assert_called_once()
    repo.listar_todas.assert_not_called()


@pytest.mark.asyncio
async def test_listar_todas_cuando_se_pide_explicitamente():
    repo = AsyncMock()
    repo.listar_todas.return_value = [crear_empresa_prueba()]

    caso_uso = ListarEmpresas(repo)
    await caso_uso.ejecutar(solo_activas=False)

    repo.listar_todas.assert_called_once()


@pytest.mark.asyncio
async def test_consultar_empresa_inexistente_lanza_excepcion():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None

    caso_uso = ConsultarEmpresa(repo)

    with pytest.raises(EmpresaNoEncontrada):
        await caso_uso.ejecutar("emp-inexistente")


@pytest.mark.asyncio
async def test_editar_empresa_actualiza_solo_campos_enviados():
    empresa = crear_empresa_prueba()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = empresa

    caso_uso = EditarEmpresa(repo)
    resultado = await caso_uso.ejecutar("emp-1", ciudad="Bogotá")

    assert resultado.ciudad == "Bogotá"
    assert resultado.nombre == "InnovaTech"  # no se tocó
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_desactivar_empresa_la_marca_inactiva():
    empresa = crear_empresa_prueba()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = empresa

    caso_uso = DesactivarEmpresa(repo)
    await caso_uso.ejecutar("emp-1")

    assert empresa.activo is False
    repo.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_reactivar_empresa_la_marca_activa():
    empresa = crear_empresa_prueba()
    empresa.desactivar()
    repo = AsyncMock()
    repo.obtener_por_id.return_value = empresa

    caso_uso = ReactivarEmpresa(repo)
    await caso_uso.ejecutar("emp-1")

    assert empresa.activo is True
