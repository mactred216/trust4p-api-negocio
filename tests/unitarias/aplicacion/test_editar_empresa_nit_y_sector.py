from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_empresas import (EditarEmpresa,
                                                         NitYaRegistrado,
                                                         SectorNoValido)
from src.dominio.entidades.empresa import Empresa, Sector

# Quien tiene el permiso de edición puede cambiar nombre, NIT, sector y número
# de empleados de una empresa.

SERVICIOS = Sector(id="s-1", codigo="servicios", nombre="Servicios profesionales")
FINTECH = Sector(id="s-2", codigo="fintech", nombre="Fintech y Servicios financieros")


def empresa(**extra):
    base = dict(
        id="emp-1",
        nombre="InnovaTech",
        sector=SERVICIOS,
        nit="900111222",
        numero_empleados=30,
    )
    return Empresa(**{**base, **extra})


def repos(emp=None, sector=FINTECH, nit_existente=None):
    repo = AsyncMock()
    repo.obtener_por_id.return_value = emp or empresa()
    repo.obtener_por_nit.return_value = nit_existente
    repo_sector = AsyncMock()
    repo_sector.obtener_por_codigo.return_value = sector
    return repo, repo_sector


@pytest.mark.asyncio
async def test_cambia_el_sector_con_el_del_catalogo():
    repo, repo_sector = repos()

    resultado = await EditarEmpresa(repo, repo_sector).ejecutar("emp-1", sector_codigo="fintech")

    assert resultado.sector == FINTECH
    repo_sector.obtener_por_codigo.assert_awaited_once_with("fintech")
    repo.actualizar.assert_awaited_once()


@pytest.mark.asyncio
async def test_un_sector_inexistente_o_inactivo_se_rechaza_y_no_se_guarda_nada():
    repo, repo_sector = repos(sector=None)

    with pytest.raises(SectorNoValido):
        await EditarEmpresa(repo, repo_sector).ejecutar(
            "emp-1", sector_codigo="no-existe", nombre="Otro nombre", numero_empleados=99
        )

    repo.actualizar.assert_not_awaited()


@pytest.mark.asyncio
async def test_si_el_sector_no_cambia_no_se_consulta_el_catalogo():
    # Una empresa puede conservar un sector que luego se desactivó.
    repo, repo_sector = repos()

    await EditarEmpresa(repo, repo_sector).ejecutar("emp-1", sector_codigo="servicios", nombre="Nuevo")

    repo_sector.obtener_por_codigo.assert_not_awaited()


@pytest.mark.asyncio
async def test_sin_catalogo_de_sectores_no_se_puede_cambiar_el_sector():
    repo, _ = repos()

    with pytest.raises(SectorNoValido):
        await EditarEmpresa(repo).ejecutar("emp-1", sector_codigo="fintech")


@pytest.mark.asyncio
async def test_cambia_el_nit():
    repo, repo_sector = repos()

    resultado = await EditarEmpresa(repo, repo_sector).ejecutar("emp-1", nit="800555666-1")

    assert resultado.nit == "800555666-1"


@pytest.mark.asyncio
async def test_un_nit_de_otra_empresa_se_rechaza_y_no_se_guarda_nada():
    repo, repo_sector = repos(nit_existente=empresa(id="emp-2", nit="800555666"))

    with pytest.raises(NitYaRegistrado):
        await EditarEmpresa(repo, repo_sector).ejecutar(
            "emp-1", nit="800555666", sector_codigo="fintech"
        )

    repo.actualizar.assert_not_awaited()


@pytest.mark.asyncio
async def test_una_empresa_sin_nit_puede_recibir_uno():
    repo, repo_sector = repos(emp=empresa(nit=None))

    resultado = await EditarEmpresa(repo, repo_sector).ejecutar("emp-1", nit="900123456")

    assert resultado.nit == "900123456"


@pytest.mark.asyncio
async def test_cambia_todos_los_campos_a_la_vez_y_respeta_lo_que_no_se_envia():
    emp = empresa(ciudad="Cali")
    repo, repo_sector = repos(emp=emp)

    resultado = await EditarEmpresa(repo, repo_sector).ejecutar(
        "emp-1",
        nombre="Nueva SAS",
        nit="800555666",
        sector_codigo="fintech",
        numero_empleados=120,
    )

    assert (resultado.nombre, resultado.nit, resultado.sector, resultado.numero_empleados) == (
        "Nueva SAS",
        "800555666",
        FINTECH,
        120,
    )
    assert resultado.ciudad == "Cali"
