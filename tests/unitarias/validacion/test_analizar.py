"""El flujo completo de la herramienta (datos sintéticos -> indicadores -> informe)."""

import json

import pytest

from scripts.validacion import analizar as an


@pytest.fixture
def carpeta(tmp_path):
    an.principal(["demo", "--carpeta", str(tmp_path)])
    return tmp_path


def test_el_analisis_calcula_todos_los_indicadores(carpeta):
    res = an.analizar(carpeta)

    assert res["sintetico"] is True
    assert len(res["casos"]) == 4
    conc = res["concordancia"]
    assert conc["n_casos"] == 4
    assert conc["veredicto"]["estado"].startswith("cumple")
    assert 0 <= conc["niveles"]["dentro_de_uno"] <= 1
    assert res["tiempo"]["reduccion_media_observado"] > 0.5
    assert 0 <= res["usabilidad"]["media"] <= 100
    assert res["recomendaciones"]["calificadas"] == 12
    assert res["avisos"] == []


def test_el_informe_html_marca_los_datos_sinteticos(carpeta):
    html = an.informe_html(an.analizar(carpeta))

    assert "DATOS SINTÉTICOS" in html
    assert html.count("<svg") == 2


def test_la_orden_analizar_escribe_resultados_e_informe(carpeta):
    an.principal(["analizar", "--carpeta", str(carpeta)])

    assert json.loads((carpeta / "resultados.json").read_text(encoding="utf-8"))[
        "concordancia"
    ]
    assert (carpeta / "informe.html").exists()


def test_con_menos_de_tres_casos_no_se_calcula_el_icc_y_se_avisa(carpeta):
    for nombre in ("sistema.csv", "experta.csv"):
        lineas = (carpeta / nombre).read_text(encoding="utf-8-sig").splitlines()
        (carpeta / nombre).write_text("\n".join(lineas[:3]), encoding="utf-8")

    res = an.analizar(carpeta)

    assert "veredicto" not in res["concordancia"]
    assert any("menos de 3 casos" in a for a in res["avisos"])


def test_avisa_si_se_mezclan_versiones_del_modelo_o_falta_la_experta(carpeta):
    filas = an.leer_csv(carpeta / "sistema.csv")
    filas[0]["modelo_version"] = "2026.2"
    an.escribir_csv(carpeta / "sistema.csv", list(filas[0]), filas)
    expertas = an.leer_csv(carpeta / "experta.csv")[:3]
    an.escribir_csv(carpeta / "experta.csv", list(expertas[0]), expertas)

    avisos = an.analizar(carpeta)["avisos"]

    assert any("más de una versión" in a for a in avisos)
    assert any("no tiene valoración de la experta" in a for a in avisos)


def test_las_plantillas_no_pisan_archivos_existentes(tmp_path, capsys):
    an.principal(["plantillas", "--carpeta", str(tmp_path)])
    (tmp_path / "sus.csv").write_text("participante\nP1\n", encoding="utf-8")
    an.principal(["plantillas", "--carpeta", str(tmp_path)])

    assert "P1" in (tmp_path / "sus.csv").read_text(encoding="utf-8")
    assert "se conserva" in capsys.readouterr().out


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *_):
        return self

    async def to_list(self, _):
        return self._docs


class _Coleccion:
    def __init__(self, docs):
        self._docs = docs

    def find(self, *_):
        return _Cursor(self._docs)

    async def find_one(self, filtro):
        return next(
            (d for d in self._docs if d.get("version") == filtro.get("version")), None
        )


def test_exportar_lee_los_diagnosticos_de_las_empresas_y_no_escribe_en_la_base(
    monkeypatch, tmp_path
):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from bson import Decimal128

    inicio = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)
    base = {
        "empresas": _Coleccion([{"_id": "e1", "nombre": "Caso A"}]),
        "diagnosticos": _Coleccion(
            [
                {
                    "_id": "d1",
                    "empresa_id": "e1",
                    "empresa_nombre": "Caso A",
                    "consecutivo": 1,
                    "modelo_version": "2026.2",
                    "estado": "evaluado",
                    "iniciado_en": inicio,
                    "completado_en": inicio + timedelta(minutes=30),
                    "evaluado_en": inicio + timedelta(minutes=42),
                    "resultado": {
                        "indice_global": Decimal128(Decimal("57.5")),
                        "nivel": 6,
                        "dimensiones": [
                            {
                                "codigo": "proposito",
                                "puntaje": Decimal128(Decimal("60")),
                            },
                            {
                                "codigo": "procesos",
                                "puntaje": Decimal128(Decimal("55")),
                            },
                        ],
                        "perfil_cultura": {"codigo": "ADH-CLN"},
                    },
                    "recomendaciones": [
                        {
                            "origen": "agente",
                            "titulo": "R1",
                            "dimension_codigo": "procesos",
                        },
                        {"origen": "consultor", "titulo": "R2"},
                    ],
                }
            ]
        ),
        "modelos_madurez": _Coleccion(
            [{"version": "2026.2", "niveles": [{"nivel": 6, "nombre": "Gestionado"}]}]
        ),
    }

    class FalsaBase:
        def __getitem__(self, nombre):
            return base[nombre]

    import src.infraestructura.persistencia.conexion as conexion

    monkeypatch.setattr(conexion, "obtener_base_datos", lambda: FalsaBase())

    an.principal(["exportar", "--empresas", "^Caso ", "--carpeta", str(tmp_path)])

    fila = an.leer_csv(tmp_path / "sistema.csv")[0]
    assert fila["caso"] == "Caso A"
    assert fila["minutos_hasta_informe"] == "42.0"
    assert fila["indice_global"] == "57.5"
    assert fila["nivel_nombre"] == "Gestionado"
    assert fila["puntaje_procesos"] == "55.0"
    assert (
        fila["recomendaciones_agente"] == "1"
        and fila["recomendaciones_consultor"] == "1"
    )
    assert len(an.leer_csv(tmp_path / "recomendaciones.csv")) == 2
