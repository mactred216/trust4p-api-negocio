import logging
import uuid
from datetime import datetime, timedelta, timezone

from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.puertos.cliente_servicio_agente import (ClienteServicioAgente,
                                                         ServicioAgenteError)
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.puertos.servicio_correo import ServicioCorreo
from src.dominio.servicios.motor_calculo import (RubricaNoCubreElIndice,
                                                 calcular_resultado)

registro = logging.getLogger("trust4p.evaluacion")

# C7: plazo durante el cual una evaluación iniciada se considera viva. Debe
# superar la espera máxima al servicio del agente (300 s por omisión) con
# margen; pasado este plazo sin terminar, se da por interrumpida.
PLAZO_EVALUACION_POR_DEFECTO = timedelta(minutes=10)
MOTIVO_INTERRUMPIDA = (
    "La evaluación se interrumpió antes de terminar (por ejemplo, porque la "
    "instancia del servicio se detuvo). El resultado calculado se conserva y "
    "el diagnóstico puede reprocesarse."
)


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
    el diagnóstico en un estado consultable y notificando por correo
    (RF-45: al representante si se evaluó; RF-38: al administrador si no)."""

    def __init__(
        self,
        repo_diagnostico: RepositorioDiagnostico,
        repo_modelo_madurez: RepositorioModeloMadurez,
        cliente_agente: ClienteServicioAgente,
        repo_usuario: RepositorioUsuario,
        servicio_correo: ServicioCorreo,
        repo_notificacion: RepositorioNotificacion,
        plazo_evaluacion: timedelta = PLAZO_EVALUACION_POR_DEFECTO,
    ):
        self._plazo = plazo_evaluacion
        self._diagnosticos = repo_diagnostico
        self._modelos = repo_modelo_madurez
        self._cliente_agente = cliente_agente
        self._usuarios = repo_usuario
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion

    async def ejecutar_en_serie(self, diagnosticos_ids: list[str]) -> None:
        """Evaluación diferida de varios diagnósticos (reproceso de los
        'fallido'): uno tras otro, sin avisar al administrador de cada fallo
        —el reproceso lo pidió él— y sin que el error de uno detenga a los
        demás. Si el servicio de evaluación sigue caído, el cortocircuito
        deja pasar los restantes al instante."""
        for diagnostico_id in diagnosticos_ids:
            try:
                await self.ejecutar(diagnostico_id, notificar_fallo=False)
            except Exception:
                registro.exception(
                    "Falló el reproceso del diagnóstico %s", diagnostico_id
                )

    async def ejecutar(self, diagnostico_id: str, notificar_fallo: bool = True) -> None:
        """C7: antes de evaluar se reclama el diagnóstico en una operación
        atómica. Si ya hay una evaluación vigente (un reproceso pedido dos
        veces, o dos instancias), esta no corre: nunca se evalúa dos veces a
        la vez ni se pisan los resultados."""
        token = uuid.uuid4().hex
        vence_en = datetime.now(timezone.utc) + self._plazo
        if not await self._diagnosticos.reclamar_evaluacion(
            diagnostico_id, token, vence_en
        ):
            registro.info(
                "Evaluación del diagnóstico %s omitida: ya hay otra en curso o "
                "no está pendiente",
                diagnostico_id,
            )
            return
        try:
            await self._evaluar(diagnostico_id, notificar_fallo)
        finally:
            await self._diagnosticos.liberar_evaluacion(diagnostico_id, token)

    async def _evaluar(self, diagnostico_id: str, notificar_fallo: bool) -> None:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            return

        modelo = await self._modelos.obtener_por_version(diagnostico.modelo_version)
        if modelo is None:
            diagnostico.marcar_fallido(
                "La versión del modelo de madurez aplicada a este diagnóstico ya no existe"
            )
            await self._diagnosticos.actualizar(diagnostico)
            if notificar_fallo:
                await self._notificar_fallido(diagnostico)
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
            if notificar_fallo:
                await self._notificar_fallido(diagnostico)
            return

        # ASR-02: se calcula y persiste el índice antes de invocar al
        # agente — no al final, ni junto con la respuesta del agente — para
        # que un fallo del servicio de inferencia nunca arrastre consigo el
        # resultado numérico ya calculado.
        # RF-14: si el administrador definió este perfil en el catálogo del
        # modelo, su nombre y descripción son los del resultado; si no, la
        # descripción la redacta el agente.
        perfil_catalogo = modelo.perfil_cultura_para(
            resultado_calculo.perfil_cultural.codigo
        )
        resultado = ResultadoDiagnostico(
            indice_global=resultado_calculo.indice_global,
            nivel=resultado_calculo.nivel,
            nivel_descripcion=resultado_calculo.nivel_descripcion,
            dimensiones=[
                DimensionResultado(codigo=d.dimension_codigo, puntaje=d.puntaje)
                for d in resultado_calculo.dimensiones
            ],
            perfil_cultura=PerfilCulturaResultado(
                codigo=resultado_calculo.perfil_cultural.codigo,
                nombre=perfil_catalogo.nombre if perfil_catalogo else None,
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
            if notificar_fallo:
                await self._notificar_fallido(diagnostico)
            return

        diagnostico.marcar_evaluado(
            perfil_cultura_descripcion=(
                perfil_catalogo.descripcion
                if perfil_catalogo
                else respuesta_agente.perfil_cultura_descripcion
            ),
            dimensiones_observaciones=respuesta_agente.dimensiones_observaciones,
            lienzo_negocio=respuesta_agente.lienzo_negocio,
            sintesis=respuesta_agente.sintesis,
            recomendaciones=respuesta_agente.recomendaciones,
            nivel_maximo=max((n.nivel for n in modelo.niveles), default=None),
        )
        await self._diagnosticos.actualizar(diagnostico)
        await self._notificar_evaluado(diagnostico)

    async def _notificar_evaluado(self, diagnostico: Diagnostico) -> None:
        representante = await self._usuarios.obtener_por_id(diagnostico.usuario_id)
        if representante is None:
            return
        await enviar_notificacion(
            self._correo,
            self._notificaciones,
            usuario_id=representante.id,
            correo_destino=representante.correo,
            tipo="diagnostico_evaluado",
            asunto="Trust 4P - Su diagnóstico ya tiene resultado",
            contenido=(
                f"Hola {representante.nombres},\n\n"
                f"El diagnóstico N.° {diagnostico.consecutivo} de {diagnostico.empresa_nombre} "
                "ya fue evaluado. Ingrese a la plataforma para consultar el resultado."
            ),
        )

    async def _notificar_fallido(self, diagnostico: Diagnostico) -> None:
        administradores = await self._usuarios.listar_por_rol("administrador")
        for administrador in administradores:
            await enviar_notificacion(
                self._correo,
                self._notificaciones,
                usuario_id=administrador.id,
                correo_destino=administrador.correo,
                tipo="diagnostico_fallido",
                asunto="Trust 4P - Un diagnóstico quedó pendiente de evaluación",
                contenido=(
                    f"El diagnóstico N.° {diagnostico.consecutivo} de "
                    f"{diagnostico.empresa_nombre} no pudo evaluarse: {diagnostico.motivo_fallo}"
                ),
            )


class RecuperarEvaluacionesInterrumpidas:
    """C7, ASR-02: la evaluación corre en segundo plano dentro de la instancia
    que recibió la petición. Si esa instancia termina antes de acabar, el
    diagnóstico quedaría 'completado' para siempre. Al arrancar el servicio
    (y antes de reprocesar pendientes) los que llevan más del plazo en cola
    sin evaluación vigente pasan a 'fallido', con su motivo, y quedan listos
    para reprocesarse. No se relanzan solos, para no duplicar evaluaciones."""

    def __init__(
        self,
        repo_diagnostico: RepositorioDiagnostico,
        plazo_evaluacion: timedelta = PLAZO_EVALUACION_POR_DEFECTO,
    ):
        self._diagnosticos = repo_diagnostico
        self._plazo = plazo_evaluacion

    async def ejecutar(self) -> list[str]:
        limite = datetime.now(timezone.utc) - self._plazo
        ids = await self._diagnosticos.marcar_evaluaciones_interrumpidas(
            limite, MOTIVO_INTERRUMPIDA
        )
        if ids:
            registro.warning(
                "Evaluaciones interrumpidas marcadas como fallidas: %s", ", ".join(ids)
            )
        return ids
