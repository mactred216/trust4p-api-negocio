from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencias import (obtener_repositorio_auditoria,
                                  obtener_repositorio_diagnostico,
                                  obtener_repositorio_modelo_madurez,
                                  obtener_repositorio_notificacion,
                                  obtener_repositorio_sesion,
                                  obtener_repositorio_usuario,
                                  obtener_servicio_correo)
from src.api.main import app
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               Recomendacion,
                                               ResultadoDiagnostico)
from src.dominio.entidades.modelo_madurez import ModeloMadurez, Nivel
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario

BASE = "/v1/consultoria/diagnosticos/d-1"


def consultor(empresas=("emp-1",)):
    return Usuario(
        id="c-1", correo="julia@x.com", clave_hash="h", nombres="Julia", apellidos="Herrera",
        rol=Rol(codigo="consultor"), asignaciones=[Asignacion(empresa_id=e) for e in empresas],
    )


def representante():
    return Usuario(
        id="u-1", correo="ana@innovatech.com", clave_hash="h", nombres="Ana", apellidos="Pérez",
        rol=Rol(codigo="representante"), empresa_id="emp-1",
    )


def modelo():
    m = ModeloMadurez(id="m", version="2026.2", nombre="M", escala_min=0, escala_max=100)
    m.niveles = [
        Nivel(nivel=i, nombre=f"Nivel {i}", descripcion="d", umbral_min=Decimal(i * 10 - 10), umbral_max=Decimal(i * 10))
        for i in range(1, 11)
    ]
    return m


def diagnostico_con(tareas, estado="evaluado"):
    d = Diagnostico(
        id="d-1", empresa_id="emp-1", empresa_nombre="InnovaTech", usuario_id="u-1",
        modelo_version="2026.2", consecutivo=1, estado=estado,
    )
    d.resultado = ResultadoDiagnostico(
        indice_global=Decimal("25"), nivel=3, nivel_descripcion="x",
        dimensiones=[DimensionResultado(codigo="proposito", puntaje=Decimal("30"))],
        perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
    )
    d.recomendaciones = tareas
    return d


def tarea(titulo="Capacitar al equipo", estado="pendiente", nivel_objetivo=4):
    return Recomendacion(origen="agente", titulo=titulo, contenido="Detalle", estado=estado, nivel_objetivo=nivel_objetivo)


@pytest.fixture
def entorno():
    estado = {"diagnostico": diagnostico_con([tarea()])}
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.side_effect = lambda _id: estado["diagnostico"]
    repo_usuario = AsyncMock()
    estado["consultor"] = consultor()
    repo_usuario.obtener_por_id.side_effect = lambda id_: {"c-1": estado["consultor"], "u-1": representante()}.get(id_)
    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = modelo()
    repo_sesion = AsyncMock()
    estado["sesion"] = {"usuario_id": "c-1", "rol_codigo": "consultor", "permisos": ["recomendaciones.registrar"]}
    repo_sesion.obtener_sesion_por_token.side_effect = lambda _t: estado["sesion"]
    repo_auditoria = AsyncMock()
    correo = AsyncMock()
    app.dependency_overrides.update({
        obtener_repositorio_diagnostico: lambda: repo_diagnostico,
        obtener_repositorio_usuario: lambda: repo_usuario,
        obtener_repositorio_modelo_madurez: lambda: repo_modelo,
        obtener_repositorio_sesion: lambda: repo_sesion,
        obtener_repositorio_auditoria: lambda: repo_auditoria,
        obtener_repositorio_notificacion: lambda: AsyncMock(),
        obtener_servicio_correo: lambda: correo,
    })
    yield TestClient(app, cookies={"sesion": "t"}), estado, repo_auditoria, correo
    app.dependency_overrides.clear()


def id_de_la_tarea(estado):
    return estado["diagnostico"].recomendaciones[0].id


# ---------- editar ----------


def test_el_consultor_cambia_estado_fecha_y_nivel_de_una_tarea(entorno):
    cliente, estado, _, _ = entorno

    r = cliente.patch(
        f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}",
        json={"estado": "en_curso", "fecha_limite": "2026-12-01", "nivel_objetivo": 5},
    )

    assert r.status_code == 200
    cuerpo = r.json()
    assert (cuerpo["estado"], cuerpo["fecha_limite"], cuerpo["nivel_objetivo"]) == ("en_curso", "2026-12-01", 5)


def test_completar_registra_cuando_y_la_fecha_limite_se_puede_quitar(entorno):
    cliente, estado, _, _ = entorno
    url = f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}"
    cliente.patch(url, json={"fecha_limite": "2026-12-01"})

    r = cliente.patch(url, json={"estado": "completada", "fecha_limite": None})

    assert r.json()["completada_en"] is not None
    assert r.json()["fecha_limite"] is None


def test_un_null_en_los_demas_campos_significa_no_cambiar(entorno):
    cliente, estado, _, _ = entorno

    r = cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json={"titulo": None, "estado": "completada"})

    assert r.status_code == 200 and r.json()["titulo"] == "Capacitar al equipo"


def test_la_bitacora_registra_el_antes_y_el_despues_de_cada_campo_y_cual_tarea(entorno):
    cliente, estado, repo_auditoria, _ = entorno

    cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json={"estado": "completada", "fecha_limite": "2026-12-01"})

    registro = repo_auditoria.registrar.await_args.args[0]
    assert registro.entidad == "diagnosticos" and registro.entidad_id == "d-1"
    assert registro.valores_anteriores == {
        "tarea_id": id_de_la_tarea(estado), "tarea": "Capacitar al equipo",
        "estado": "pendiente", "fecha_limite": None,
    }
    assert registro.valores_nuevos == {
        "tarea_id": id_de_la_tarea(estado), "tarea": "Capacitar al equipo",
        "estado": "completada", "fecha_limite": "2026-12-01",
    }


@pytest.mark.parametrize(
    "cuerpo",
    [{"estado": "terminada"}, {"titulo": "  "}, {"nivel_objetivo": 0}, {"fecha_limite": "no-es-fecha"}],
)
def test_datos_invalidos_responden_422(entorno, cuerpo):
    cliente, estado, _, _ = entorno

    assert cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json=cuerpo).status_code == 422


def test_un_nivel_fuera_de_rango_responde_400_con_el_motivo(entorno):
    cliente, estado, _, _ = entorno

    r = cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json={"nivel_objetivo": 11})

    assert r.status_code == 400 and "nivel máximo" in r.json()["detail"]


def test_una_tarea_o_un_diagnostico_inexistentes_responden_404(entorno):
    cliente, estado, _, _ = entorno

    assert cliente.patch(f"{BASE}/recomendaciones/no-existe", json={"estado": "completada"}).status_code == 404
    estado["diagnostico"] = None
    assert cliente.patch(f"{BASE}/recomendaciones/x", json={"estado": "completada"}).status_code == 404


def test_un_diagnostico_cerrado_no_se_modifica(entorno):
    cliente, estado, _, _ = entorno
    estado["diagnostico"] = diagnostico_con([tarea()], estado="cerrado")

    r = cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json={"estado": "completada"})

    assert r.status_code == 400 and "cerrado" in r.json()["detail"]


def test_sin_asignacion_vigente_responde_403_y_queda_en_la_bitacora(entorno):
    cliente, estado, repo_auditoria, _ = entorno
    estado["consultor"] = consultor(empresas=("otra",))

    r = cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json={"estado": "completada"})

    assert r.status_code == 403
    assert repo_auditoria.registrar.await_args.args[0].valores_nuevos == {"acceso": "denegado"}


@pytest.mark.parametrize("rol", ["representante", "administrador"])
def test_solo_el_consultor_gestiona_las_tareas(entorno, rol):
    cliente, estado, _, _ = entorno
    estado["sesion"] = {"usuario_id": "x", "rol_codigo": rol, "permisos": ["recomendaciones.registrar"]}

    r = cliente.patch(f"{BASE}/recomendaciones/{id_de_la_tarea(estado)}", json={"estado": "completada"})

    assert r.status_code == 403


# ---------- agregar ----------


def test_agregar_una_tarea_con_fecha_y_nivel(entorno):
    cliente, _, _, _ = entorno

    r = cliente.post(
        f"{BASE}/recomendaciones",
        json={"titulo": "Definir un comité", "contenido": "Detalle", "fecha_limite": "2026-12-15", "nivel_objetivo": 5},
    )

    assert r.status_code == 201
    cuerpo = r.json()
    assert (cuerpo["fecha_limite"], cuerpo["nivel_objetivo"], cuerpo["estado"]) == ("2026-12-15", 5, "pendiente")
    assert cuerpo["id"]


def test_agregar_sin_nivel_apunta_al_siguiente_de_la_empresa(entorno):
    cliente, _, _, _ = entorno

    r = cliente.post(f"{BASE}/recomendaciones", json={"titulo": "T", "contenido": "c"})

    assert r.json()["nivel_objetivo"] == 4


# ---------- avanzar de nivel ----------


def test_confirmar_el_nivel_cuando_las_tareas_estan_completadas(entorno):
    cliente, estado, repo_auditoria, correo = entorno
    estado["diagnostico"] = diagnostico_con([tarea("A", "completada"), tarea("B", "completada")])

    r = cliente.post(f"{BASE}/avanzar-nivel")

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["nivel_alcanzado"] == 4
    assert [a["nivel"] for a in cuerpo["avances_de_nivel"]] == [4]
    assert cuerpo["avances_de_nivel"][0]["consultor_nombre"] == "Julia Herrera"
    assert cuerpo["nuevo_diagnostico_recomendado"] is False
    registro = repo_auditoria.registrar.await_args.args[0]
    assert (registro.valores_anteriores, registro.valores_nuevos) == ({"nivel_alcanzado": 3}, {"nivel_alcanzado": 4})
    correo.enviar.assert_awaited_once()


def test_si_faltan_tareas_responde_400_con_cuantas(entorno):
    cliente, estado, _, correo = entorno
    estado["diagnostico"] = diagnostico_con([tarea("A", "completada"), tarea("B", "pendiente")])

    r = cliente.post(f"{BASE}/avanzar-nivel")

    assert r.status_code == 400 and "Faltan 1 de 2 tareas" in r.json()["detail"]
    correo.enviar.assert_not_awaited()


def test_tras_dos_niveles_se_recomienda_un_nuevo_diagnostico(entorno):
    cliente, estado, _, _ = entorno
    estado["diagnostico"] = diagnostico_con([tarea("A", "completada", 4), tarea("B", "completada", 5)])

    cliente.post(f"{BASE}/avanzar-nivel")
    r = cliente.post(f"{BASE}/avanzar-nivel")

    assert r.json()["nivel_alcanzado"] == 5
    assert r.json()["nuevo_diagnostico_recomendado"] is True
    assert r.json()["niveles_para_nuevo_diagnostico"] == 2


def test_avanzar_sin_asignacion_responde_403(entorno):
    cliente, estado, _, _ = entorno
    estado["consultor"] = consultor(empresas=("otra",))

    assert cliente.post(f"{BASE}/avanzar-nivel").status_code == 403


# ---------- lo que ve la empresa ----------


def test_la_empresa_ve_el_estado_la_fecha_y_el_nivel_de_cada_tarea_pero_no_las_ocultas(entorno):
    cliente, estado, _, _ = entorno
    oculta = tarea("Borrador")
    oculta.visible = False
    estado["diagnostico"] = diagnostico_con([tarea("Visible", "en_curso"), oculta])
    estado["sesion"] = {"usuario_id": "u-1", "rol_codigo": "representante", "permisos": ["resultados.consultar"]}

    r = cliente.get("/v1/diagnosticos/d-1")

    assert r.status_code == 200
    tareas = r.json()["recomendaciones"]
    assert [t["titulo"] for t in tareas] == ["Visible"]
    assert (tareas[0]["estado"], tareas[0]["nivel_objetivo"]) == ("en_curso", 4)
