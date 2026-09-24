# 0004. Validación de entrada en Pydantic, separada de las reglas de negocio del dominio

**Estado:** Aceptado

## Contexto

Un campo de entrada mezcla dos tipos de restricción de naturaleza distinta: formato (¿el texto no está vacío? ¿el peso es un número entre 0 y 1? ¿la longitud no excede 200 caracteres?) y regla de negocio (¿la suma de los pesos de las dimensiones da exactamente 1? ¿la versión ya fue publicada? ¿el consultor tiene una asignación vigente sobre esta empresa?). La primera depende solo del dato entrante; la segunda depende del estado del sistema y pertenece al dominio (RF-30 a RF-34, reglas R-01 a R-04 del diccionario de datos).

## Decisión

La validación de formato vive en los modelos Pydantic de cada router (`field_validator`, `model_validator`), con las funciones reutilizables centralizadas en [`validadores_comunes.py`](../../src/api/validadores_comunes.py) (`texto_no_vacio`, `peso_valido`, `entero_positivo`, `clave_cumple_politica`, etc. — extraídas en el pendiente #3 tras detectarse repetidas palabra por palabra en `solicitudes.py`, `empresas.py`, `usuarios.py`, `autenticacion.py` y `modelos_madurez.py`). Las reglas de negocio viven como métodos en las entidades de dominio (`ModeloMadurez.validar_pesos_dimensiones()`, `RolCatalogo.quitar_permiso()`, `SolicitudAcceso.aprobar()`) o, cuando dependen de más de una entidad, en el caso de uso (p. ej. R-17: revocar sesiones al cambiar permisos de un rol).

Un router nunca reimplementa una regla de negocio en un validador Pydantic, y un método de dominio nunca valida formato de entrada (longitud de cadena, rango numérico crudo) — esa responsabilidad ya fue cubierta en el borde.

## Consecuencias

- **Positivas:** las reglas de negocio se prueban con pruebas de dominio puras, sin FastAPI ni HTTP de por medio (`tests/unitarias/dominio/`); un error de formato se rechaza con 400 antes de invocar ningún caso de uso, sin tocar la base de datos.
- **Negativas:** una regla que parece "de formato" pero en realidad depende de otras entidades (p. ej. que `dimension_codigo` de una pregunta exista entre las dimensiones ya creadas) no puede resolverse en Pydantic y obliga a un `ValueError` en el dominio, capturado luego como 400 en el router — la frontera exige criterio, no es automática.
