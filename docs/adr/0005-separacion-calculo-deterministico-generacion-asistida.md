# 0005. Separación entre el cálculo determinístico y la generación asistida

**Estado:** Aceptado

## Contexto

El índice de madurez de innovación tiene dos componentes de naturaleza distinta: un valor numérico (índice global, puntaje por dimensión, nivel de la rúbrica) derivado mecánicamente de las respuestas cerradas y la ponderación configurada en el modelo de madurez (RF-12, RF-13), y una interpretación en lenguaje natural (perfil de cultura, lienzo de negocio, recomendaciones — RF-14, RF-15, RF-16) que requiere razonamiento sobre texto libre y contexto recuperado de la base de conocimiento.

Si ambos componentes se calcularan en el mismo lugar invocando al modelo de lenguaje, el índice dejaría de ser reproducible: dos ejecuciones sobre el mismo diagnóstico podrían arrojar valores distintos, lo que rompe el objetivo de la tesis de que el sistema reproduzca el criterio de valoración de Trust 4P de forma consistente (ASR-01) y contradice la propia noción de "índice" como medición.

## Decisión

El motor de cálculo del índice reside en el núcleo de dominio del servicio de negocio (`trust4p-api-negocio`, este repo) y no invoca al modelo de lenguaje ni a ningún servicio externo — ver [`src/dominio/servicios/motor_calculo.py`](../../src/dominio/servicios/motor_calculo.py). El servicio de inteligencia artificial (`trust4p-servicio-agente`) recibe el índice ya calculado y genera el perfil de cultura, el lienzo de negocio y las recomendaciones a partir de él, sin poder alterarlo.

Las reglas de ponderación se encapsulan conforme al patrón de Estrategia (`EstrategiaPuntuacion`): cada tipo de pregunta (`seleccion_unica`/`seleccion_multiple`, `escala`/`numerica`, `texto_libre`) sabe convertir su propia respuesta en un valor dentro de la escala del modelo, o en `None` si no aporta un valor numérico. El puntaje de cada dimensión es el promedio ponderado (peso relativo de cada pregunta, RF-31/R-03) de las preguntas que sí aportan número, renormalizado sobre ese subconjunto — una pregunta de texto libre puede tener peso en la validación R-03 sin diluir el puntaje alcanzable de su dimensión, porque su contribución numérica es `None` y queda fuera de la suma de pesos. El índice global es el promedio ponderado de los puntajes de dimensión, usando el peso de cada dimensión (R-02). El nivel se obtiene ubicando el índice global dentro de la rúbrica publicada del modelo (RF-32).

## Consecuencias

- **Positivas:** el motor puede probarse por unidad sin red ni base de datos, incluida la prueba de reproducibilidad obligatoria (mismo conjunto de respuestas → mismo índice, ver `test_calcular_resultado_es_reproducible`); el índice sigue calculándose y persistiéndose aunque el servicio de inteligencia artificial no esté disponible, porque no depende de él.
- **Negativas:** el flujo adquiere una dependencia secuencial entre ambos servicios — el de negocio debe calcular antes de invocar al de inteligencia artificial, y debe mantenerse la correspondencia entre el esquema de salida del motor y el contrato de entrada del servicio de inteligencia artificial (`resultado_calculo`, ver sección 3.5.1 del documento de arquitectura).

Trazabilidad: ASR-01, ASR-04, ASR-16 · RNF-13.
