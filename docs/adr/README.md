# Registro de decisiones de arquitectura (ADR)

Formato: [Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (Contexto / Decisión / Consecuencias). Un ADR se escribe cuando la decisión ya está tomada e implementada, no antes — documenta lo que el código hace y por qué, para que no haya que reconstruirlo leyendo el historial de commits.

Estos ADR alimentan el Bloque H del SAD (documento final del trabajo de grado); este directorio es la fuente de verdad, el SAD los transcribe.

| # | Título | Estado |
|---|---|---|
| [0001](0001-sesion-con-estado-no-jwt.md) | Sesión con estado en servidor, no JWT | Aceptado |
| [0002](0002-puertos-sin-referencia-a-adaptadores.md) | Los puertos del dominio no referencian adaptadores concretos | Aceptado |
| [0003](0003-tokens-un-solo-uso-codigo-hasheado.md) | Tokens de un solo uso con código hasheado | Aceptado |
| [0004](0004-validacion-pydantic-separada-del-dominio.md) | Validación de entrada en Pydantic, separada de las reglas de negocio | Aceptado |
| [0005](0005-separacion-calculo-deterministico-generacion-asistida.md) | Separación entre el cálculo determinístico y la generación asistida | Aceptado |
| [0006](0006-no-revelar-existencia-de-correo.md) | No revelar la existencia de un correo registrado | Aceptado |
| [0007](0007-versionado-api-v1.md) | Versionado de la API bajo prefijo `/v1` | Aceptado |
