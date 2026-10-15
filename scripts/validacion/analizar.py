"""Herramienta de la validación QA/QC del cuarto objetivo.

Cuatro órdenes:

  exportar   Lee (solo lectura) los diagnósticos de las empresas indicadas y
             escribe sistema.csv con tiempos, índice, nivel y puntajes.
  plantillas Escribe los CSV vacíos donde se transcriben los formatos de papel.
  analizar   Cruza los CSV, calcula los indicadores del objetivo 4 y escribe
             resultados.json e informe.html (con gráficos).
  demo       Genera datos SINTÉTICOS para probar el flujo completo.

Uso (desde la raíz del repositorio de la API, con el entorno virtual activo):

  python -m scripts.validacion.analizar plantillas --carpeta validacion_datos
  python -m scripts.validacion.analizar exportar --empresas "^Caso " --carpeta validacion_datos
  python -m scripts.validacion.analizar analizar --carpeta validacion_datos

Ver docs/validacion/herramienta_validacion.md para los formatos de cada CSV."""

import argparse
import asyncio
import csv
import html
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.validacion import estadistica as est

META_ICC = 0.70
CALIFICACIONES = {"util": "Útil", "parcial": "Parcialmente útil", "no_util": "No útil"}
RESULTADOS_TAREA = ("exito", "con_ayuda", "fallo")
UMBRAL_SUS = 68.0  # Sauro (2011): promedio de referencia del SUS.


# ------------------------------------------------------------------------ CSV
def leer_csv(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        return [
            {k.strip(): (v or "").strip() for k, v in fila.items() if k}
            for fila in csv.DictReader(f)
            if any((v or "").strip() for v in fila.values())
        ]


def escribir_csv(ruta: Path, columnas: list[str], filas: list[dict]) -> None:
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def numero(texto: str) -> Optional[float]:
    texto = (texto or "").strip().replace(",", ".")
    try:
        return float(texto) if texto else None
    except ValueError:
        return None


def dimensiones_de(filas: list[dict]) -> list[str]:
    if not filas:
        return []
    return [c[len("puntaje_") :] for c in filas[0] if c.startswith("puntaje_")]


# -------------------------------------------------------------------- exportar
async def _exportar(patron: str, carpeta: Path) -> None:
    from dotenv import load_dotenv

    load_dotenv()
    from src.infraestructura.persistencia.conexion import obtener_base_datos

    db = obtener_base_datos()
    empresas = await db["empresas"].find({"nombre": {"$regex": patron}}).to_list(None)
    if not empresas:
        raise SystemExit(f"Ninguna empresa coincide con el patrón {patron!r}")
    ids = [str(e["_id"]) for e in empresas]
    docs = (
        await db["diagnosticos"]
        .find({"empresa_id": {"$in": ids}})
        .sort([("empresa_nombre", 1), ("consecutivo", 1)])
        .to_list(None)
    )

    def dec(v):
        return (
            float(v.to_decimal())
            if hasattr(v, "to_decimal")
            else (None if v is None else float(v))
        )

    def minutos(a, b):
        if not a or not b:
            return None
        return round((b - a).total_seconds() / 60.0, 1)

    niveles: dict[str, dict[int, str]] = {}
    filas, recs = [], []
    for d in docs:
        version = d["modelo_version"]
        if version not in niveles:
            modelo = await db["modelos_madurez"].find_one({"version": version}) or {}
            niveles[version] = {
                n["nivel"]: n["nombre"] for n in modelo.get("niveles", [])
            }
        r = d.get("resultado") or {}
        fila = {
            "caso": d["empresa_nombre"],
            "diagnostico_id": str(d["_id"]),
            "consecutivo": d["consecutivo"],
            "modelo_version": version,
            "estado": d["estado"],
            "iniciado_en": d["iniciado_en"].isoformat() if d.get("iniciado_en") else "",
            "completado_en": (
                d["completado_en"].isoformat() if d.get("completado_en") else ""
            ),
            "evaluado_en": d["evaluado_en"].isoformat() if d.get("evaluado_en") else "",
            "minutos_hasta_informe": minutos(
                d.get("iniciado_en"), d.get("evaluado_en")
            ),
            "indice_global": dec(r.get("indice_global")),
            "nivel": r.get("nivel"),
            "nivel_nombre": niveles[version].get(r.get("nivel"), ""),
            "perfil_cultura": (r.get("perfil_cultura") or {}).get("codigo", ""),
            "recomendaciones_agente": sum(
                1 for x in d.get("recomendaciones", []) if x.get("origen") == "agente"
            ),
            "recomendaciones_consultor": sum(
                1
                for x in d.get("recomendaciones", [])
                if x.get("origen") == "consultor"
            ),
        }
        for dim in r.get("dimensiones", []):
            fila[f"puntaje_{dim['codigo']}"] = dec(dim.get("puntaje"))
        filas.append(fila)
        for x in d.get("recomendaciones", []):
            recs.append(
                {
                    "caso": d["empresa_nombre"],
                    "recomendacion": x.get("titulo", ""),
                    "origen": x.get("origen", ""),
                    "dimension": x.get("dimension_codigo") or "",
                    "calificacion": "",
                }
            )

    columnas = list(dict.fromkeys(c for f in filas for c in f))
    carpeta.mkdir(parents=True, exist_ok=True)
    escribir_csv(carpeta / "sistema.csv", columnas, filas)
    if not (carpeta / "recomendaciones.csv").exists():
        escribir_csv(
            carpeta / "recomendaciones.csv",
            ["caso", "recomendacion", "origen", "dimension", "calificacion"],
            recs,
        )
    versiones = sorted({f["modelo_version"] for f in filas})
    print(
        f"{len(filas)} diagnóstico(s) de {len(empresas)} empresa(s) → {carpeta / 'sistema.csv'}"
    )
    print(
        f"Versiones del modelo usadas: {', '.join(versiones)}",
        "(¡más de una! la comparación no es homogénea)" if len(versiones) > 1 else "",
    )
    print(
        f"Recomendaciones listadas para calificar: {len(recs)} (columna 'calificacion': util | parcial | no_util)"
    )


# ------------------------------------------------------------------ plantillas
def _plantillas(carpeta: Path, dimensiones: list[str]) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    dims = [f"puntaje_{d}" for d in dimensiones]
    plan = {
        "experta.csv": [
            "caso",
            "indice_experta",
            "nivel_experta",
            *dims,
            "prioridad_1",
            "prioridad_2",
            "prioridad_3",
        ],
        "tiempos.csv": ["caso", "minutos_manual", "minutos_sistema_observado"],
        "recomendaciones.csv": [
            "caso",
            "recomendacion",
            "origen",
            "dimension",
            "calificacion",
        ],
        "sus.csv": ["participante", "rol", *[f"i{n}" for n in range(1, 11)]],
        "tareas.csv": ["participante", "rol", "tarea", "resultado"],
    }
    for nombre, cols in plan.items():
        ruta = carpeta / nombre
        if ruta.exists():
            print(f"(se conserva) {ruta}")
            continue
        escribir_csv(ruta, cols, [])
        print(f"creado {ruta}")


# -------------------------------------------------------------------- análisis
def _por_caso(filas: list[dict], clave: str = "caso") -> dict[str, dict]:
    return {f[clave]: f for f in filas if f.get(clave)}


def analizar(carpeta: Path) -> dict:
    sistema = leer_csv(carpeta / "sistema.csv")
    experta = leer_csv(carpeta / "experta.csv")
    tiempos = leer_csv(carpeta / "tiempos.csv")
    recs = leer_csv(carpeta / "recomendaciones.csv")
    sus = leer_csv(carpeta / "sus.csv")
    tareas = leer_csv(carpeta / "tareas.csv")

    avisos: list[str] = []
    res: dict = {
        "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sintetico": (carpeta / "sintetico.flag").exists(),
        "avisos": avisos,
    }

    s_caso = {}
    for f in sistema:
        if f["caso"] in s_caso:
            avisos.append(
                f"El caso {f['caso']!r} tiene más de un diagnóstico; se usa el de mayor consecutivo."
            )
        s_caso[f["caso"]] = f
    versiones = sorted(
        {
            f.get("modelo_version", "")
            for f in s_caso.values()
            if f.get("modelo_version")
        }
    )
    res["versiones_modelo"] = versiones
    if len(versiones) > 1:
        avisos.append(
            "Los casos se evaluaron con más de una versión del modelo: la comparación no es homogénea."
        )
    for f in s_caso.values():
        if f.get("estado") not in ("evaluado", "cerrado"):
            avisos.append(
                f"El caso {f['caso']!r} está en estado {f.get('estado')!r}: no tiene resultado final."
            )

    e_caso = _por_caso(experta)
    pares = [
        c
        for c in s_caso
        if c in e_caso
        and numero(s_caso[c].get("indice_global")) is not None
        and numero(e_caso[c].get("indice_experta")) is not None
    ]
    res["casos"] = sorted(pares)
    for c in s_caso:
        if c not in e_caso:
            avisos.append(f"El caso {c!r} no tiene valoración de la experta.")
    for c in e_caso:
        if c not in s_caso:
            avisos.append(
                f"La experta valoró {c!r}, que no tiene diagnóstico del sistema."
            )

    # ---- Concordancia (KPI 2)
    if pares:
        pares = sorted(pares)
        glob_s = [numero(s_caso[c]["indice_global"]) for c in pares]
        glob_e = [numero(e_caso[c]["indice_experta"]) for c in pares]
        conc: dict = {"n_casos": len(pares), "meta": META_ICC}
        conc["global"] = {
            "pares": [
                {"caso": c, "sistema": a, "experta": b}
                for c, a, b in zip(pares, glob_s, glob_e)
            ],
            "bland_altman": (
                est.sesgo_y_limites(glob_s, glob_e) if len(pares) >= 2 else None
            ),
        }
        if len(pares) >= 3:
            icc_g = est.icc([[a, b] for a, b in zip(glob_s, glob_e)])
            conc["global"]["icc"] = icc_g
            ref = icc_g["formas"].get("ICC2")
            if ref:
                conc["veredicto"] = _veredicto(ref)
        else:
            avisos.append("Con menos de 3 casos no se puede calcular el ICC.")

        dims = dimensiones_de(sistema)
        sd, ed = [], []
        for c in pares:
            for d in dims:
                a, b = numero(s_caso[c].get(f"puntaje_{d}")), numero(
                    e_caso[c].get(f"puntaje_{d}")
                )
                if a is not None and b is not None:
                    sd.append(a), ed.append(b)
        if len(sd) >= 3 and len(sd) == len(pares) * len(dims):
            conc["dimensiones"] = {
                "n_puntos": len(sd),
                "icc": est.icc([[a, b] for a, b in zip(sd, ed)]),
                "nota": "Los puntos de un mismo caso no son independientes: es un análisis secundario.",
            }

        niv_s = [
            int(numero(s_caso[c].get("nivel")))
            for c in pares
            if numero(s_caso[c].get("nivel")) is not None
        ]
        niv_e = [
            int(numero(e_caso[c].get("nivel_experta")))
            for c in pares
            if numero(e_caso[c].get("nivel_experta")) is not None
        ]
        if len(niv_s) == len(niv_e) == len(pares):
            escala = max(10, max(niv_s + niv_e))
            conc["niveles"] = {
                "coinciden": est.proporcion_de_acuerdo(niv_s, niv_e, 0),
                "dentro_de_uno": est.proporcion_de_acuerdo(niv_s, niv_e, 1),
                "kappa_ponderado": est.kappa_ponderado(niv_s, niv_e, escala, "lineal"),
                "spearman": est.spearman(glob_s, glob_e) if len(pares) >= 3 else None,
                "pares": [
                    {"caso": c, "sistema": a, "experta": b}
                    for c, a, b in zip(pares, niv_s, niv_e)
                ],
            }

        # Prioridades: ¿la dimensión más débil del sistema está entre las prioridades de la experta?
        prior = []
        for c in pares:
            puntajes = {d: numero(s_caso[c].get(f"puntaje_{d}")) for d in dims}
            puntajes = {d: v for d, v in puntajes.items() if v is not None}
            if not puntajes:
                continue
            debil = min(puntajes, key=puntajes.get)
            ps = [e_caso[c].get(f"prioridad_{i}", "") for i in (1, 2, 3)]
            ps = [p for p in ps if p]
            if ps:
                prior.append(
                    {
                        "caso": c,
                        "dimension_mas_debil_sistema": debil,
                        "prioridades_experta": ps,
                        "coincide": debil in ps,
                        "coincide_con_la_primera": debil == ps[0],
                    }
                )
        if prior:
            conc["prioridades"] = {
                "casos": prior,
                "coincide": sum(p["coincide"] for p in prior) / len(prior),
                "coincide_con_la_primera": sum(
                    p["coincide_con_la_primera"] for p in prior
                )
                / len(prior),
            }
        res["concordancia"] = conc

    # ---- Tiempo (KPI 1)
    t_caso = _por_caso(tiempos)
    filas_t = []
    for c, t in t_caso.items():
        man = numero(t.get("minutos_manual"))
        bd = numero(s_caso.get(c, {}).get("minutos_hasta_informe"))
        obs = numero(t.get("minutos_sistema_observado"))
        if man is None:
            avisos.append(
                f"El caso {c!r} no tiene tiempo manual: no se calcula la reducción."
            )
            continue
        fila = {
            "caso": c,
            "minutos_manual": man,
            "minutos_sistema_bd": bd,
            "minutos_sistema_observado": obs,
        }
        if bd is not None:
            fila["reduccion_bd"] = est.reduccion_de_tiempo(man, bd)
        if obs is not None:
            fila["reduccion_observado"] = est.reduccion_de_tiempo(man, obs)
        filas_t.append(fila)
    if filas_t:

        def media(k):
            v = [f[k] for f in filas_t if k in f]
            return sum(v) / len(v) if v else None

        res["tiempo"] = {
            "casos": filas_t,
            "reduccion_media_bd": media("reduccion_bd"),
            "reduccion_media_observado": media("reduccion_observado"),
            "nota": "El tiempo de la BD va desde la apertura hasta el informe e incluye pausas de quien responde; "
            "el observado cuenta solo el tiempo activo. Se reportan ambos.",
        }

    # ---- Calidad de las recomendaciones
    calif = [r for r in recs if r.get("calificacion")]
    if calif:
        invalidas = [r for r in calif if r["calificacion"] not in CALIFICACIONES]
        if invalidas:
            avisos.append(
                f"{len(invalidas)} calificación(es) de recomendaciones no son util/parcial/no_util y se ignoran."
            )
        calif = [r for r in calif if r["calificacion"] in CALIFICACIONES]
        n = len(calif)
        if n:
            cuenta = {
                k: sum(1 for r in calif if r["calificacion"] == k)
                for k in CALIFICACIONES
            }
            res["recomendaciones"] = {
                "calificadas": n,
                "total_listadas": len(recs),
                "conteo": cuenta,
                "porcentaje_util": cuenta["util"] / n,
                "porcentaje_util_o_parcial": (cuenta["util"] + cuenta["parcial"]) / n,
            }

    # ---- Usabilidad
    puntajes = []
    for s in sus:
        try:
            p = est.puntaje_sus(
                [int(numero(s.get(f"i{i}")) or 0) for i in range(1, 11)]
            )
        except ValueError:
            avisos.append(
                f"El SUS del participante {s.get('participante')!r} está incompleto o fuera de rango."
            )
            continue
        puntajes.append(
            {
                "participante": s.get("participante", ""),
                "rol": s.get("rol", ""),
                "sus": p,
            }
        )
    if puntajes:
        vals = [p["sus"] for p in puntajes]
        res["usabilidad"] = {
            "participantes": puntajes,
            "media": sum(vals) / len(vals),
            "minimo": min(vals),
            "maximo": max(vals),
            "referencia": UMBRAL_SUS,
            "supera_referencia": sum(vals) / len(vals) >= UMBRAL_SUS,
        }
    if tareas:
        validas = [t for t in tareas if t.get("resultado") in RESULTADOS_TAREA]
        if validas:
            por_tarea: dict[str, list[str]] = {}
            for t in validas:
                por_tarea.setdefault(t.get("tarea", ""), []).append(t["resultado"])
            res["tareas"] = {
                "intentos": len(validas),
                "exito_sin_ayuda": sum(1 for t in validas if t["resultado"] == "exito")
                / len(validas),
                "por_tarea": {
                    k: {
                        "exito": v.count("exito"),
                        "con_ayuda": v.count("con_ayuda"),
                        "fallo": v.count("fallo"),
                    }
                    for k, v in por_tarea.items()
                },
            }
    return res


def _veredicto(ref: dict) -> dict:
    estimado, inferior = ref["estimado"], ref["inferior"]
    if estimado >= META_ICC and inferior is not None and inferior >= META_ICC:
        estado = "cumple con evidencia robusta"
    elif estimado >= META_ICC:
        estado = "cumple con evidencia limitada"
    else:
        estado = "no cumple"
    return {
        "estado": estado,
        "estimado": estimado,
        "inferior": inferior,
        "superior": ref["superior"],
        "interpretacion": (
            est.clasificar_icc(estimado) if estimado is not None else None
        ),
    }


# ---------------------------------------------------------------------- informe
def _fmt(v, dec=2, pct=False):
    if v is None:
        return "—"
    return f"{v * 100:.{dec - 1 if dec > 1 else 0}f} %" if pct else f"{v:.{dec}f}"


def _svg_dispersion(pares: list[dict], eje: str) -> str:
    ancho, alto, m = 360, 300, 40
    vals = [p["sistema"] for p in pares] + [p["experta"] for p in pares]
    tope = 100 if max(vals) > 10 else 10

    def px(v):
        return m + (ancho - 2 * m) * v / tope

    def py(v):
        return alto - m - (alto - 2 * m) * v / tope

    partes = [
        f'<svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="Dispersión sistema contra experta" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{ancho}" height="{alto}" fill="white"/>',
        f'<line x1="{m}" y1="{alto - m}" x2="{ancho - m}" y2="{alto - m}" stroke="#444"/>',
        f'<line x1="{m}" y1="{m}" x2="{m}" y2="{alto - m}" stroke="#444"/>',
        f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(tope)}" y2="{py(tope)}" stroke="#999" stroke-dasharray="4 3"/>',
    ]
    for t in range(0, tope + 1, tope // 5):
        partes.append(
            f'<text x="{px(t)}" y="{alto - m + 16}" font-size="10" text-anchor="middle">{t}</text>'
        )
        partes.append(
            f'<text x="{m - 6}" y="{py(t) + 3}" font-size="10" text-anchor="end">{t}</text>'
        )
    for p in pares:
        partes.append(
            f'<circle cx="{px(p["experta"])}" cy="{py(p["sistema"])}" r="5" fill="#1f5fae"/>'
        )
        partes.append(
            f'<text x="{px(p["experta"]) + 8}" y="{py(p["sistema"]) - 6}" font-size="10">{html.escape(p["caso"][:18])}</text>'
        )
    partes.append(
        f'<text x="{ancho / 2}" y="{alto - 6}" font-size="11" text-anchor="middle">Valoración de la experta ({eje})</text>'
    )
    partes.append(
        f'<text transform="translate(12 {alto / 2}) rotate(-90)" font-size="11" text-anchor="middle">Sistema ({eje})</text>'
    )
    partes.append("</svg>")
    return "".join(partes)


def _svg_barras(filas: list[dict]) -> str:
    ancho, alto, m = 460, 300, 46
    tope = (
        max(
            max(
                f["minutos_manual"],
                f.get("minutos_sistema_bd") or 0,
                f.get("minutos_sistema_observado") or 0,
            )
            for f in filas
        )
        or 1
    )
    grupo = (ancho - m - 10) / len(filas)
    partes = [
        f'<svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="Minutos por caso" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{ancho}" height="{alto}" fill="white"/>',
        f'<line x1="{m}" y1="{alto - m}" x2="{ancho - 10}" y2="{alto - m}" stroke="#444"/>',
    ]
    series = [
        ("minutos_manual", "#b3541e", "Manual"),
        ("minutos_sistema_bd", "#1f5fae", "Sistema (BD)"),
        ("minutos_sistema_observado", "#2f8f5b", "Sistema (observado)"),
    ]
    for i, f in enumerate(filas):
        x0 = m + grupo * i + 6
        ancho_b = (grupo - 12) / 3
        for j, (clave, color, _) in enumerate(series):
            v = f.get(clave)
            if v is None:
                continue
            h = (alto - 2 * m) * v / tope
            partes.append(
                f'<rect x="{x0 + ancho_b * j:.1f}" y="{alto - m - h:.1f}" width="{ancho_b - 2:.1f}" height="{h:.1f}" fill="{color}"/>'
            )
            partes.append(
                f'<text x="{x0 + ancho_b * j + ancho_b / 2 - 1:.1f}" y="{alto - m - h - 3:.1f}" font-size="9" text-anchor="middle">{v:.0f}</text>'
            )
        partes.append(
            f'<text x="{x0 + (grupo - 12) / 2:.1f}" y="{alto - m + 14}" font-size="10" text-anchor="middle">{html.escape(f["caso"][:16])}</text>'
        )
    for j, (_, color, nombre) in enumerate(series):
        partes.append(
            f'<rect x="{m + j * 130}" y="8" width="10" height="10" fill="{color}"/><text x="{m + j * 130 + 14}" y="17" font-size="10">{nombre}</text>'
        )
    partes.append(
        f'<text transform="translate(12 {alto / 2}) rotate(-90)" font-size="11" text-anchor="middle">Minutos</text>'
    )
    partes.append("</svg>")
    return "".join(partes)


def _tabla(encabezados: list[str], filas: list[list[str]]) -> str:
    cab = "".join(f"<th>{html.escape(h)}</th>" for h in encabezados)
    cuerpo = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in fila) + "</tr>" for fila in filas
    )
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table>"


def _forma_icc(r: dict, nombre: str) -> str:
    f = r["formas"].get(nombre)
    if not f:
        return "—"
    ic = (
        "sin intervalo"
        if f["inferior"] is None
        else f"IC 95 %: {_fmt(f['inferior'])} a {_fmt(f['superior'])}"
    )
    return f"{_fmt(f['estimado'])} ({ic})"


def informe_html(res: dict) -> str:
    h = [
        "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Informe de validación QA/QC</title>",
        "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#222}"
        "table{border-collapse:collapse;margin:8px 0 16px;width:100%}th,td{border:1px solid #bbb;padding:5px 8px;font-size:13px;text-align:left}"
        "th{background:#eef2f7}.aviso{background:#fff4d6;border:1px solid #e0b84a;padding:8px 12px;margin:8px 0}"
        ".sintetico{background:#fde2e2;border:1px solid #d33;padding:10px 14px;font-weight:bold}"
        ".ok{color:#17703d;font-weight:bold}.no{color:#b3261e;font-weight:bold}.lim{color:#8a5a00;font-weight:bold}h2{margin-top:28px}"
        ".fig{display:inline-block;vertical-align:top;margin:0 12px 12px 0}</style></head><body>",
        "<h1>Informe de validación QA/QC — Trust 4P</h1>",
        f"<p>Generado: {res['generado_en']} · Versión(es) del modelo: {html.escape(', '.join(res['versiones_modelo']) or '—')}</p>",
    ]
    if res["sintetico"]:
        h.append(
            "<p class='sintetico'>DATOS SINTÉTICOS DE DEMOSTRACIÓN: estas cifras no son resultados del estudio.</p>"
        )
    for a in res["avisos"]:
        h.append(f"<p class='aviso'>⚠ {html.escape(a)}</p>")

    c = res.get("concordancia")
    h.append(
        "<h2>1. Concordancia con la valoración de la experta (KPI: ICC ≥ 0,70)</h2>"
    )
    if not c:
        h.append("<p>Sin datos suficientes: faltan sistema.csv o experta.csv.</p>")
    else:
        h.append(
            f"<p>Casos comparados: <b>{c['n_casos']}</b>. Meta del documento: ICC ≥ {META_ICC:.2f}.</p>"
        )
        g = c["global"]
        h.append(
            _tabla(
                [
                    "Caso",
                    "Índice del sistema",
                    "Valoración de la experta",
                    "Diferencia",
                ],
                [
                    [
                        html.escape(p["caso"]),
                        _fmt(p["sistema"], 1),
                        _fmt(p["experta"], 1),
                        _fmt(p["sistema"] - p["experta"], 1),
                    ]
                    for p in g["pares"]
                ],
            )
        )
        if g.get("icc") and g["icc"].get("definido"):
            v = c.get("veredicto")
            if v:
                clase = {
                    "cumple con evidencia robusta": "ok",
                    "cumple con evidencia limitada": "lim",
                }.get(v["estado"], "no")
                h.append(
                    f"<p>ICC(2,1), acuerdo absoluto sobre el índice global: <b>{_forma_icc(g['icc'], 'ICC2')}</b> → "
                    f"<span class='{clase}'>{v['estado']}</span> (concordancia {v['interpretacion']}).</p>"
                )
            h.append(
                _tabla(
                    ["Forma", "Estimador (IC 95 %)"],
                    [
                        [n, _forma_icc(g["icc"], n)]
                        for n in ("ICC1", "ICC2", "ICC3", "ICC2k", "ICC3k")
                        if n in g["icc"]["formas"]
                    ],
                )
            )
            if g["icc"]["n"] < 5:
                h.append(
                    "<p class='aviso'>Con menos de 5 casos el intervalo de confianza es muy amplio: la cifra no permite generalizar.</p>"
                )
        ba = g.get("bland_altman")
        if ba:
            h.append(
                f"<p>Sesgo medio (sistema − experta): <b>{_fmt(ba['sesgo'], 1)}</b> puntos · límites de acuerdo 95 %: "
                f"{_fmt(ba['limite_inferior'], 1)} a {_fmt(ba['limite_superior'], 1)} · diferencia absoluta media: {_fmt(ba['diferencia_absoluta_media'], 1)}.</p>"
            )
        h.append(
            "<div class='fig'>" + _svg_dispersion(g["pares"], "índice 0–100") + "</div>"
        )
        if c.get("dimensiones"):
            d = c["dimensiones"]
            h.append(
                f"<h3>Por dimensión (análisis secundario, {d['n_puntos']} puntos)</h3><p>ICC(2,1): {_forma_icc(d['icc'], 'ICC2')}. {d['nota']}</p>"
            )
        if c.get("niveles"):
            n = c["niveles"]
            h.append("<h3>Nivel de madurez</h3>")
            h.append(
                f"<p>Coinciden exactamente: <b>{_fmt(n['coinciden'], 1, True)}</b> · dentro de ±1 nivel: <b>{_fmt(n['dentro_de_uno'], 1, True)}</b> · "
                f"kappa ponderado lineal: <b>{_fmt(n['kappa_ponderado'])}</b> · Spearman (índice): <b>{_fmt(n['spearman'])}</b>.</p>"
            )
        if c.get("prioridades"):
            p = c["prioridades"]
            h.append("<h3>Prioridades de mejora</h3>")
            h.append(
                f"<p>La dimensión más débil del sistema está entre las 3 prioridades de la experta en <b>{_fmt(p['coincide'], 1, True)}</b> de los casos "
                f"y coincide con su primera prioridad en <b>{_fmt(p['coincide_con_la_primera'], 1, True)}</b>.</p>"
            )
            h.append(
                _tabla(
                    [
                        "Caso",
                        "Más débil (sistema)",
                        "Prioridades de la experta",
                        "¿Coincide?",
                    ],
                    [
                        [
                            html.escape(x["caso"]),
                            html.escape(x["dimension_mas_debil_sistema"]),
                            html.escape(" > ".join(x["prioridades_experta"])),
                            "Sí" if x["coincide"] else "No",
                        ]
                        for x in p["casos"]
                    ],
                )
            )

    t = res.get("tiempo")
    h.append("<h2>2. Reducción del tiempo de diagnóstico</h2>")
    if not t:
        h.append("<p>Sin datos: falta tiempos.csv.</p>")
    else:
        h.append(
            _tabla(
                [
                    "Caso",
                    "Manual (min)",
                    "Sistema, BD (min)",
                    "Reducción BD",
                    "Sistema, observado (min)",
                    "Reducción observada",
                ],
                [
                    [
                        html.escape(f["caso"]),
                        _fmt(f["minutos_manual"], 0),
                        _fmt(f.get("minutos_sistema_bd"), 0),
                        _fmt(f.get("reduccion_bd"), 1, True),
                        _fmt(f.get("minutos_sistema_observado"), 0),
                        _fmt(f.get("reduccion_observado"), 1, True),
                    ]
                    for f in t["casos"]
                ],
            )
        )
        h.append(
            f"<p>Reducción media con el tiempo de la BD: <b>{_fmt(t['reduccion_media_bd'], 1, True)}</b> · con el tiempo observado: <b>{_fmt(t['reduccion_media_observado'], 1, True)}</b>.</p><p>{t['nota']}</p>"
        )
        h.append("<div class='fig'>" + _svg_barras(t["casos"]) + "</div>")

    r = res.get("recomendaciones")
    h.append("<h2>3. Utilidad de las recomendaciones (juicio de la experta)</h2>")
    if not r:
        h.append("<p>Sin calificaciones.</p>")
    else:
        h.append(
            _tabla(
                ["Calificación", "Cantidad"],
                [[CALIFICACIONES[k], str(v)] for k, v in r["conteo"].items()],
            )
        )
        h.append(
            f"<p>Útiles: <b>{_fmt(r['porcentaje_util'], 1, True)}</b> · útiles o parcialmente útiles: <b>{_fmt(r['porcentaje_util_o_parcial'], 1, True)}</b> ({r['calificadas']} de {r['total_listadas']} calificadas).</p>"
        )

    u = res.get("usabilidad")
    h.append("<h2>4. Usabilidad</h2>")
    if not u:
        h.append("<p>Sin cuestionarios SUS.</p>")
    else:
        h.append(
            _tabla(
                ["Participante", "Rol", "SUS (0–100)"],
                [
                    [
                        html.escape(p["participante"]),
                        html.escape(p["rol"]),
                        _fmt(p["sus"], 1),
                    ]
                    for p in u["participantes"]
                ],
            )
        )
        h.append(
            f"<p>SUS medio: <b>{_fmt(u['media'], 1)}</b> (referencia {u['referencia']:.0f}) → "
            f"{'supera' if u['supera_referencia'] else 'no alcanza'} la referencia.</p>"
        )
    tk = res.get("tareas")
    if tk:
        h.append(
            f"<p>Tasa de éxito sin ayuda en las tareas clave: <b>{_fmt(tk['exito_sin_ayuda'], 1, True)}</b> ({tk['intentos']} intentos).</p>"
        )
        h.append(
            _tabla(
                ["Tarea", "Éxito", "Con ayuda", "Fallo"],
                [
                    [
                        html.escape(k),
                        str(v["exito"]),
                        str(v["con_ayuda"]),
                        str(v["fallo"]),
                    ]
                    for k, v in tk["por_tarea"].items()
                ],
            )
        )
    h.append("</body></html>")
    return "\n".join(h)


# ------------------------------------------------------------------------ demo
def _demo(carpeta: Path) -> None:
    """Datos inventados para probar la herramienta; se marcan como sintéticos."""
    azar = random.Random(2026)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "sintetico.flag").write_text(
        "datos sintéticos de demostración\n", encoding="utf-8"
    )
    dims = ["proposito", "procesos", "personas", "plataforma"]
    casos = ["Caso A", "Caso B", "Caso C", "Caso D"]
    base = {
        "Caso A": [28, 35, 40, 22],
        "Caso B": [55, 48, 60, 52],
        "Caso C": [72, 66, 80, 70],
        "Caso D": [40, 52, 45, 58],
    }
    sist, exp = [], []
    for c in casos:
        ps = base[c]
        glob = sum(ps) / 4
        nivel = min(10, max(1, int(-(-glob // 10))))
        sist.append(
            {
                "caso": c,
                "diagnostico_id": f"demo-{c[-1]}",
                "consecutivo": 1,
                "modelo_version": "demo",
                "estado": "evaluado",
                "minutos_hasta_informe": round(azar.uniform(35, 70), 1),
                "indice_global": round(glob, 2),
                "nivel": nivel,
                **{f"puntaje_{d}": v for d, v in zip(dims, ps)},
            }
        )
        ruido = [azar.uniform(-8, 8) for _ in dims]
        pe = [max(0, min(100, v + r)) for v, r in zip(ps, ruido)]
        ge = sum(pe) / 4
        orden = sorted(zip(dims, pe), key=lambda x: x[1])
        exp.append(
            {
                "caso": c,
                "indice_experta": round(ge, 1),
                "nivel_experta": min(10, max(1, int(-(-ge // 10)))),
                **{f"puntaje_{d}": round(v, 1) for d, v in zip(dims, pe)},
                "prioridad_1": orden[0][0],
                "prioridad_2": orden[1][0],
                "prioridad_3": orden[2][0],
            }
        )
    escribir_csv(carpeta / "sistema.csv", list(sist[0]), sist)
    escribir_csv(carpeta / "experta.csv", list(exp[0]), exp)
    escribir_csv(
        carpeta / "tiempos.csv",
        ["caso", "minutos_manual", "minutos_sistema_observado"],
        [
            {"caso": c, "minutos_manual": m, "minutos_sistema_observado": o}
            for c, m, o in zip(casos, (300, 240, 360, 280), (32, 41, 38, 35))
        ],
    )
    escribir_csv(
        carpeta / "recomendaciones.csv",
        ["caso", "recomendacion", "origen", "dimension", "calificacion"],
        [
            {
                "caso": c,
                "recomendacion": f"Recomendación {i}",
                "origen": "agente",
                "dimension": d,
                "calificacion": azar.choice(["util", "util", "parcial", "no_util"]),
            }
            for c in casos
            for i, d in enumerate(dims[:3], 1)
        ],
    )
    escribir_csv(
        carpeta / "sus.csv",
        ["participante", "rol", *[f"i{n}" for n in range(1, 11)]],
        [
            {
                "participante": f"P{i}",
                "rol": rol,
                **{
                    f"i{n}": (azar.choice([4, 5]) if n % 2 else azar.choice([1, 2]))
                    for n in range(1, 11)
                },
            }
            for i, rol in enumerate(["representante", "consultor", "administrador"], 1)
        ],
    )
    escribir_csv(
        carpeta / "tareas.csv",
        ["participante", "rol", "tarea", "resultado"],
        [
            {
                "participante": f"P{i}",
                "rol": "representante",
                "tarea": t,
                "resultado": azar.choice(["exito", "exito", "con_ayuda"]),
            }
            for i in (1, 2)
            for t in (
                "T1 iniciar diagnóstico",
                "T2 responder",
                "T3 ver informe",
                "T4 descargar PDF",
            )
        ],
    )
    print(f"Datos sintéticos escritos en {carpeta}")


# ------------------------------------------------------------------------ main
def principal(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(prog="validacion", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="orden", required=True)
    for nombre in ("exportar", "plantillas", "analizar", "demo"):
        s = sub.add_parser(nombre)
        s.add_argument("--carpeta", default="validacion_datos", type=Path)
        if nombre == "exportar":
            s.add_argument(
                "--empresas",
                required=True,
                help="Expresión regular (sobre el nombre) de las empresas del estudio",
            )
        if nombre == "plantillas":
            s.add_argument(
                "--dimensiones", default="proposito,procesos,personas,plataforma"
            )
    a = p.parse_args(argv)
    if a.orden == "exportar":
        asyncio.run(_exportar(a.empresas, a.carpeta))
    elif a.orden == "plantillas":
        _plantillas(a.carpeta, [d for d in a.dimensiones.split(",") if d])
    elif a.orden == "demo":
        _demo(a.carpeta)
    else:
        res = analizar(a.carpeta)
        (a.carpeta / "resultados.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        (a.carpeta / "informe.html").write_text(informe_html(res), encoding="utf-8")
        print(
            f"Resultados en {a.carpeta / 'resultados.json'} e {a.carpeta / 'informe.html'}"
        )
        for aviso in res["avisos"]:
            print("AVISO:", aviso)


if __name__ == "__main__":
    principal()
