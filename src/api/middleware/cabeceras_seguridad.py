from starlette.middleware.base import BaseHTTPMiddleware

CABECERAS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class CabecerasSeguridad(BaseHTTPMiddleware):
    """RNF-05: cabeceras de seguridad básicas en todas las respuestas; las de
    la API (/v1) además no se almacenan en caché."""

    async def dispatch(self, request, call_next):
        respuesta = await call_next(request)
        for nombre, valor in CABECERAS.items():
            respuesta.headers.setdefault(nombre, valor)
        if request.url.path.startswith("/v1"):
            respuesta.headers.setdefault("Cache-Control", "no-store")
        return respuesta
