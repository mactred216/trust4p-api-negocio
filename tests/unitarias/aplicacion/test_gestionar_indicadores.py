from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_indicadores import (
    ConsultarIndicadoresAgregados, ExportarDatosAgregados, FiltroInvalido)
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario


def empresa(id, sector="J62", empleados=30):
    return Empresa(
        id=id,
        nombre=f"Empresa {id}",
        sector=Sector(id="s", codigo=sector, nombre=f"Sector {sector}"),
        numero_empleados=empleados,
    )


def diagnostico(empresa_id, consecutivo=1, estado="evaluado", nivel=2, indice="6"):
    d = Diagnostico(
        id=f"d-{empresa_id}-{consecutivo}",
        empresa_id=empresa_id,
        empresa_nombre="x",
        usuario_id="u",
        modelo_version="1",
        consecutivo=consecutivo,
        estado=estado,
    )
    if estado != "borrador":
        d.resultado = ResultadoDiagnostico(
            indice_global=Decimal(indice),
            nivel=nivel,
            nivel_descripcion="...",
            dimensiones=[DimensionResultado(codigo="innovacion", puntaje=Decimal("7"))],
            perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
        )
    return d


def consultor(empresas):
    return Usuario(
        id="c-1",
        correo="c@trust4p.com",
        clave_hash="h",
        nombres="C",
        apellidos="C",
        rol=Rol(codigo="consultor"),
        asignaciones=[Asignacion(empresa_id=e) for e in empresas],
    )


def armar(empresas_por_id, diagnosticos_por_empresa, asignadas):
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = consultor(asignadas)
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.side_effect = lambda i: empresas_por_id.get(i)
    repo_empresa.listar_todas.return_value = list(empresas_por_id.values())
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.side_effect = (
        lambda i: diagnosticos_por_empresa.get(i, [])
    )
    return repo_usuario, repo_empresa, repo_diagnostico


def escenario(n=3):
    ids = [f"e{i}" for i in range(n)]
    return (
        {i: empresa(i) for i in ids},
        {i: [diagnostico(i)] for i in ids},
        ids,
    )


@pytest.mark.asyncio
async def test_consultor_ve_indicadores_de_sus_empresas_asignadas():
    empresas, diagnosticos, ids = escenario(3)
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids))

    resultado = await caso_uso.ejecutar("c-1")

    assert resultado.detalle_disponible is True
    assert resultado.total_empresas == 3


@pytest.mark.asyncio
async def test_no_incluye_empresas_no_asignadas():
    empresas, diagnosticos, ids = escenario(4)
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids[:3]))

    assert (await caso_uso.ejecutar("c-1")).total_empresas == 3


@pytest.mark.asyncio
async def test_con_menos_de_tres_empresas_asignadas_no_hay_detalle():
    empresas, diagnosticos, ids = escenario(2)
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids))

    assert (await caso_uso.ejecutar("c-1")).detalle_disponible is False


@pytest.mark.asyncio
async def test_filtro_por_sector_con_menos_de_tres_oculta_detalle():
    empresas, diagnosticos, ids = escenario(3)
    empresas["e0"] = empresa("e0", sector="C10")
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids))

    resultado = await caso_uso.ejecutar("c-1", sector_codigo="C10")

    assert resultado.detalle_disponible is False


@pytest.mark.asyncio
async def test_usa_solo_el_diagnostico_mas_reciente_con_resultado():
    empresas, diagnosticos, ids = escenario(3)
    diagnosticos["e0"] = [
        diagnostico("e0", 1, indice="3", nivel=1),
        diagnostico("e0", 2, indice="9", nivel=4),
        diagnostico("e0", 3, estado="borrador"),
    ]
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids))

    resultado = await caso_uso.ejecutar("c-1")

    assert resultado.total_empresas == 3
    assert resultado.indice_promedio == Decimal("7.00")  # (9 + 6 + 6) / 3


@pytest.mark.asyncio
async def test_empresas_sin_resultado_no_cuentan():
    empresas, diagnosticos, ids = escenario(3)
    diagnosticos["e0"] = [diagnostico("e0", estado="borrador")]
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids))

    assert (await caso_uso.ejecutar("c-1")).detalle_disponible is False


@pytest.mark.asyncio
async def test_tamano_invalido_se_rechaza():
    empresas, diagnosticos, ids = escenario(3)
    caso_uso = ConsultarIndicadoresAgregados(*armar(empresas, diagnosticos, ids))

    with pytest.raises(FiltroInvalido):
        await caso_uso.ejecutar("c-1", tamano="gigante")


@pytest.mark.asyncio
async def test_exportacion_considera_todas_las_empresas():
    empresas, diagnosticos, ids = escenario(3)
    _, repo_empresa, repo_diagnostico = armar(empresas, diagnosticos, [])

    filas = await ExportarDatosAgregados(repo_empresa, repo_diagnostico).ejecutar()

    assert len(filas) == 1
    assert filas[0].empresas == 3


@pytest.mark.asyncio
async def test_exportacion_filtra_por_rango_de_fechas():
    empresas, diagnosticos, ids = escenario(3)
    _, repo_empresa, repo_diagnostico = armar(empresas, diagnosticos, [])
    manana = datetime.now(timezone.utc) + timedelta(days=1)

    filas = await ExportarDatosAgregados(repo_empresa, repo_diagnostico).ejecutar(
        fecha_desde=manana
    )

    assert filas == []
