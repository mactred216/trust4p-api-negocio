# 0021. Sustitución del modelo de lenguaje por el retiro del proveedor

**Estado:** Aceptado (reemplaza el modelo de ADR-007; el resto de ADR-007 sigue vigente)

## Contexto

ADR-007 eligió Qwen3-Next-80B-Instruct servido como servicio gestionado de Vertex AI. Google deprecó los cuatro endpoints gestionados de Qwen el 21 de julio de 2026 y los retiró el 21 de octubre de 2026; su alternativa documentada es desplegar el modelo por cuenta propia en Model Garden.

Desde esa fecha toda llamada al modelo responde `404 NOT_FOUND` («Publisher model … was not found or your project does not have access to it»). El servicio de evaluación lo traduce en un `502` y el diagnóstico queda `fallido`: conserva su índice, sus puntajes y su nivel, pero sin perfil de cultura, lienzo, síntesis ni recomendaciones, y el informe en PDF no se genera. Lo observó la dirección de Trust 4P el 24 de octubre de 2026 durante el plan de pruebas, y el reproceso fallaba igual.

## Decisión

Se sustituye el modelo por **gpt-oss-120b** (`publishers/openai/models/gpt-oss-120b-maas`), de pesos abiertos y servido como servicio gestionado de Vertex AI por el mismo endpoint global. Se mantiene el resto de ADR-007: modelo servido por la plataforma de nube (sin credenciales de otro proveedor), familia de pesos abiertos (RNF-28) y cuenta de servicio con permiso mínimo.

El identificador sigue siendo configurable con `VERTEX_INFERENCE_MODEL`, y la bitácora de ejecuciones del agente registra el nombre del modelo realmente usado. El adaptador deja de forzar `response_mime_type`: el formato JSON se exige en la instrucción y RF-38 valida la respuesta en el código, que es lo que ya hacía con Qwen.

Alternativas descartadas:

- **Desplegar Qwen3-Next por cuenta propia en Model Garden:** exige una GPU dedicada permanente, con un costo mensual incompatible con la escala a cero de ADR-016.
- **Un modelo propietario (Gemini):** cumple técnicamente, pero incumple el requisito de familia de pesos abiertos (RNF-28).

## Consecuencias

- **Positivas:** el servicio de evaluación vuelve a funcionar sin cambiar el contrato con la API de negocio; el índice no cambia porque lo calcula el motor determinístico (ADR-005); el cambio de modelo en el futuro es una variable de entorno.
- **Negativas:** gpt-oss-120b razona antes de responder y tarda más que Qwen: en la prueba en vivo del 25 de octubre de 2026 una evaluación completa tomó entre 60 y 146 segundos, dentro de la espera de 300 segundos de la API y del plazo de Cloud Run. El texto que redacta el agente cambia de estilo, de modo que los diagnósticos evaluados con Qwen no son idénticos en redacción a los nuevos. Los diagnósticos que quedaron `fallidos` desde el 21 de octubre se recuperan con «Reprocesar evaluaciones pendientes».
