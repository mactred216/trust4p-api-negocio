from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

ESTADOS_VALIDOS = {"borrador", "completado", "evaluado", "fallido", "cerrado"}
ESTADO_INICIAL = "borrador"
ESTADO_CERRADO = "cerrado"


@dataclass
class Respuesta:
    pregunta_codigo: str
    dimension_codigo: str
    opcion_codigo: Optional[str] = None
    valor: Optional[Decimal] = None
    texto: Optional[str] = None
    respondida_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Diagnostico:
    id: Optional[str]
    empresa_id: str
    empresa_nombre: str
    usuario_id: str
    modelo_version: str
    consecutivo: int
    estado: str = ESTADO_INICIAL
    porcentaje_avance: int = 0
    respuestas: list[Respuesta] = field(default_factory=list)
    iniciado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completado_en: Optional[datetime] = None
    evaluado_en: Optional[datetime] = None
    cerrado_en: Optional[datetime] = None

    def esta_cerrado(self) -> bool:
        return self.estado == ESTADO_CERRADO

    def registrar_respuesta(
        self, respuesta: Respuesta, total_preguntas_activas: int
    ) -> None:
        """RF-09 (HU-10): cada respuesta se guarda de inmediato, sin acción
        explícita de 'guardar'. Si la pregunta ya tenía respuesta, la
        reemplaza (permite corregir antes de enviar el diagnóstico)."""
        if self.esta_cerrado():
            raise ValueError("El diagnóstico está cerrado y no admite más respuestas")

        self.respuestas = [
            r for r in self.respuestas if r.pregunta_codigo != respuesta.pregunta_codigo
        ]
        self.respuestas.append(respuesta)
        self._actualizar_avance(total_preguntas_activas)

    def _actualizar_avance(self, total_preguntas_activas: int) -> None:
        if total_preguntas_activas <= 0:
            self.porcentaje_avance = 0
            return
        self.porcentaje_avance = min(
            100, round(len(self.respuestas) * 100 / total_preguntas_activas)
        )

    def respuesta_de(self, pregunta_codigo: str) -> Optional[Respuesta]:
        for r in self.respuestas:
            if r.pregunta_codigo == pregunta_codigo:
                return r
        return None
