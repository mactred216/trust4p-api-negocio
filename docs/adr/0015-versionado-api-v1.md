# 0015. Versionado de la API bajo prefijo `/v1`

**Estado:** Aceptado

## Contexto

El frontend de Sebastián (React) y, más adelante, un cliente de terceros, consumen esta API por HTTP. Un cambio incompatible en la forma de un endpoint (renombrar un campo, cambiar un código de estado) no puede desplegarse sin coordinar el despliegue exacto del cliente, salvo que las versiones convivan. La gestión de inventario de endpoints con versión explícita es, además, una práctica de seguridad reconocida por OWASP (un endpoint sin versión ni catálogo es más difícil de dar de baja de forma controlada).

## Decisión

Todos los routers se montan bajo el prefijo `/v1` en [`main.py`](../../src/api/main.py) (`app.include_router(x.router, prefix="/v1")`), nunca en la raíz. Un cambio incompatible en el futuro se serviría bajo `/v2` en paralelo, sin retirar `/v1` hasta que el o los clientes migren.

## Consecuencias

- **Positivas:** el frontend puede fijar `API_BASE_URL=".../v1"` una sola vez; un cambio incompatible no rompe clientes en producción de forma silenciosa.
- **Negativas:** ninguna hasta ahora — el costo de este ADR es prácticamente nulo (un prefijo de ruta) comparado con el riesgo que evita; no ha sido necesario todavía introducir `/v2`.
