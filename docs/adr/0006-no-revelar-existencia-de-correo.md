# 0006. No revelar la existencia de un correo registrado

**Estado:** Aceptado

## Contexto

El flujo de restablecimiento de contraseña (RF-05) recibe un correo y, si existe una cuenta asociada, envía un código de un solo uso. Si el endpoint respondiera distinto según el correo exista o no (404 vs 200, o un mensaje distinto), cualquiera podría enumerar qué correos tienen cuenta en la plataforma probando uno por uno — una enumeración de usuarios (RNF-02, aislamiento y confidencialidad, citando OWASP Top 10 como fuente).

## Decisión

`SolicitarRestablecimiento.ejecutar()` ([`recuperar_contrasena.py`](../../src/aplicacion/casos_uso/recuperar_contrasena.py)) sale en silencio si el correo no existe, sin lanzar excepción; el router siempre responde el mismo mensaje genérico ("Si el correo está registrado, recibirá un enlace de restablecimiento") con el mismo código HTTP, exista o no la cuenta. El caso de uso está documentado explícitamente con este propósito en su docstring.

## Consecuencias

- **Positivas:** cierra el vector de enumeración de usuarios por este endpoint.
- **Negativas / límite conocido:** el tiempo de respuesta puede diferir ligeramente entre "correo existe → genera token y envía correo" y "correo no existe → retorna de inmediato" (un side-channel de temporización). No se ha mitigado (p. ej. con un retraso artificial constante) porque no está entre los RNF aprobados; queda como riesgo residual aceptado, no como pendiente activo.
- La misma disciplina debe aplicarse a cualquier futuro endpoint que reciba un identificador potencialmente enumerable (correo, NIT) sin autenticación previa — el diagnóstico de demostración (HU-007, el único endpoint público del sistema) es el próximo candidato a revisar bajo este mismo criterio cuando se implemente.
