import os
from urllib.parse import quote


def enlace_frontend(ruta: str, codigo: str) -> str:
    """Enlace a una pantalla del frontend que recibe un codigo de un solo uso
    (invitacion, restablecimiento). La base sale de URL_FRONTEND (RNF-08)."""
    base = os.getenv("URL_FRONTEND", "http://localhost:5173").rstrip("/")
    return f"{base}{ruta}?codigo={quote(codigo)}"
