# Herramienta de análisis de la validación QA/QC

Código: `scripts/validacion/`. Apoya el cuarto objetivo (ver `Plan-de-validacion-QA-QC.docx`). Está en Python puro: no
necesita paquetes distintos de los del proyecto (`motor`, `python-dotenv`). Las pruebas
(`tests/unitarias/validacion/`) contrastan el cálculo del ICC con el ejemplo publicado de Shrout y Fleiss (1979).

## Flujo

```bash
python -m scripts.validacion.analizar plantillas --carpeta validacion_datos
python -m scripts.validacion.analizar exportar --empresas "^Caso " --carpeta validacion_datos
python -m scripts.validacion.analizar analizar --carpeta validacion_datos
```

1. `plantillas` crea los CSV vacíos (no pisa los que ya existen).
2. Se transcriben a mano los formatos de papel: `experta.csv` (F-04), `tiempos.csv` (F-03), `sus.csv` (F-06),
   `tareas.csv` (F-02) y la columna `calificacion` de `recomendaciones.csv` (F-05).
3. `exportar` lee —**solo lectura**— los diagnósticos de las empresas cuyo nombre coincida con la expresión regular y
   escribe `sistema.csv`. Avisa si los casos se hicieron con más de una versión del modelo.
4. `analizar` escribe `resultados.json` e `informe.html` (con gráficos) y lista avisos de inconsistencia.

`demo --carpeta <ruta>` genera datos **sintéticos** (marcados como tales en el informe) para ensayar el flujo.

## Columnas de los CSV (UTF-8, punto decimal)

| Archivo | Columnas |
|---|---|
| `sistema.csv` (lo escribe `exportar`) | `caso, diagnostico_id, consecutivo, modelo_version, estado, iniciado_en, completado_en, evaluado_en, minutos_hasta_informe, indice_global, nivel, nivel_nombre, perfil_cultura, recomendaciones_agente, recomendaciones_consultor, puntaje_<dimension>…` |
| `experta.csv` (F-04) | `caso, indice_experta, nivel_experta, puntaje_<dimension>…, prioridad_1, prioridad_2, prioridad_3` (las prioridades son códigos de dimensión: `proposito`, `procesos`, `personas`, `plataforma`) |
| `tiempos.csv` (F-03) | `caso, minutos_manual, minutos_sistema_observado` (el tiempo de la base de datos viene de `sistema.csv`) |
| `recomendaciones.csv` (F-05) | `caso, recomendacion, origen, dimension, calificacion` (`util`, `parcial` o `no_util`) |
| `sus.csv` (F-06) | `participante, rol, i1 … i10` (valores 1 a 5) |
| `tareas.csv` (F-02) | `participante, rol, tarea, resultado` (`exito`, `con_ayuda` o `fallo`) |

La columna `caso` debe ser idéntica en todos los archivos y coincidir con el **nombre de la empresa** en la plataforma.

## Qué calcula

- **Concordancia (KPI 2):** ICC(2,1) de acuerdo absoluto del índice global (sistema vs experta) con IC 95 %; veredicto
  «cumple con evidencia robusta / limitada» o «no cumple» según la meta 0,70; ICC por dimensión (análisis secundario);
  sesgo y límites de Bland-Altman; coincidencia de nivel exacta y a ±1, kappa ponderado lineal, Spearman; coincidencia de
  la dimensión más débil del sistema con las prioridades de la experta.
- **Tiempo (KPI 1):** reducción por caso y media, con el tiempo de la base de datos y con el observado.
- **Recomendaciones:** distribución útil / parcial / no útil.
- **Usabilidad:** SUS por participante y media (referencia 68); tasa de éxito sin ayuda por tarea.

## Límites

- El ICC exige al menos 3 casos; con menos de 5 el intervalo es muy amplio y el informe lo advierte.
- El tiempo de la base de datos va de la apertura del diagnóstico a la evaluación e incluye pausas de quien responde.
- La herramienta no decide la aceptación: eso lo hace el acta F-09 con los criterios del plan.
