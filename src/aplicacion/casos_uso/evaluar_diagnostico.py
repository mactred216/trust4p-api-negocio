from src.dominio.entidades.diagnostico import (DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.puertos.cliente_servicio_agente import (ClienteServicioAgente,
                                                         ServicioAgenteError)
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.servicios.motor_calculo import (RubricaNoCubreElIndice,
                                                 calcular_resultado)


class EvaluarDiagnostico:
    """RF-36 a RF-40 (HU-038), ASR-02: orquesta la evaluación de un
    diagnóstico ya completado. Calcula el resultado determinístico con el
    motor de cálculo (ADR-005) y lo persiste de inmediato —antes de invocar
    al agente—, de modo que una caída posterior del servicio de inferencia
    nunca comprometa el índice ya calculado. Solo entonces delega en
    trust4p-servicio-agente la redacción del contenido narrativo. Se
    ejecuta en segundo plano tras completar el diagnóstico (ASR-02:
    interpretación encolada y procesada de forma asíncrona), por lo que no
    tiene a quién reportarle una excepción: todo fallo se resuelve dejando
    el diagnóstico en un estado consultable."""

    def __init__(
        self,
        repo_diagnostico: RepositorioDiagnostico,
        repo_modelo_madurez: RepositorioModeloMadurez,
        cliente_agente: ClienteServicioAgente,
    ):
        self._diagnosticos = repo_diagnostico
        self._modelos = repo_modelo_madurez
        self._cliente_agente = cliente_agente

    async def ejecutar(self, diagnostico_id: str) -> None:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            return

        modelo = await self._modelos.obtener_por_version(diagnostico.modelo_version)
        if modelo is None:
            diagnostico.marcar_fallido(
                "La versión del modelo de madurez aplicada a este diagnóstico ya no existe"
            )
            await self._diagnosticos.actualizar(diagnostico)
            return

        try:
            resultado_calculo = calcular_resultado(diagnostico, modelo)
        except RubricaNoCubreElIndice as e:
            # No es un fallo del agente (ASR-02 no aplica aquí: no hay nada
            # que persistir todavía) sino de la configuración del modelo o
            # de una respuesta fuera de rango. Igual se deja el diagnóstico
            # en un estado consultable, nunca en 'completado' colgado sin
            # explicación.
            diagnostico.marcar_fallido(str(e))
            await self._diagnosticos.actualizar(diagnostico)
            return

        # ASR-02: se calcula y persiste el índice antes de invocar al
        # agente — no al final, ni junto con la respuesta del agente — para
        # que un fallo del servicio de inferencia nunca arrastre consigo el
        # resultado numérico ya calculado.
        resultado = ResultadoDiagnostico(
            indice_global=resultado_calculo.indice_global,
            nivel=resultado_calculo.nivel,
            nivel_descripcion=resultado_calculo.nivel_descripcion,
            dimensiones=[
                DimensionResultado(codigo=d.dimension_codigo, puntaje=d.puntaje)
                for d in resultado_calculo.dimensiones
            ],
            perfil_cultura=PerfilCulturaResultado(
                codigo=resultado_calculo.perfil_cultural.codigo
            ),
        )
        diagnostico.registrar_resultado_calculado(resultado)
        await self._diagnosticos.actualizar(diagnostico)

        try:
            respuesta_agente = await self._cliente_agente.evaluar(
                diagnostico, modelo, resultado_calculo
            )
        except ServicioAgenteError as e:
            diagnostico.marcar_fallido(str(e))
            await self._diagnosticos.actualizar(diagnostico)
            return

        diagnostico.marcar_evaluado(
            perfil_cultura_descripcion=respuesta_agente.perfil_cultura_descripcion,
            dimensiones_observaciones=respuesta_agente.dimensiones_observaciones,
            lienzo_negocio=respuesta_agente.lienzo_negocio,
            sintesis=respuesta_agente.sintesis,
            recomendaciones=respuesta_agente.recomendaciones,
        )
        await self._diagnosticos.actualizar(diagnostico)
