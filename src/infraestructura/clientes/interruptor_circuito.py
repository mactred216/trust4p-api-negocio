import time
from typing import Callable


class InterruptorDeCircuito:
    """Cortocircuito ante la caída de un servicio externo (ASR-02).

    Tras `umbral` fallos de disponibilidad seguidos el circuito se abre: durante
    `enfriamiento` segundos las llamadas se rechazan de inmediato, sin esperar
    el plazo del servicio caído. Pasado ese tiempo se deja pasar una sola
    llamada de sondeo (semiabierto): si tiene éxito el circuito se cierra; si
    falla vuelve a abrirse. El estado vive en la memoria de la instancia, igual
    que el límite de peticiones (cada instancia de Cloud Run aprende por su
    cuenta que el servicio está caído)."""

    def __init__(
        self,
        umbral: int = 3,
        enfriamiento: float = 60.0,
        reloj: Callable[[], float] = time.monotonic,
    ):
        self._umbral = max(1, umbral)
        self._enfriamiento = enfriamiento
        self._reloj = reloj
        self._fallos_seguidos = 0
        self._abierto_en: float | None = None
        self._sondeando = False

    @property
    def estado(self) -> str:
        if self._abierto_en is None:
            return "cerrado"
        if self._reloj() - self._abierto_en >= self._enfriamiento:
            return "semiabierto"
        return "abierto"

    def permitir(self) -> bool:
        """¿Se puede llamar al servicio ahora? En semiabierto solo pasa el
        sondeo: mientras esté en vuelo, las demás llamadas se rechazan."""
        estado = self.estado
        if estado == "cerrado":
            return True
        if estado == "semiabierto" and not self._sondeando:
            self._sondeando = True
            return True
        return False

    def registrar_exito(self) -> None:
        self._fallos_seguidos = 0
        self._abierto_en = None
        self._sondeando = False

    def registrar_fallo(self) -> None:
        self._fallos_seguidos += 1
        if self._sondeando or self._fallos_seguidos >= self._umbral:
            self._abierto_en = self._reloj()
            self._sondeando = False

    def segundos_para_reintento(self) -> int:
        if self._abierto_en is None:
            return 0
        restante = self._enfriamiento - (self._reloj() - self._abierto_en)
        return max(0, int(restante) + 1)
