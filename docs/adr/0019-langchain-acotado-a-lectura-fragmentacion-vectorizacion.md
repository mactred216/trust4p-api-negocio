# 0019. LangChain acotado a la lectura de PDF, la fragmentación y la vectorización

**Estado:** Aceptado

## Contexto

LangChain ofrece componentes para casi todo el flujo de recuperación y generación, pero orquestar con él la evaluación completa ocultaría reglas que deben ser explícitas y verificables (anclaje en evidencia, saneamiento, reintentos), y acoplaría el núcleo a una librería que cambia con rapidez (ADR-004, ADR-005).

## Decisión

En el servicio de evaluación asistida LangChain se usa solo para tres tareas de ingesta: leer PDF, fragmentar el texto y generar los vectores. La construcción de la petición, la validación de la salida, los reintentos y la recuperación de contexto se implementan en código propio, detrás de puertos.

## Consecuencias

- **Positivas:** el flujo de evaluación es legible y comprobable con pruebas; reemplazar la librería afecta a tres adaptadores.
- **Negativas:** hay código propio que mantener para lo que la librería ya resolvía.
