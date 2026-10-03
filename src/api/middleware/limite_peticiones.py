import math
import time
from collections import deque

from fastapi import HTTPException, Request

"""Límite de peticiones por origen para endpoints públicos (RNF-09). Ventana
deslizante en memoria: no se persiste nada —ni la IP— y se pierde al reiniciar
el proceso. Con varias instancias (Cloud Run) el tope efectivo es por
instancia; un límite global exigiría un almacén compartido."""

MAXIMO_ORIGENES_RECORDADOS = 10_000


class LimitadorPeticiones:
    def __init__(self, maximo: int, ventana_segundos: int):
        self.maximo = maximo
        self.ventana_segundos = ventana_segundos
        self._registros: dict[str, deque[float]] = {}

    def _depurar(self, ahora: float) -> None:
        if len(self._registros) < MAXIMO_ORIGENES_RECORDADOS:
            return
        for origen in list(self._registros):
            cola = self._registros[origen]
            while cola and ahora - cola[0] >= self.ventana_segundos:
                cola.popleft()
            if not cola:
                del self._registros[origen]

    def registrar(self, origen: str) -> int | None:
        """None si la petición se admite; si no, segundos hasta poder reintentar."""
        ahora = time.monotonic()
        self._depurar(ahora)
        cola = self._registros.setdefault(origen, deque())
        while cola and ahora - cola[0] >= self.ventana_segundos:
            cola.popleft()
        if len(cola) >= self.maximo:
            return max(1, math.ceil(self.ventana_segundos - (ahora - cola[0])))
        cola.append(ahora)
        return None


def limitar_peticiones(limitador: LimitadorPeticiones):
    """Dependencia de FastAPI: responde 429 con Retry-After al superar el tope."""

    async def dependencia(request: Request) -> None:
        origen = request.client.host if request.client else "desconocido"
        espera = limitador.registrar(origen)
        if espera is not None:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas peticiones; intente de nuevo más tarde",
                headers={"Retry-After": str(espera)},
            )

    return dependencia
