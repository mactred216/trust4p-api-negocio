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
    opciones_codigo: list[str] = field(default_factory=list)
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
        self, respuesta: Respuesta, codigos_obligatorias_aplicables: set[str]
    ) -> None:
        """RF-09 (HU-10): cada respuesta se guarda de inmediato, sin acción
        explícita de 'guardar'. Si la pregunta ya tenía respuesta, la
        reemplaza (permite corregir antes de enviar el diagnóstico).

        RF-10: el avance se calcula sobre las preguntas OBLIGATORIAS
        APLICABLES (respetando el bloqueo condicional de RF-08), no sobre
        todas las preguntas activas."""
        if self.estado != ESTADO_INICIAL:
            raise ValueError(
                f"El diagnóstico no admite más respuestas (estado actual: {self.estado})"
            )

        self.respuestas = [
            r for r in self.respuestas if r.pregunta_codigo != respuesta.pregunta_codigo
        ]
        self.respuestas.append(respuesta)
        self._actualizar_avance(codigos_obligatorias_aplicables)

    def _actualizar_avance(self, codigos_obligatorias_aplicables: set[str]) -> None:
        total = len(codigos_obligatorias_aplicables)
        if total <= 0:
            self.porcentaje_avance = 0
            return
        respondidas = sum(
            1
            for r in self.respuestas
            if r.pregunta_codigo in codigos_obligatorias_aplicables
        )
        self.porcentaje_avance = min(100, round(respondidas * 100 / total))

    def respuesta_de(self, pregunta_codigo: str) -> Optional[Respuesta]:
        for r in self.respuestas:
            if r.pregunta_codigo == pregunta_codigo:
                return r
        return None

    def marcar_completado(self) -> None:
        """RF-07 paso 5: cierra la etapa de captura de respuestas antes de
        que el motor de cálculo/agente procese el diagnóstico (Iteración 3)."""
        if self.esta_cerrado():
            raise ValueError("El diagnóstico está cerrado")
        if self.estado != ESTADO_INICIAL:
            raise ValueError(
                f"El diagnóstico no está en borrador (estado actual: {self.estado})"
            )
        if self.porcentaje_avance < 100:
            raise ValueError(
                "Faltan preguntas obligatorias por responder para completar el diagnóstico"
            )
        self.estado = "completado"
        self.completado_en = datetime.now(timezone.utc)
