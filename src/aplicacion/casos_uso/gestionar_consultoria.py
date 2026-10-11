from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.diagnostico import (AvanceNivel, Diagnostico,
                                               Recomendacion)
from src.dominio.entidades.modelo_madurez import ModeloMadurez
from src.dominio.entidades.usuario import Usuario
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.puertos.repositorio_notificacion import \
    RepositorioNotificacion
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.puertos.servicio_correo import ServicioCorreo


@dataclass
class ResumenEmpresaAsignada:
    empresa_id: str
    empresa_nombre: str
    diagnostico_id: Optional[str]
    consecutivo: Optional[int]
    estado: Optional[str]
    iniciado_en: Optional[datetime]
    nivel: Optional[int]
    indice_global: Optional[Decimal]


def _como_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


async def _obtener_consultor(
    repo_usuario: RepositorioUsuario, consultor_id: str
) -> Usuario:
    consultor = await repo_usuario.obtener_por_id(consultor_id)
    if consultor is None:
        raise AccesoNoAutorizado()
    return consultor


async def _nivel_maximo(
    repo_modelo: Optional[RepositorioModeloMadurez], diagnostico: Diagnostico
) -> Optional[int]:
    """Nivel más alto de la rúbrica con que se evaluó el diagnóstico."""
    if repo_modelo is None:
        return None
    modelo = await repo_modelo.obtener_por_version(diagnostico.modelo_version)
    if modelo is None or not modelo.niveles:
        return None
    return max(n.nivel for n in modelo.niveles)


def _exigir_asignacion(consultor: Usuario, empresa_id: str) -> None:
    """ASR-03/RF-20: un consultor solo ve empresas con asignación vigente."""
    if empresa_id not in consultor.empresas_asignadas_vigentes():
        raise AccesoNoAutorizado()


class ListarEmpresasAsignadas:
    """RF-19 (HU-020): empresas con asignación vigente del consultor, con el
    estado y el nivel de su diagnóstico más reciente, filtrables por estado
    y por rango de fechas de inicio."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_empresa: RepositorioEmpresa,
        repo_diagnostico: RepositorioDiagnostico,
    ):
        self._usuarios = repo_usuario
        self._empresas = repo_empresa
        self._diagnosticos = repo_diagnostico

    async def ejecutar(
        self,
        consultor_id: str,
        estado: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> list[ResumenEmpresaAsignada]:
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        resumenes = []
        for empresa_id in consultor.empresas_asignadas_vigentes():
            empresa = await self._empresas.obtener_por_id(empresa_id)
            if empresa is None:
                continue
            diagnosticos = await self._diagnosticos.listar_por_empresa(empresa_id)
            ultimo = max(diagnosticos, key=lambda d: d.consecutivo, default=None)
            resumen = ResumenEmpresaAsignada(
                empresa_id=empresa_id,
                empresa_nombre=empresa.nombre,
                diagnostico_id=ultimo.id if ultimo else None,
                consecutivo=ultimo.consecutivo if ultimo else None,
                estado=ultimo.estado if ultimo else None,
                iniciado_en=ultimo.iniciado_en if ultimo else None,
                nivel=ultimo.resultado.nivel if ultimo and ultimo.resultado else None,
                indice_global=(
                    ultimo.resultado.indice_global
                    if ultimo and ultimo.resultado
                    else None
                ),
            )
            if self._cumple_filtros(resumen, estado, fecha_desde, fecha_hasta):
                resumenes.append(resumen)
        return resumenes

    @staticmethod
    def _cumple_filtros(
        resumen: ResumenEmpresaAsignada,
        estado: Optional[str],
        fecha_desde: Optional[datetime],
        fecha_hasta: Optional[datetime],
    ) -> bool:
        if estado is not None and resumen.estado != estado:
            return False
        if fecha_desde is not None or fecha_hasta is not None:
            if resumen.iniciado_en is None:
                return False
            iniciado = _como_utc(resumen.iniciado_en)
            if fecha_desde is not None and iniciado < _como_utc(fecha_desde):
                return False
            if fecha_hasta is not None and iniciado > _como_utc(fecha_hasta):
                return False
        return True


class ListarDiagnosticosDeEmpresaAsignada:
    """RF-20 (HU-021): histórico de diagnósticos de una empresa asignada."""

    def __init__(
        self, repo_usuario: RepositorioUsuario, repo_diagnostico: RepositorioDiagnostico
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico

    async def ejecutar(self, consultor_id: str, empresa_id: str) -> list[Diagnostico]:
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        _exigir_asignacion(consultor, empresa_id)
        return await self._diagnosticos.listar_por_empresa(empresa_id)


class ConsultarDiagnosticoAsignado:
    """RF-20 (HU-021): respuestas y resultados de un diagnóstico, únicamente
    de empresas que el consultor tiene asignadas."""

    def __init__(
        self, repo_usuario: RepositorioUsuario, repo_diagnostico: RepositorioDiagnostico
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico

    async def ejecutar(self, consultor_id: str, diagnostico_id: str) -> Diagnostico:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        _exigir_asignacion(consultor, diagnostico.empresa_id)
        return diagnostico


class RegistrarRecomendacion:
    """RF-21 (HU-022): el consultor registra una recomendación sobre un
    diagnóstico de una empresa asignada y se notifica al representante
    (RF-45)."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_diagnostico: RepositorioDiagnostico,
        servicio_correo: ServicioCorreo,
        repo_notificacion: RepositorioNotificacion,
        repo_modelo: Optional[RepositorioModeloMadurez] = None,
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion
        self._modelos = repo_modelo

    async def ejecutar(
        self,
        consultor_id: str,
        diagnostico_id: str,
        titulo: str,
        contenido: str,
        dimension_codigo: Optional[str] = None,
        visible: bool = True,
        fecha_limite: Optional[date] = None,
        nivel_objetivo: Optional[int] = None,
    ) -> Recomendacion:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        _exigir_asignacion(consultor, diagnostico.empresa_id)

        recomendacion = diagnostico.agregar_recomendacion_consultor(
            autor_id=consultor_id,
            titulo=titulo,
            contenido=contenido,
            dimension_codigo=dimension_codigo,
            visible=visible,
            autor_nombre=f"{consultor.nombres} {consultor.apellidos}".strip(),
            fecha_limite=fecha_limite,
            nivel_objetivo=nivel_objetivo,
            nivel_maximo=await _nivel_maximo(self._modelos, diagnostico),
        )
        await self._diagnosticos.actualizar(diagnostico)

        if visible:
            await self._notificar_representante(diagnostico, consultor, titulo)
        return recomendacion

    async def _notificar_representante(
        self, diagnostico: Diagnostico, consultor: Usuario, titulo: str
    ) -> None:
        representante = await self._usuarios.obtener_por_id(diagnostico.usuario_id)
        if representante is None:
            return
        await enviar_notificacion(
            self._correo,
            self._notificaciones,
            usuario_id=representante.id,
            correo_destino=representante.correo,
            tipo="recomendacion_registrada",
            asunto="Trust 4P - Su consultor registró una recomendación",
            contenido=(
                f"Hola {representante.nombres},\n\n"
                f"{consultor.nombres} {consultor.apellidos} registró la recomendación "
                f"'{titulo}' sobre el diagnóstico N.° {diagnostico.consecutivo}. "
                "Ingrese a la plataforma para consultarla."
            ),
        )


class TareaNoEncontrada(Exception):
    pass


def resumen_de_tarea(diagnostico: Diagnostico, recomendacion: Recomendacion) -> dict:
    """Los campos de una tarea que se comparan en la bitácora."""
    return {
        "titulo": recomendacion.titulo,
        "contenido": recomendacion.contenido,
        "estado": recomendacion.estado,
        "fecha_limite": (
            recomendacion.fecha_limite.isoformat() if recomendacion.fecha_limite else None
        ),
        "nivel_objetivo": diagnostico.nivel_objetivo_de(recomendacion),
        "visible": recomendacion.visible,
    }


@dataclass
class CambioDeTarea:
    recomendacion: Recomendacion
    diagnostico: Diagnostico
    antes: dict
    despues: dict


class EditarTarea:
    """El consultor asignado gestiona las tareas del plan de mejora de la empresa:
    cambia su estado, su fecha límite, su nivel objetivo, su texto o si se comparte
    con la empresa."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_diagnostico: RepositorioDiagnostico,
        repo_modelo: Optional[RepositorioModeloMadurez] = None,
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico
        self._modelos = repo_modelo

    async def ejecutar(
        self, consultor_id: str, diagnostico_id: str, tarea_id: str, cambios: dict
    ) -> CambioDeTarea:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        _exigir_asignacion(consultor, diagnostico.empresa_id)
        recomendacion = diagnostico.recomendacion_por_id(tarea_id)
        if recomendacion is None:
            raise TareaNoEncontrada()

        antes = resumen_de_tarea(diagnostico, recomendacion)
        diagnostico.editar_recomendacion(
            recomendacion, cambios, nivel_maximo=await _nivel_maximo(self._modelos, diagnostico)
        )
        await self._diagnosticos.actualizar(diagnostico)
        return CambioDeTarea(
            recomendacion=recomendacion,
            diagnostico=diagnostico,
            antes=antes,
            despues=resumen_de_tarea(diagnostico, recomendacion),
        )


class AvanzarNivel:
    """El consultor confirma que la empresa alcanzó el siguiente nivel de madurez
    al completar las tareas que lo llevaban hasta él. Avisa al representante."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_diagnostico: RepositorioDiagnostico,
        repo_modelo: RepositorioModeloMadurez,
        servicio_correo: ServicioCorreo,
        repo_notificacion: RepositorioNotificacion,
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico
        self._modelos = repo_modelo
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion

    async def ejecutar(
        self, consultor_id: str, diagnostico_id: str
    ) -> tuple[Diagnostico, AvanceNivel, int]:
        """Devuelve el diagnóstico, el avance y el nivel de partida."""
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        _exigir_asignacion(consultor, diagnostico.empresa_id)
        modelo = await self._modelos.obtener_por_version(diagnostico.modelo_version)
        nivel_maximo = max((n.nivel for n in modelo.niveles), default=None) if modelo else None

        nivel_anterior = diagnostico.nivel_actual()
        avance = diagnostico.avanzar_nivel(
            consultor_id,
            f"{consultor.nombres} {consultor.apellidos}".strip(),
            nivel_maximo,
        )
        await self._diagnosticos.actualizar(diagnostico)
        await self._notificar_representante(diagnostico, avance, modelo)
        return diagnostico, avance, nivel_anterior

    async def _notificar_representante(
        self, diagnostico: Diagnostico, avance: AvanceNivel, modelo: Optional[ModeloMadurez]
    ) -> None:
        representante = await self._usuarios.obtener_por_id(diagnostico.usuario_id)
        if representante is None:
            return
        nombre = next((n.nombre for n in (modelo.niveles if modelo else []) if n.nivel == avance.nivel), None)
        nivel = f"{avance.nivel} ({nombre})" if nombre else str(avance.nivel)
        recomendacion = (
            " Se recomienda realizar un nuevo diagnóstico para medir el progreso."
            if diagnostico.nuevo_diagnostico_recomendado()
            else " Revise en su plan de mejora las tareas para el siguiente nivel."
        )
        await enviar_notificacion(
            self._correo,
            self._notificaciones,
            usuario_id=representante.id,
            correo_destino=representante.correo,
            tipo="nivel_alcanzado",
            asunto="Trust 4P - Su empresa alcanzó un nuevo nivel de madurez",
            contenido=(
                f"Hola {representante.nombres},\n\n"
                f"{avance.consultor_nombre or 'Su consultor'} confirmó que {diagnostico.empresa_nombre} "
                f"alcanzó el nivel {nivel} de madurez de innovación.{recomendacion}"
            ),
        )


class ObtenerCuestionarioAsignado:
    """HU-021: estructura del cuestionario (enunciados, opciones y rúbrica) de
    la versión aplicada a un diagnóstico de una empresa asignada, para que el
    consultor pueda leer las respuestas con su contexto."""

    def __init__(
        self,
        repo_usuario: RepositorioUsuario,
        repo_diagnostico: RepositorioDiagnostico,
        repo_modelo_madurez: RepositorioModeloMadurez,
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico
        self._modelos = repo_modelo_madurez

    async def ejecutar(self, consultor_id: str, diagnostico_id: str) -> ModeloMadurez:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        _exigir_asignacion(consultor, diagnostico.empresa_id)
        modelo = await self._modelos.obtener_por_version(diagnostico.modelo_version)
        if modelo is None:
            raise ValueError(
                "La versión del modelo aplicada a este diagnóstico ya no existe"
            )
        return modelo
