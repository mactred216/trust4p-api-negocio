from datetime import datetime, timezone
from typing import Optional

from src.aplicacion.casos_uso.gestionar_consultoria import (_como_utc,
                                                            _obtener_consultor)
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.servicios.indicadores_agregados import (
    TAMANOS, FilaExportacion, IndicadoresAgregados, MuestraEmpresa,
    calcular_indicadores, clasificar_tamano, filas_para_exportacion,
    filtrar_muestras)

ESTADOS_CON_RESULTADO = ("evaluado", "fallido", "cerrado")


class FiltroInvalido(Exception):
    pass


def _validar_tamano(tamano: Optional[str]) -> None:
    if tamano is not None and tamano not in TAMANOS:
        raise FiltroInvalido(f"Tamaño inválido; use uno de: {', '.join(TAMANOS)}")


async def _recolectar_muestras(
    repo_empresa: RepositorioEmpresa,
    repo_diagnostico: RepositorioDiagnostico,
    empresa_ids: list[str],
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
) -> list[MuestraEmpresa]:
    """Una muestra por empresa: su diagnóstico más reciente con resultado
    calculado (el motor determinístico ya lo persistió, ASR-02)."""
    muestras = []
    for empresa_id in empresa_ids:
        empresa = await repo_empresa.obtener_por_id(empresa_id)
        if empresa is None:
            continue
        candidatos = [
            d
            for d in await repo_diagnostico.listar_por_empresa(empresa_id)
            if d.estado in ESTADOS_CON_RESULTADO and d.resultado is not None
        ]
        if fecha_desde is not None:
            candidatos = [
                d
                for d in candidatos
                if _como_utc(d.iniciado_en) >= _como_utc(fecha_desde)
            ]
        if fecha_hasta is not None:
            candidatos = [
                d
                for d in candidatos
                if _como_utc(d.iniciado_en) <= _como_utc(fecha_hasta)
            ]
        ultimo = max(candidatos, key=lambda d: d.consecutivo, default=None)
        if ultimo is None:
            continue
        muestras.append(
            MuestraEmpresa(
                sector_codigo=empresa.sector.codigo,
                sector_nombre=empresa.sector.nombre,
                tamano=clasificar_tamano(empresa.numero_empleados),
                nivel=ultimo.resultado.nivel,
                indice_global=ultimo.resultado.indice_global,
                puntajes_dimension={
                    d.codigo: d.puntaje for d in ultimo.resultado.dimensiones
                },
            )
        )
    return muestras


class ConsultarIndicadoresAgregados:
    """RF-22 (HU-023): tablero de indicadores agregados sobre las empresas
    con asignación vigente del consultor, filtrable por sector y tamaño. Si
    el filtro agrupa menos de tres empresas no se presenta el detalle."""

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
        sector_codigo: Optional[str] = None,
        tamano: Optional[str] = None,
    ) -> IndicadoresAgregados:
        _validar_tamano(tamano)
        consultor = await _obtener_consultor(self._usuarios, consultor_id)
        muestras = await _recolectar_muestras(
            self._empresas,
            self._diagnosticos,
            consultor.empresas_asignadas_vigentes(),
        )
        return calcular_indicadores(filtrar_muestras(muestras, sector_codigo, tamano))


class ExportarDatosAgregados:
    """RF-46 (HU-023): el administrador exporta datos agregados y anonimizados
    de todas las empresas, con filtros de fecha, sector y tamaño."""

    def __init__(
        self, repo_empresa: RepositorioEmpresa, repo_diagnostico: RepositorioDiagnostico
    ):
        self._empresas = repo_empresa
        self._diagnosticos = repo_diagnostico

    async def ejecutar(
        self,
        sector_codigo: Optional[str] = None,
        tamano: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
    ) -> list[FilaExportacion]:
        _validar_tamano(tamano)
        empresas = await self._empresas.listar_todas()
        muestras = await _recolectar_muestras(
            self._empresas,
            self._diagnosticos,
            [e.id for e in empresas],
            fecha_desde,
            fecha_hasta,
        )
        return filas_para_exportacion(filtrar_muestras(muestras, sector_codigo, tamano))
