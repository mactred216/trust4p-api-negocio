import os

import httpx

from src.dominio.entidades.diagnostico import Diagnostico, Recomendacion
from src.dominio.entidades.modelo_madurez import ModeloMadurez
from src.dominio.puertos.cliente_servicio_agente import (ClienteServicioAgente,
                                                         RespuestaAgente,
                                                         ServicioAgenteError)
from src.dominio.servicios.motor_calculo import ResultadoCalculo
from src.infraestructura.clientes.interruptor_circuito import     InterruptorDeCircuito

# El agente responde en segundos, pero su servicio escala a cero: la primera
# evaluación tras un periodo de inactividad paga además el arranque en frío de
# la instancia. Con 60 s el plazo se agotaba ahí y el diagnóstico quedaba sin
# interpretación aunque el agente la hubiera generado bien.
TIEMPO_ESPERA_POR_DEFECTO = "300"
RUTA_EVALUACIONES = "/v1/evaluaciones"

# ASR-02: tras UMBRAL fallos de disponibilidad seguidos se deja de llamar al
# agente durante ENFRIAMIENTO segundos; los diagnósticos que lleguen en ese
# lapso quedan 'fallido' al instante (con su índice ya calculado) y se
# reprocesan después, en vez de esperar cada uno el plazo completo.
INTERRUPTOR_AGENTE = InterruptorDeCircuito(
    umbral=int(os.getenv("AGENTE_CIRCUITO_UMBRAL", "3")),
    enfriamiento=float(os.getenv("AGENTE_CIRCUITO_ENFRIAMIENTO_SEGUNDOS", "60")),
)


class ClienteServicioAgenteHTTP(ClienteServicioAgente):
    """Adaptador HTTP hacia trust4p-servicio-agente. Autenticación de
    servicio a servicio vía X-Api-Key (API_KEY_SERVICIOS) — distinta de la
    sesión de usuario, ya que quien invoca es este backend, no un
    navegador."""

    def __init__(
        self,
        url_base: str | None = None,
        api_key: str | None = None,
        tiempo_espera: float | None = None,
        interruptor: InterruptorDeCircuito | None = None,
    ):
        self._url_base = (url_base or os.getenv("SERVICIO_AGENTE_URL") or "").rstrip(
            "/"
        )
        self._api_key = api_key or os.getenv("API_KEY_SERVICIOS")
        self._tiempo_espera = tiempo_espera or float(
            os.getenv("AGENTE_TIEMPO_ESPERA_SEGUNDOS", TIEMPO_ESPERA_POR_DEFECTO)
        )
        self._interruptor = interruptor or INTERRUPTOR_AGENTE

    async def evaluar(
        self,
        diagnostico: Diagnostico,
        modelo: ModeloMadurez,
        resultado_calculo: ResultadoCalculo,
    ) -> RespuestaAgente:
        payload = self._construir_solicitud(diagnostico, modelo, resultado_calculo)
        if not self._interruptor.permitir():
            raise ServicioAgenteError(
                "El servicio de evaluación asistida está temporalmente fuera de "
                "servicio (cortocircuito abierto tras fallos consecutivos); la "
                "evaluación puede reprocesarse en unos "
                f"{self._interruptor.segundos_para_reintento()} segundos"
            )
        try:
            async with httpx.AsyncClient(timeout=self._tiempo_espera) as cliente:
                respuesta = await cliente.post(
                    f"{self._url_base}{RUTA_EVALUACIONES}",
                    json=payload,
                    headers={"X-Api-Key": self._api_key or ""},
                )
        except httpx.HTTPError as e:
            self._interruptor.registrar_fallo()
            raise ServicioAgenteError(
                f"Error de red al invocar al servicio del agente: {e}"
            )

        if respuesta.status_code != 200:
            # Solo cuentan como caída del servicio los errores del servidor y la
            # saturación (429); un 4xx indica que el servicio respondió.
            if respuesta.status_code >= 500 or respuesta.status_code == 429:
                self._interruptor.registrar_fallo()
            else:
                self._interruptor.registrar_exito()
            raise ServicioAgenteError(
                f"El servicio del agente respondió {respuesta.status_code}: {respuesta.text}"
            )

        try:
            respuesta_agente = self._a_respuesta(respuesta.json())
        except (KeyError, TypeError, ValueError) as e:
            self._interruptor.registrar_fallo()
            raise ServicioAgenteError(
                f"El servicio del agente devolvió una respuesta con formato inválido: {e!r}"
            )
        self._interruptor.registrar_exito()
        return respuesta_agente

    @staticmethod
    def _a_respuesta(datos: dict) -> RespuestaAgente:
        return RespuestaAgente(
            perfil_cultura_descripcion=datos["perfil_cultura_descripcion"],
            dimensiones_observaciones=datos["dimensiones_observaciones"],
            lienzo_negocio=datos["lienzo_negocio"],
            sintesis=datos["sintesis"],
            recomendaciones=[
                Recomendacion(
                    origen="agente",
                    dimension_codigo=r["dimension_codigo"],
                    titulo=r["titulo"],
                    contenido=r["contenido"],
                    prioridad=r["prioridad"],
                    autor_id=None,
                    visible=True,
                )
                for r in datos["recomendaciones"]
            ],
        )

    def _construir_solicitud(
        self,
        diagnostico: Diagnostico,
        modelo: ModeloMadurez,
        resultado_calculo: ResultadoCalculo,
    ) -> dict:
        """R-13 (dato con destino externo): solo viajan empresa_id y el
        contenido del diagnóstico — nunca razón social, NIT ni datos de
        contacto (ADR-005/saneador de trust4p-servicio-agente valida esto
        también en el otro extremo, defensa en profundidad)."""
        preguntas_por_codigo = {p.codigo: p for p in modelo.preguntas}
        return {
            "diagnostico_id": diagnostico.id,
            "empresa_id": diagnostico.empresa_id,
            "modelo_version": diagnostico.modelo_version,
            "resultado_calculo": {
                "indice_global": str(resultado_calculo.indice_global),
                "nivel": resultado_calculo.nivel,
                "nivel_nombre": resultado_calculo.nivel_nombre,
                "nivel_descripcion": resultado_calculo.nivel_descripcion,
                "dimensiones": [
                    {"codigo": d.dimension_codigo, "puntaje": str(d.puntaje)}
                    for d in resultado_calculo.dimensiones
                ],
                "perfil_cultural": {"codigo": resultado_calculo.perfil_cultural.codigo},
            },
            "respuestas": [
                {
                    "pregunta_codigo": r.pregunta_codigo,
                    "dimension_codigo": r.dimension_codigo,
                    "enunciado": preguntas_por_codigo[r.pregunta_codigo].enunciado,
                    "tipo": preguntas_por_codigo[r.pregunta_codigo].tipo,
                    "opciones_codigo": r.opciones_codigo,
                    "valor": str(r.valor) if r.valor is not None else None,
                    "texto": r.texto,
                }
                for r in diagnostico.respuestas
                if r.pregunta_codigo in preguntas_por_codigo
            ],
            "dimensiones_modelo": [
                {
                    "codigo": d.codigo,
                    "nombre": d.nombre,
                    "peso": str(d.peso),
                    "orden": d.orden,
                }
                for d in modelo.dimensiones
            ],
            "niveles_modelo": [
                {
                    "nivel": n.nivel,
                    "nombre": n.nombre,
                    "descripcion": n.descripcion,
                    "umbral_min": str(n.umbral_min),
                    "umbral_max": str(n.umbral_max),
                }
                for n in modelo.niveles
            ],
        }
