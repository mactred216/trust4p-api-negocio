import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

ESTADOS_VALIDOS = {"borrador", "completado", "evaluado", "fallido", "cerrado"}
ESTADO_INICIAL = "borrador"
ESTADO_CERRADO = "cerrado"

# Plan de mejora: cada recomendación es una tarea con estado y fecha, pensada
# para que la empresa llegue al siguiente nivel de madurez.
ESTADOS_TAREA = ("pendiente", "en_curso", "completada")
ESTADO_TAREA_COMPLETADA = "completada"
# Tras avanzar este número de niveles sobre el del diagnóstico, se recomienda
# volver a diagnosticar.
NIVELES_PARA_NUEVO_DIAGNOSTICO = 2


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
    nombre: Optional[str] = None  # nombre del catálogo del modelo, si lo hay


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
    # Nombre del consultor al registrar, para que la empresa vea quién la escribió.
    autor_nombre: Optional[str] = None
    # Identificador estable para poder editarla como tarea.
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    estado: str = "pendiente"
    fecha_limite: Optional[date] = None
    # Nivel de madurez que ayuda a alcanzar; None = el siguiente al del diagnóstico.
    nivel_objetivo: Optional[int] = None
    actualizado_en: Optional[datetime] = None
    completada_en: Optional[datetime] = None


@dataclass
class AvanceNivel:
    """El consultor confirmó que la empresa alcanzó este nivel."""

    nivel: int
    alcanzado_en: datetime
    consultor_id: Optional[str] = None
    consultor_nombre: Optional[str] = None


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
    # Momento en que un reproceso lo devolvió a la cola de evaluación (C7).
    reabierto_en: Optional[datetime] = None
    evaluado_en: Optional[datetime] = None
    cerrado_en: Optional[datetime] = None
    # Nivel confirmado por el consultor; None = todavía el del diagnóstico.
    nivel_alcanzado: Optional[int] = None
    avances_de_nivel: list[AvanceNivel] = field(default_factory=list)

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
        nivel_maximo: Optional[int] = None,
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
        # Las del agente son las tareas para llegar al siguiente nivel; si la
        # empresa ya está en el máximo, no hay un nivel al que apuntar.
        siguiente = self.resultado.nivel + 1
        for recomendacion in recomendaciones:
            if recomendacion.nivel_objetivo is None and (
                nivel_maximo is None or siguiente <= nivel_maximo
            ):
                recomendacion.nivel_objetivo = siguiente
        # Las del consultor (registradas mientras el diagnóstico estaba
        # 'fallido', antes de un reproceso) se conservan; solo se reemplazan
        # las generadas por el agente.
        self.recomendaciones = [
            r for r in self.recomendaciones if r.origen != "agente"
        ] + recomendaciones
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

    def reabrir_para_reproceso(self) -> None:
        """RF-40/ASR-02: la evaluación diferida. Un diagnóstico 'fallido'
        vuelve a 'completado' para que se evalúe de nuevo; sus respuestas y su
        resultado calculado no se tocan (la evaluación los recalcula con la
        versión del modelo que ya tenía). Solo procede desde 'fallido': ni un
        diagnóstico en proceso, ni uno evaluado, ni uno cerrado."""
        if self.estado != "fallido":
            raise ValueError(
                f"Solo un diagnóstico fallido puede reprocesarse (estado actual: {self.estado})"
            )
        self.estado = "completado"
        self.motivo_fallo = None
        self.reabierto_en = datetime.now(timezone.utc)

    def agregar_recomendacion_consultor(
        self,
        autor_id: str,
        titulo: str,
        contenido: str,
        dimension_codigo: Optional[str] = None,
        visible: bool = True,
        autor_nombre: Optional[str] = None,
        fecha_limite: Optional[date] = None,
        nivel_objetivo: Optional[int] = None,
        nivel_maximo: Optional[int] = None,
    ) -> Recomendacion:
        """RF-21 (HU-022): el consultor complementa el resultado automático
        con recomendaciones propias. Solo sobre un diagnóstico ya evaluado o
        fallido, y nunca sobre uno cerrado (RF-23: el cierre bloquea nuevas
        recomendaciones, HU-024 CA-01)."""
        if self.estado == ESTADO_CERRADO:
            raise ValueError(
                "El diagnóstico está cerrado y no admite nuevas recomendaciones"
            )
        if self.estado not in ("evaluado", "fallido"):
            raise ValueError(
                f"El diagnóstico aún no admite recomendaciones (estado actual: {self.estado})"
            )
        if dimension_codigo is not None and (
            self.resultado is None
            or dimension_codigo not in {d.codigo for d in self.resultado.dimensiones}
        ):
            raise ValueError(
                f"La dimensión '{dimension_codigo}' no pertenece a este diagnóstico"
            )
        if nivel_objetivo is None and self.nivel_actual() is not None:
            siguiente = self.nivel_actual() + 1
            if nivel_maximo is None or siguiente <= nivel_maximo:
                nivel_objetivo = siguiente
        if nivel_objetivo is not None:
            self._validar_nivel_objetivo(nivel_objetivo, nivel_maximo)
        recomendacion = Recomendacion(
            origen="consultor",
            titulo=titulo,
            contenido=contenido,
            dimension_codigo=dimension_codigo,
            autor_id=autor_id,
            autor_nombre=autor_nombre,
            visible=visible,
            fecha_limite=fecha_limite,
            nivel_objetivo=nivel_objetivo,
        )
        self.recomendaciones.append(recomendacion)
        return recomendacion

    # ------------------------------------------------------------------
    # Plan de mejora: tareas y avance de nivel
    # ------------------------------------------------------------------

    def nivel_actual(self) -> Optional[int]:
        """El nivel que el consultor confirmó o, mientras no confirme ninguno, el
        del diagnóstico."""
        if self.nivel_alcanzado is not None:
            return self.nivel_alcanzado
        return self.resultado.nivel if self.resultado else None

    def nivel_objetivo_de(self, recomendacion: Recomendacion) -> Optional[int]:
        """Nivel al que apunta una tarea; las anteriores a esta función, que no lo
        guardaron, apuntan al siguiente del diagnóstico."""
        if recomendacion.nivel_objetivo is not None:
            return recomendacion.nivel_objetivo
        return self.resultado.nivel + 1 if self.resultado else None

    def recomendacion_por_id(self, recomendacion_id: str) -> Optional[Recomendacion]:
        for recomendacion in self.recomendaciones:
            if recomendacion.id == recomendacion_id:
                return recomendacion
        return None

    def nuevo_diagnostico_recomendado(self) -> bool:
        """Con el plan avanzado dos niveles sobre el diagnóstico, conviene volver a
        diagnosticar para medir el progreso real."""
        if self.resultado is None or self.nivel_alcanzado is None:
            return False
        return (
            self.nivel_alcanzado - self.resultado.nivel >= NIVELES_PARA_NUEVO_DIAGNOSTICO
        )

    def _exigir_plan_editable(self) -> None:
        if self.estado == ESTADO_CERRADO:
            raise ValueError(
                "El diagnóstico está cerrado y su plan de mejora ya no se puede modificar"
            )
        if self.estado != "evaluado" or self.resultado is None:
            raise ValueError(
                f"El plan de mejora solo se gestiona en un diagnóstico evaluado (estado actual: {self.estado})"
            )

    def _validar_nivel_objetivo(
        self, nivel_objetivo: int, nivel_maximo: Optional[int]
    ) -> None:
        actual = self.nivel_actual()
        if actual is not None and nivel_objetivo <= actual:
            raise ValueError(
                f"El nivel objetivo debe ser mayor que el nivel actual de la empresa ({actual})"
            )
        if nivel_maximo is not None and nivel_objetivo > nivel_maximo:
            raise ValueError(f"El nivel objetivo no puede superar el nivel máximo ({nivel_maximo})")

    def editar_recomendacion(
        self,
        recomendacion: Recomendacion,
        cambios: dict[str, Any],
        nivel_maximo: Optional[int] = None,
    ) -> None:
        """El consultor edita una tarea: título, contenido, estado, fecha límite,
        nivel objetivo y si se comparte con la empresa. Solo `cambios` se toca; una
        `fecha_limite` explícita en None la quita."""
        self._exigir_plan_editable()
        confirmado = self.nivel_actual()
        objetivo_actual = self.nivel_objetivo_de(recomendacion)
        nivel_ya_confirmado = (
            objetivo_actual is not None and confirmado is not None and objetivo_actual <= confirmado
        )

        if "estado" in cambios:
            nuevo = cambios["estado"]
            if nuevo not in ESTADOS_TAREA:
                raise ValueError(
                    f"Estado inválido; use uno de: {', '.join(ESTADOS_TAREA)}"
                )
            if (
                nuevo != recomendacion.estado
                and nivel_ya_confirmado
                and recomendacion.estado == ESTADO_TAREA_COMPLETADA
            ):
                raise ValueError(
                    f"El nivel {objetivo_actual} ya fue confirmado: su tarea completada no se puede reabrir"
                )
        if "nivel_objetivo" in cambios and cambios["nivel_objetivo"] is not None:
            if cambios["nivel_objetivo"] != objetivo_actual:
                self._validar_nivel_objetivo(cambios["nivel_objetivo"], nivel_maximo)

        ahora = datetime.now(timezone.utc)
        for campo in ("titulo", "contenido", "visible", "fecha_limite", "nivel_objetivo"):
            if campo in cambios and not (campo == "nivel_objetivo" and cambios[campo] is None):
                setattr(recomendacion, campo, cambios[campo])
        if "estado" in cambios and cambios["estado"] != recomendacion.estado:
            recomendacion.estado = cambios["estado"]
            recomendacion.completada_en = (
                ahora if cambios["estado"] == ESTADO_TAREA_COMPLETADA else None
            )
        recomendacion.actualizado_en = ahora

    def avanzar_nivel(
        self,
        consultor_id: Optional[str],
        consultor_nombre: Optional[str],
        nivel_maximo: Optional[int] = None,
    ) -> AvanceNivel:
        """El consultor confirma que la empresa alcanzó el siguiente nivel. Exige
        al menos una tarea (compartida con la empresa) para ese nivel y que todas
        estén completadas."""
        self._exigir_plan_editable()
        actual = self.nivel_actual()
        if nivel_maximo is not None and actual >= nivel_maximo:
            raise ValueError(f"La empresa ya está en el nivel máximo ({nivel_maximo})")
        objetivo = actual + 1
        tareas = [
            r
            for r in self.recomendaciones
            if r.visible and self.nivel_objetivo_de(r) == objetivo
        ]
        if not tareas:
            raise ValueError(
                f"No hay tareas para llegar al nivel {objetivo}: agregue al menos una antes de confirmarlo"
            )
        pendientes = [r for r in tareas if r.estado != ESTADO_TAREA_COMPLETADA]
        if pendientes:
            raise ValueError(
                f"Faltan {len(pendientes)} de {len(tareas)} tareas por completar para llegar al nivel {objetivo}"
            )
        avance = AvanceNivel(
            nivel=objetivo,
            alcanzado_en=datetime.now(timezone.utc),
            consultor_id=consultor_id,
            consultor_nombre=consultor_nombre,
        )
        self.nivel_alcanzado = objetivo
        self.avances_de_nivel.append(avance)
        return avance

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
