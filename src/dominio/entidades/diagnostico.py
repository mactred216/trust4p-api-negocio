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
class DimensionResultado:
    codigo: str
    puntaje: Decimal
    observacion: Optional[str] = None


@dataclass
class PerfilCulturaResultado:
    codigo: str
    descripcion: Optional[str] = None


@dataclass
class ResultadoDiagnostico:
    """RF-12 a RF-16, ADR-005, ASR-02: el resultado determinístico del motor
    de cálculo (indice_global, nivel, puntaje y código de perfil cultural)
    se persiste de inmediato, antes de invocar al agente — ver
    Diagnostico.registrar_resultado_calculado(). Los campos narrativos
    (observacion, descripcion, lienzo_negocio, sintesis) los añade
    trust4p-servicio-agente y pueden quedar en None si el agente agota sus
    reintentos sin responder (el diagnóstico queda 'fallido' pero el
    resultado numérico ya calculado sigue siendo consultable)."""

    indice_global: Decimal
    nivel: int
    nivel_descripcion: str
    dimensiones: list[DimensionResultado]
    perfil_cultura: PerfilCulturaResultado
    lienzo_negocio: Optional[dict[str, str]] = None
    sintesis: Optional[str] = None
    generado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Recomendacion:
    """RF-16/RF-17/RF-21: conviven en el mismo arreglo recomendaciones
    generadas por el agente y registradas manualmente por un consultor
    (HU-022, Iteración 4) — origen y autor_id distinguen su procedencia
    desde ya para que esa historia no requiera migrar el esquema."""

    origen: str  # "agente" | "consultor"
    titulo: str
    contenido: str
    dimension_codigo: Optional[str] = None
    autor_id: Optional[str] = None
    prioridad: Optional[int] = None
    visible: bool = True
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


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
    resultado: Optional[ResultadoDiagnostico] = None
    recomendaciones: list[Recomendacion] = field(default_factory=list)
    motivo_fallo: Optional[str] = None
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

    def registrar_resultado_calculado(self, resultado: ResultadoDiagnostico) -> None:
        """ASR-02: persiste el resultado determinístico (índice, nivel,
        puntaje por dimensión, código de perfil cultural) ANTES de invocar
        al agente. El orden importa: si el servicio de inferencia falla
        después de este punto, el resultado numérico ya calculado no se
        pierde — solo queda pendiente la interpretación narrativa."""
        if self.estado != "completado":
            raise ValueError(
                f"El diagnóstico debe estar completado para calcular su resultado (estado actual: {self.estado})"
            )
        self.resultado = resultado

    def marcar_evaluado(
        self,
        perfil_cultura_descripcion: str,
        dimensiones_observaciones: dict[str, str],
        lienzo_negocio: dict[str, str],
        sintesis: str,
        recomendaciones: list[Recomendacion],
    ) -> None:
        """RF-36 a RF-40 (HU-038): añade el contenido narrativo que redactó
        trust4p-servicio-agente sobre el resultado determinístico ya
        persistido por registrar_resultado_calculado(). Solo procede desde
        'completado' y requiere que ese resultado exista."""
        if self.estado != "completado":
            raise ValueError(
                f"El diagnóstico debe estar completado para evaluarse (estado actual: {self.estado})"
            )
        if self.resultado is None:
            raise ValueError(
                "No se puede evaluar un diagnóstico sin un resultado calculado previamente"
            )
        self.resultado.perfil_cultura.descripcion = perfil_cultura_descripcion
        for dimension in self.resultado.dimensiones:
            if dimension.codigo in dimensiones_observaciones:
                dimension.observacion = dimensiones_observaciones[dimension.codigo]
        self.resultado.lienzo_negocio = lienzo_negocio
        self.resultado.sintesis = sintesis
        self.recomendaciones = recomendaciones
        self.estado = "evaluado"
        self.evaluado_en = datetime.now(timezone.utc)

    def marcar_fallido(self, motivo: str) -> None:
        """RF-40/ASR-02: si el agente no logra producir una respuesta válida
        tras sus reintentos, el diagnóstico queda en 'fallido' — pero el
        resultado determinístico ya persistido por
        registrar_resultado_calculado() (si llegó a calcularse) permanece
        intacto y consultable; solo falta la interpretación."""
        if self.estado != "completado":
            raise ValueError(
                f"El diagnóstico debe estar completado para marcarse como fallido (estado actual: {self.estado})"
            )
        self.estado = "fallido"
        self.motivo_fallo = motivo

    def marcar_cerrado(self) -> None:
        """RF-23 (HU-024): el consultor cierra el diagnóstico una vez
        concluido el acompañamiento. Procede desde 'evaluado' o 'fallido' —
        los dos estados terminales de la evaluación — nunca desde
        'completado' (todavía en proceso) ni 'borrador'."""
        if self.estado not in ("evaluado", "fallido"):
            raise ValueError(
                f"El diagnóstico debe estar evaluado o fallido para cerrarse (estado actual: {self.estado})"
            )
        self.estado = ESTADO_CERRADO
        self.cerrado_en = datetime.now(timezone.utc)
