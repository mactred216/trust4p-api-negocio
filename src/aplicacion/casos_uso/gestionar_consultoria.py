from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.aplicacion.servicios.notificar import enviar_notificacion
from src.dominio.entidades.diagnostico import Diagnostico, Recomendacion
from src.dominio.entidades.usuario import Usuario
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
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
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico
        self._correo = servicio_correo
        self._notificaciones = repo_notificacion

    async def ejecutar(
        self,
        consultor_id: str,
        diagnostico_id: str,
        titulo: str,
        contenido: str,
        dimension_codigo: Optional[str] = None,
        visible: bool = True,
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
