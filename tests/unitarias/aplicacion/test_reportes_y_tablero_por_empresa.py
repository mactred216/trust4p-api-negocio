from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.generar_informe import (
    DiagnosticoSinResultado, GenerarInformeDiagnostico)
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.aplicacion.casos_uso.gestionar_indicadores import (
    ConsultarIndicadoresAgregados, EmpresaFueraDeAlcance, FiltroInvalido)
from src.aplicacion.casos_uso.gestionar_reportes import \
    FiltroInvalido as FiltroReporteInvalido
from src.aplicacion.casos_uso.gestionar_reportes import (
    GenerarInformeDeEmpresa, ListarEmpresasParaReporte)
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario
from src.dominio.servicios.indicadores_agregados import (
    MuestraEmpresa, calcular_indicadores, calcular_indicadores_empresa)

# Informes y tablero por empresa: el administrador alcanza a todas; el consultor
# solo a las que tiene asignadas.


def empresa(id, nombre=None, sector="servicios", empleados=30):
    return Empresa(
        id=id,
        nombre=nombre or f"Empresa {id}",
        sector=Sector(id="s", codigo=sector, nombre=f"Sector {sector}"),
        numero_empleados=empleados,
    )


def diagnostico(empresa_id, consecutivo=1, estado="evaluado", nivel=2, indice="60"):
    d = Diagnostico(
        id=f"d-{empresa_id}-{consecutivo}",
        empresa_id=empresa_id,
        empresa_nombre=f"Empresa {empresa_id}",
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
            dimensiones=[
                DimensionResultado(codigo="proposito", puntaje=Decimal("70")),
                DimensionResultado(codigo="procesos", puntaje=Decimal("50")),
            ],
            perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
        )
    return d


def usuario(rol, asignadas=()):
    return Usuario(
        id=f"{rol}-1",
        correo=f"{rol}@trust4p.com",
        clave_hash="h",
        nombres="U",
        apellidos="U",
        rol=Rol(codigo=rol),
        asignaciones=[Asignacion(empresa_id=e) for e in asignadas],
    )


def repos(quien, empresas, diagnosticos):
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = quien
    repo_empresa = AsyncMock()
    por_id = {e.id: e for e in empresas}
    repo_empresa.obtener_por_id.side_effect = lambda i: por_id.get(i)
    repo_empresa.listar_activas.return_value = empresas
    repo_empresa.listar_todas.return_value = empresas
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.side_effect = lambda i: diagnosticos.get(i, [])
    repo_diagnostico.obtener_por_id.side_effect = lambda i: next(
        (d for ds in diagnosticos.values() for d in ds if d.id == i), None
    )
    return repo_usuario, repo_empresa, repo_diagnostico


# ---------------- Tablero ----------------


def cinco_empresas():
    empresas = [
        empresa("a", "Alfa SAS", sector="tecnologia", empleados=8),
        empresa("b", "Beta SAS", sector="tecnologia", empleados=40),
        empresa("c", "Gamma SAS", sector="servicios", empleados=120),
        empresa("d", "Delta SAS", sector="servicios", empleados=500),
        empresa("e", "Épsilon SAS", sector="fintech", empleados=25),
    ]
    return empresas, {
        e.id: [diagnostico(e.id, nivel=2 + i % 2, indice=str(50 + i * 5))]
        for i, e in enumerate(empresas)
    }


@pytest.mark.asyncio
async def test_el_administrador_ve_el_tablero_de_todas_las_empresas():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    r = await caso.ejecutar("administrador-1")

    assert r.ambito == "total"
    assert r.detalle_disponible is True
    assert r.total_empresas == 5


@pytest.mark.asyncio
async def test_el_consultor_solo_cuenta_las_empresas_que_tiene_asignadas():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("consultor", ["a", "b", "c"]), empresas, diag)
    )

    r = await caso.ejecutar("consultor-1")

    assert r.total_empresas == 3


@pytest.mark.asyncio
async def test_al_consultor_con_menos_de_tres_empresas_no_se_le_presenta_el_detalle():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("consultor", ["a", "b"]), empresas, diag)
    )

    r = await caso.ejecutar("consultor-1")

    assert r.detalle_disponible is False
    assert "confidencialidad" in r.mensaje


@pytest.mark.asyncio
async def test_al_administrador_el_tope_de_confidencialidad_no_le_aplica():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    r = await caso.ejecutar(
        "administrador-1", sector_codigo="fintech"
    )  # una sola empresa

    assert r.detalle_disponible is True
    assert r.total_empresas == 1


@pytest.mark.asyncio
async def test_administrador_filtra_por_sector_y_tamano():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    por_sector = await caso.ejecutar("administrador-1", sector_codigo="tecnologia")
    por_tamano = await caso.ejecutar("administrador-1", tamano="grande")

    assert por_sector.total_empresas == 2
    assert por_tamano.total_empresas == 1


@pytest.mark.asyncio
async def test_vista_de_una_empresa_muestra_sus_propios_resultados():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    r = await caso.ejecutar("administrador-1", empresa_id="c")

    assert r.ambito == "empresa"
    assert r.empresa_nombre == "Gamma SAS"
    assert r.total_empresas == 1
    assert r.promedio_por_dimension == {
        "procesos": Decimal("50.00"),
        "proposito": Decimal("70.00"),
    }


@pytest.mark.asyncio
async def test_el_consultor_ve_una_empresa_asignada_aunque_sea_una_sola():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("consultor", ["a"]), empresas, diag)
    )

    r = await caso.ejecutar("consultor-1", empresa_id="a")

    assert r.detalle_disponible is True
    assert r.ambito == "empresa"


@pytest.mark.asyncio
async def test_el_consultor_no_puede_ver_una_empresa_ajena():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("consultor", ["a"]), empresas, diag)
    )

    with pytest.raises(EmpresaFueraDeAlcance):
        await caso.ejecutar("consultor-1", empresa_id="e")


@pytest.mark.asyncio
async def test_empresa_inexistente_esta_fuera_de_alcance_tambien_para_el_administrador():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    with pytest.raises(EmpresaFueraDeAlcance):
        await caso.ejecutar("administrador-1", empresa_id="no-existe")


@pytest.mark.asyncio
async def test_empresa_sin_diagnostico_evaluado_lo_informa():
    empresas, diag = cinco_empresas()
    diag["a"] = [diagnostico("a", estado="borrador")]
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    r = await caso.ejecutar("administrador-1", empresa_id="a")

    assert r.detalle_disponible is False
    assert "aún no tiene un diagnóstico evaluado" in r.mensaje


@pytest.mark.asyncio
async def test_tamano_invalido_se_rechaza():
    empresas, diag = cinco_empresas()
    caso = ConsultarIndicadoresAgregados(
        *repos(usuario("administrador"), empresas, diag)
    )

    with pytest.raises(FiltroInvalido):
        await caso.ejecutar("administrador-1", tamano="gigante")


def test_dominio_sin_empresas_no_dice_que_es_por_confidencialidad():
    r = calcular_indicadores([], minimo=1)

    assert r.detalle_disponible is False
    assert "confidencialidad" not in r.mensaje


def test_dominio_vista_de_empresa_no_aplica_el_tope():
    muestra = MuestraEmpresa(
        sector_codigo="servicios",
        sector_nombre="Servicios",
        tamano="pequena",
        nivel=3,
        indice_global=Decimal("71.256"),
        puntajes_dimension={"a": Decimal("80")},
        empresa_id="x",
        empresa_nombre="X SAS",
    )

    r = calcular_indicadores_empresa(muestra)

    assert r.detalle_disponible and r.ambito == "empresa"
    assert r.indice_promedio == Decimal("71.26")
    assert [g.etiqueta for g in r.por_nivel] == ["Nivel 3"]


# ---------------- Empresas con informe ----------------


@pytest.mark.asyncio
async def test_administrador_ve_todas_las_empresas_ordenadas_por_nombre():
    empresas, diag = cinco_empresas()
    caso = ListarEmpresasParaReporte(*repos(usuario("administrador"), empresas, diag))

    r = await caso.ejecutar("administrador-1")

    assert [e.nombre for e in r] == [
        "Alfa SAS",
        "Beta SAS",
        "Delta SAS",
        "Gamma SAS",
        "Épsilon SAS",
    ]


@pytest.mark.asyncio
async def test_consultor_solo_ve_sus_empresas_asignadas():
    empresas, diag = cinco_empresas()
    caso = ListarEmpresasParaReporte(
        *repos(usuario("consultor", ["b", "d"]), empresas, diag)
    )

    r = await caso.ejecutar("consultor-1")

    assert {e.empresa_id for e in r} == {"b", "d"}


@pytest.mark.asyncio
async def test_filtra_por_nombre_sin_distinguir_mayusculas():
    empresas, diag = cinco_empresas()
    caso = ListarEmpresasParaReporte(*repos(usuario("administrador"), empresas, diag))

    r = await caso.ejecutar("administrador-1", nombre="  gamMA ")

    assert [e.empresa_id for e in r] == ["c"]


@pytest.mark.asyncio
async def test_filtra_por_sector_y_tamano_y_combina_con_el_nombre():
    empresas, diag = cinco_empresas()
    caso = ListarEmpresasParaReporte(*repos(usuario("administrador"), empresas, diag))

    por_sector = await caso.ejecutar("administrador-1", sector_codigo="tecnologia")
    por_tamano = await caso.ejecutar("administrador-1", tamano="micro")
    combinado = await caso.ejecutar(
        "administrador-1", sector_codigo="tecnologia", nombre="beta"
    )
    sin_coincidencia = await caso.ejecutar(
        "administrador-1", sector_codigo="fintech", nombre="beta"
    )

    assert {e.empresa_id for e in por_sector} == {"a", "b"}
    assert [e.empresa_id for e in por_tamano] == ["a"]
    assert [e.empresa_id for e in combinado] == ["b"]
    assert sin_coincidencia == []


@pytest.mark.asyncio
async def test_el_filtro_del_consultor_nunca_amplia_su_alcance():
    empresas, diag = cinco_empresas()
    caso = ListarEmpresasParaReporte(
        *repos(usuario("consultor", ["a"]), empresas, diag)
    )

    r = await caso.ejecutar("consultor-1", nombre="beta")  # Beta existe pero no es suya

    assert r == []


@pytest.mark.asyncio
async def test_solo_lista_diagnosticos_evaluados_o_cerrados_el_mas_reciente_primero():
    empresas = [empresa("a")]
    diag = {
        "a": [
            diagnostico("a", 1, "evaluado", indice="40"),
            diagnostico("a", 2, "borrador"),
            diagnostico("a", 3, "fallido"),
            diagnostico("a", 4, "cerrado", indice="80"),
        ]
    }
    caso = ListarEmpresasParaReporte(*repos(usuario("administrador"), empresas, diag))

    r = await caso.ejecutar("administrador-1")

    assert [d.consecutivo for d in r[0].diagnosticos] == [4, 1]
    assert r[0].tamano == "pequena"


@pytest.mark.asyncio
async def test_tamano_invalido_en_el_listado_se_rechaza():
    caso = ListarEmpresasParaReporte(*repos(usuario("administrador"), [], {}))

    with pytest.raises(FiltroReporteInvalido):
        await caso.ejecutar("administrador-1", tamano="x")


# ---------------- Descarga del informe ----------------


@pytest.mark.asyncio
async def test_administrador_descarga_el_informe_de_cualquier_empresa():
    empresas, diag = cinco_empresas()
    caso = GenerarInformeDeEmpresa(
        *[repos(usuario("administrador"), empresas, diag)[i] for i in (0, 2)]
    )

    d = await caso.ejecutar("administrador-1", "d-e-1")

    assert d.empresa_id == "e"


@pytest.mark.asyncio
async def test_consultor_descarga_solo_de_una_empresa_asignada():
    empresas, diag = cinco_empresas()
    r = repos(usuario("consultor", ["a"]), empresas, diag)
    caso = GenerarInformeDeEmpresa(r[0], r[2])

    assert (await caso.ejecutar("consultor-1", "d-a-1")).empresa_id == "a"
    with pytest.raises(AccesoNoAutorizado):
        await caso.ejecutar("consultor-1", "d-b-1")


@pytest.mark.asyncio
async def test_un_consultor_con_la_asignacion_finalizada_pierde_el_acceso():
    from datetime import datetime, timezone

    empresas, diag = cinco_empresas()
    quien = usuario("consultor", [])
    quien.asignaciones = [
        Asignacion(empresa_id="a", finalizado_en=datetime.now(timezone.utc))
    ]
    r = repos(quien, empresas, diag)

    with pytest.raises(AccesoNoAutorizado):
        await GenerarInformeDeEmpresa(r[0], r[2]).ejecutar("consultor-1", "d-a-1")


@pytest.mark.asyncio
async def test_informe_de_diagnostico_cerrado_se_puede_descargar_pero_no_el_borrador_ni_el_fallido():
    empresas = [empresa("a")]
    diag = {
        "a": [
            diagnostico("a", 1, "cerrado"),
            diagnostico("a", 2, "borrador"),
            diagnostico("a", 3, "fallido"),
        ]
    }
    r = repos(usuario("administrador"), empresas, diag)
    caso = GenerarInformeDeEmpresa(r[0], r[2])

    assert (await caso.ejecutar("administrador-1", "d-a-1")).estado == "cerrado"
    for id_ in ("d-a-2", "d-a-3"):
        with pytest.raises(DiagnosticoSinResultado):
            await caso.ejecutar("administrador-1", id_)


@pytest.mark.asyncio
async def test_diagnostico_inexistente_se_informa():
    r = repos(usuario("administrador"), [], {})

    with pytest.raises(DiagnosticoNoEncontrado):
        await GenerarInformeDeEmpresa(r[0], r[2]).ejecutar("administrador-1", "nada")


@pytest.mark.asyncio
async def test_el_representante_ahora_tambien_descarga_el_informe_de_su_diagnostico_cerrado():
    rep = usuario("representante")
    rep.empresa_id = "a"
    d = diagnostico("a", 1, "cerrado")
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = rep
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = d

    resultado = await GenerarInformeDiagnostico(
        repo_diagnostico, repo_usuario
    ).ejecutar("representante-1", d.id)

    assert resultado.estado == "cerrado"


@pytest.mark.asyncio
async def test_los_diagnosticos_fallidos_se_listan_aparte_y_no_como_informes():
    empresas = [empresa("a", "Alfa SAS")]
    diag = {
        "a": [
            diagnostico("a", consecutivo=1, estado="evaluado"),
            diagnostico("a", consecutivo=2, estado="fallido"),
            diagnostico("a", consecutivo=3, estado="completado"),
        ]
    }
    caso = ListarEmpresasParaReporte(*repos(usuario("administrador"), empresas, diag))

    [alfa] = await caso.ejecutar("administrador-1")

    assert [d.consecutivo for d in alfa.diagnosticos] == [1]
    assert [(f.id, f.consecutivo) for f in alfa.fallidos] == [("d-a-2", 2)]


@pytest.mark.asyncio
async def test_el_consultor_solo_ve_los_fallidos_de_sus_empresas():
    empresas = [empresa("a", "Alfa SAS"), empresa("b", "Beta SAS")]
    diag = {
        "a": [diagnostico("a", estado="fallido")],
        "b": [diagnostico("b", estado="fallido")],
    }
    caso = ListarEmpresasParaReporte(
        *repos(usuario("consultor", ["a"]), empresas, diag)
    )

    r = await caso.ejecutar("consultor-1")

    assert [(e.empresa_id, len(e.fallidos)) for e in r] == [("a", 1)]
