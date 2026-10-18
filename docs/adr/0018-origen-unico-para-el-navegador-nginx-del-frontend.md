# 0018. Origen único para el navegador: nginx del frontend reenvía a las dos APIs

**Estado:** Aceptado

## Contexto

La sesión viaja en una cookie `HttpOnly`, `Secure` y `SameSite=Strict` (ADR-010). Si cada servicio tuviera su propio dominio, la cookie emitida por la API de negocio no llegaría al servicio de evaluación y habría que abrir CORS con credenciales entre dominios.

## Decisión

El contenedor del frontend sirve la aplicación y actúa como proxy inverso (`nginx.conf.template` del repositorio `trust4p-frontend`): `/api/negocio/` se reenvía a la API de negocio y `/api/agente/` al servicio de evaluación. El navegador solo habla con un origen.

## Consecuencias

- **Positivas:** la cookie de sesión funciona sin configuración cruzada entre dominios; los servicios internos no se exponen directamente al navegador.
- **Negativas:** el frontend es un punto adicional en la ruta de cada petición; las URL de destino deben configurarse por variable de entorno en cada despliegue.
