# 0012. Tokens de un solo uso con código hasheado

**Estado:** Aceptado

## Contexto

Tres flujos del sistema dependen de un código de un solo uso enviado por correo: invitación para completar registro (RF-03), restablecimiento de contraseña (RF-05) y verificación de correo. En los tres casos, si el código quedara almacenado en texto claro en `tokens_verificacion`, cualquiera con acceso de lectura a la base de datos (un volcado, un log mal configurado, un acceso indebido) podría usarlo directamente — el mismo problema que ya se evita con las contraseñas (RNF-03, bcrypt con sal).

## Decisión

`TokenVerificacion.generar_codigo()` produce el código en claro que se envía por correo (ver [`servicio_correo.py`](../../src/dominio/puertos/servicio_correo.py) y `ClienteCorreoSMTP`). El repositorio nunca persiste ese valor: `RepositorioMongoToken.guardar` calcula `hashlib.sha256(codigo.encode()).hexdigest()` y guarda solo `codigo_hash` ([`repositorio_mongo_token.py`](../../src/infraestructura/persistencia/repositorio_mongo_token.py)). La búsqueda al validar un token (`obtener_por_codigo`) hashea el código recibido y compara contra `codigo_hash` — el código en claro nunca vuelve a la base de datos después de generado.

Regla de integridad asociada (R-08 del diccionario de datos): un token solo puede consumirse una vez (`TokenVerificacion.marcar_usado()`); el token también tiene vigencia acotada (`esta_vigente()`).

## Consecuencias

- **Positivas:** un volcado de la colección `tokens_verificacion` no es explotable para completar un registro o restablecer una contraseña ajena.
- **Negativas:** ninguna relevante — SHA-256 sobre un código aleatorio de longitud suficiente no necesita sal (a diferencia de una contraseña elegida por un humano, no hay diccionario de ataque útil contra un código generado con `secrets`).
- La auditoría nunca debe registrar `codigo_hash` en claro junto con metadatos que permitan reconstruir el contexto de uso — regla ya aplicada en [`auditoria.py`](../../src/api/middleware/auditoria.py) (`Nunca incluir clave_hash, token_hash ni codigo_hash en valores_anteriores/valores_nuevos`).
