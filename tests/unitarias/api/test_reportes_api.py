from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (
    obtener_caso_uso_consultar_indicadores,
    obtener_caso_uso_generar_informe_de_empresa,
    obtener_caso_uso_listar_empresas_para_reporte,
    obtener_repositorio_auditoria, obtener_repositorio_sesion)
from src.api.main import app
from src.aplicacion.casos_uso.generar_informe import DiagnosticoSinResultado
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.aplicacion.casos_uso.gestionar_indicadores import \
    EmpresaFueraDeAlcance
from src.aplicacion.casos_uso.gestionar_reportes import (DiagnosticoDeReporte,
                                                         EmpresaDeReporte)
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.servicios.indicadores_agregados import IndicadoresAgregados


def sesion(rol, permisos):
    return {"usuario_id": f"{rol}-1", "rol_codigo": rol, "permisos": permisos}


def diagnostico_evaluado():
    d = Diagnostico(
        id="d-1",
        empresa_id="e-1",
        empresa_nombre="Alfa y Omega S.A.S.",
        usuario_id="u",
        modelo_version="1",
        consecutivo=2,
        estado="evaluado",
    )
    d.resultado = ResultadoDiagnostico(
        indice_global=Decimal("70"),
        nivel=3,
        nivel_descripcion="Sistemático",
        dimensiones=[DimensionResultado(codigo="a", puntaje=Decimal("70"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    return d


@pytest.fixture
def entorno():
    repo_sesion = AsyncMock()
    repo_auditoria = AsyncMock()
    app.dependency_overrides[obtener_repositorio_sesion] = lambda: repo_sesion
    app.dependency_overrides[obtener_repositorio_auditoria] = lambda: repo_auditoria
    cliente = TestClient(app, cookies={"sesion": "t"})
    yield cliente, repo_sesion, repo_auditoria
    app.dependency_overrides.clear()


def con_caso_de_uso(proveedor, resultado=None, error=None):
    caso = AsyncMock()
    if error:
        caso.ejecutar.side_effect = error
    else:
        caso.ejecutar.return_value = resultado
    app.dependency_overrides[proveedor] = lambda: caso
    return caso


def test_sin_sesion_no_se_listan_empresas():
    assert TestClient(app).get("/v1/reportes/empresas").status_code == 401


def test_el_representante_no_accede_a_los_reportes(entorno):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "representante", ["informes.descargar"]
    )

    assert cliente.get("/v1/reportes/empresas").status_code == 403
    assert cliente.get("/v1/reportes/diagnosticos/d-1/informe").status_code == 403


def test_un_consultor_sin_el_permiso_recibe_403(entorno):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion("consultor", [])

    assert cliente.get("/v1/reportes/empresas").status_code == 403


@pytest.mark.parametrize("rol", ["administrador", "consultor"])
def test_lista_empresas_con_filtros_para_cada_rol(entorno, rol):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        rol, ["informes.descargar"]
    )
    caso = con_caso_de_uso(
        obtener_caso_uso_listar_empresas_para_reporte,
        [
            EmpresaDeReporte(
                empresa_id="e-1",
                nombre="Alfa",
                nit="900",
                sector_codigo="servicios",
                sector_nombre="Servicios",
                numero_empleados=30,
                tamano="pequena",
                diagnosticos=[
                    DiagnosticoDeReporte(
                        id="d-1",
                        consecutivo=2,
                        estado="evaluado",
                        nivel=3,
                        indice_global=Decimal("70"),
                        evaluado_en=None,
                    )
                ],
            )
        ],
    )

    r = cliente.get("/v1/reportes/empresas?nombre=alf&sector=servicios&tamano=pequena")

    assert r.status_code == 200
    assert r.json()[0]["diagnosticos"][0]["id"] == "d-1"
    caso.ejecutar.assert_awaited_once_with(
        f"{rol}-1", nombre="alf", sector_codigo="servicios", tamano="pequena"
    )


def test_descarga_el_pdf_y_deja_constancia_en_la_bitacora(entorno):
    cliente, repo_sesion, repo_auditoria = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "administrador", ["informes.descargar"]
    )
    con_caso_de_uso(obtener_caso_uso_generar_informe_de_empresa, diagnostico_evaluado())

    r = cliente.get("/v1/reportes/diagnosticos/d-1/informe")

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    nombre = r.headers["content-disposition"]
    assert "Alfa-y-Omega" in nombre and "diagnostico-2" in nombre and ".pdf" in nombre
    repo_auditoria.registrar.assert_awaited()
    registro = repo_auditoria.registrar.await_args.args[0]
    assert registro.usuario_id == "administrador-1"
    assert registro.valores_nuevos["accion"] == "descargar_informe"


def test_un_consultor_sin_asignacion_recibe_403_y_queda_registrado(entorno):
    cliente, repo_sesion, repo_auditoria = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "consultor", ["informes.descargar"]
    )
    con_caso_de_uso(
        obtener_caso_uso_generar_informe_de_empresa, error=AccesoNoAutorizado()
    )

    r = cliente.get("/v1/reportes/diagnosticos/d-9/informe")

    assert r.status_code == 403
    registro = repo_auditoria.registrar.await_args.args[0]
    assert registro.valores_nuevos["acceso"] == "denegado"


@pytest.mark.parametrize(
    "error,estado",
    [(DiagnosticoNoEncontrado(), 404), (DiagnosticoSinResultado(), 409)],
)
def test_errores_del_informe(entorno, error, estado):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "administrador", ["informes.descargar"]
    )
    con_caso_de_uso(obtener_caso_uso_generar_informe_de_empresa, error=error)

    assert cliente.get("/v1/reportes/diagnosticos/d-1/informe").status_code == estado


@pytest.mark.parametrize("rol", ["administrador", "consultor"])
def test_ambos_roles_consultan_el_tablero_y_pueden_filtrar_por_empresa(entorno, rol):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        rol, ["indicadores.consultar"]
    )
    caso = con_caso_de_uso(
        obtener_caso_uso_consultar_indicadores,
        IndicadoresAgregados(
            detalle_disponible=True,
            ambito="empresa",
            empresa_nombre="Alfa",
            total_empresas=1,
        ),
    )

    r = cliente.get("/v1/indicadores/agregados?empresa_id=e-1")

    assert r.status_code == 200
    assert r.json()["ambito"] == "empresa" and r.json()["empresa_nombre"] == "Alfa"
    caso.ejecutar.assert_awaited_once_with(
        f"{rol}-1", sector_codigo=None, tamano=None, empresa_id="e-1"
    )


def test_empresa_fuera_del_alcance_en_el_tablero_responde_403(entorno):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "consultor", ["indicadores.consultar"]
    )
    con_caso_de_uso(
        obtener_caso_uso_consultar_indicadores, error=EmpresaFueraDeAlcance()
    )

    assert cliente.get("/v1/indicadores/agregados?empresa_id=ajena").status_code == 403


def test_el_representante_no_ve_el_tablero(entorno):
    cliente, repo_sesion, _ = entorno
    repo_sesion.obtener_sesion_por_token.return_value = sesion(
        "representante", ["indicadores.consultar"]
    )

    assert cliente.get("/v1/indicadores/agregados").status_code == 403
