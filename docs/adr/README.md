# Registro de decisiones de arquitectura (ADR)

Formato: [Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (Contexto / Decisión / Consecuencias). Un ADR se escribe cuando la decisión ya está tomada e implementada, no antes — documenta lo que el código hace y por qué, para que no haya que reconstruirlo leyendo el historial de commits.

La numeración es la del **catálogo unificado** del documento de arquitectura (SAD), que reúne las decisiones de todo el sistema. Este directorio contiene las decisiones que gobierna este repositorio o que viven en su código o en su proceso; las demás se documentan en el SAD o en el repositorio que las implementa.

| # | Título | Estado | Dónde |
|---|---|---|---|
| ADR-001 a ADR-004 | Dos servicios; diseño hexagonal; persistencia documental; búsqueda vectorial integrada | Aceptado | SAD |
| [ADR-005](0005-separacion-calculo-deterministico-generacion-asistida.md) | Separación entre el cálculo determinístico y la generación asistida | Aceptado | Este repositorio |
| ADR-006 a ADR-009 | Patrón repositorio; modelo de lenguaje de la plataforma; Python con FastAPI; React con Vite | Aceptado | SAD |
| [ADR-010](0010-sesion-con-estado-no-jwt.md) | Sesión con estado en servidor, no JWT | Aceptado | Este repositorio |
| [ADR-011](0011-puertos-sin-referencia-a-adaptadores.md) | Los puertos del dominio no referencian adaptadores concretos | Aceptado | Este repositorio |
| [ADR-012](0012-tokens-un-solo-uso-codigo-hasheado.md) | Tokens de un solo uso con código hasheado | Aceptado | Este repositorio |
| [ADR-013](0013-validacion-pydantic-separada-del-dominio.md) | Validación de entrada en Pydantic, separada de las reglas de negocio | Aceptado | Este repositorio |
| [ADR-014](0014-no-revelar-existencia-de-correo.md) | No revelar la existencia de un correo registrado | Aceptado | Este repositorio |
| [ADR-015](0015-versionado-api-v1.md) | Versionado de la API bajo prefijo `/v1` | Aceptado | Este repositorio |
| [ADR-016](0016-cloud-run-escala-a-cero-cpu-asignada-en-la-api.md) | Cloud Run con escala a cero y CPU siempre asignada en la API | Aceptado | Infraestructura |
| [ADR-017](0017-infraestructura-como-codigo-terraform-workload-identity.md) | Terraform y despliegue sin llaves con Workload Identity | Aceptado | Infraestructura |
| [ADR-018](0018-origen-unico-para-el-navegador-nginx-del-frontend.md) | Origen único para el navegador: nginx del frontend reenvía a las dos APIs | Aceptado | Frontend |
| [ADR-019](0019-langchain-acotado-a-lectura-fragmentacion-vectorizacion.md) | LangChain acotado a lectura de PDF, fragmentación y vectorización | Aceptado | Servicio de evaluación |
| [ADR-020](0020-desarrollo-iterativo-kanban-sin-scrum.md) | Desarrollo iterativo con tablero Kanban, sin Scrum | Aceptado | Proceso |

Equivalencia con la numeración anterior de este directorio: 0001 → ADR-010, 0002 → ADR-011, 0003 → ADR-012, 0004 → ADR-013, 0005 → ADR-005, 0006 → ADR-014, 0007 → ADR-015.
