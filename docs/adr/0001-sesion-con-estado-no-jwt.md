# 0001. Sesión con estado en servidor, no JWT

**Estado:** Aceptado

## Contexto

El borrador inicial del proyecto contemplaba JWT para la autenticación. El sistema tiene un requisito explícito (RF-28, catálogo de roles y permisos) por el cual un administrador puede modificar los permisos de un rol en cualquier momento, y ese cambio debe tener efecto inmediato sobre cualquier usuario que ya tenga una sesión abierta con ese rol.

Un JWT es un testigo autocontenido: una vez firmado, el servidor no puede invalidarlo antes de su expiración sin mantener una lista de revocación — lo que anula la ventaja principal de JWT (no consultar estado en cada petición) y termina siendo, en la práctica, una sesión con estado disfrazada de JWT.

## Decisión

Usamos sesión con estado en el servidor: un testigo opaco (`secrets.token_urlsafe(32)`) que el cliente guarda en una cookie `HttpOnly`, `Secure`, `SameSite=Strict`; el servidor almacena únicamente el hash SHA-256 del testigo (nunca el valor en claro) en la colección `sesiones`, junto con `usuario_id`, `rol_codigo`, `permisos` y `expira_en`. Cada petición autenticada consulta esta colección ([`autorizacion.py`](../../src/api/middleware/autorizacion.py)).

Consecuencia directa: revocar una sesión es una operación trivial (`RepositorioSesion.revocar` / `revocar_todas_de_usuario`), usada en: cambio de contraseña (revoca todas las sesiones del usuario), y modificación de los permisos de un rol (revoca las sesiones de todos los usuarios que lo ostentan — ver decisión implementada tras el hallazgo de la regla R-17 del diccionario de datos).

## Consecuencias

- **Positivas:** revocación inmediata y real, sin lista de revocación adicional; el testigo nunca se persiste en claro (solo su hash), igual que las contraseñas.
- **Negativas:** cada petición autenticada hace una consulta a `sesiones` (costo aceptado; no hay escalamiento horizontal sin estado compartido — la colección en MongoDB Atlas ya es el estado compartido).
- Cierre de sesión por inactividad a los 30 minutos (`DURACION_SESION_MINUTOS`, RF-49) es una consecuencia natural de tener `expira_en` en el documento de sesión.
