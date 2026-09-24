# 0002. Los puertos del dominio no referencian adaptadores concretos

**Estado:** Aceptado

## Contexto

El proyecto usa arquitectura hexagonal explícitamente para poder sustituir MongoDB, el proveedor de correo o el agente de IA sin tocar el dominio ni los casos de uso (justificación documentada en las restricciones de origen del CEO, RNF-25 a RNF-28, y resuelta con TRIZ en el Bloque B). Esa garantía solo existe si la dependencia va en una sola dirección: `infraestructura/` → `dominio/`, nunca al revés.

## Decisión

Cada puerto en `src/dominio/puertos/` es una clase `ABC` que declara únicamente en términos del dominio (entidades y tipos primitivos) — nunca importa `motor`, `bson`, `smtplib` ni ningún símbolo de `src/infraestructura/`. Cada adaptador en `src/infraestructura/persistencia/` o `src/infraestructura/clientes/` implementa un puerto y es la única capa que conoce el motor concreto. Esta regla se declara en el docstring de cada puerto (`"Puerto del dominio. Ningún adaptador se referencia aquí (ADR-002)."`) para que sea imposible de pasar por alto al añadir uno nuevo.

La inyección de dependencias se ensambla en un único punto, [`dependencias.py`](../../src/api/dependencias.py), vía `Depends()` de FastAPI — ningún caso de uso instancia un adaptador directamente.

## Consecuencias

- **Positivas:** un caso de uso se prueba con `unittest.mock.AsyncMock` sin tocar red ni MongoDB (ver `tests/unitarias/aplicacion/`); cambiar de MongoDB a otro motor, o de Gmail SMTP a un proveedor transaccional, es un adaptador nuevo detrás del mismo puerto, sin tocar dominio ni casos de uso — ya ocurrió una vez al decidir el proveedor SMTP (pendiente #6/#4).
- **Negativas:** cada nueva capacidad de persistencia exige tres archivos (entidad, puerto, adaptador) en vez de uno; se acepta el costo porque el proyecto explícitamente necesita esa sustituibilidad (RNF-25 a RNF-28).
