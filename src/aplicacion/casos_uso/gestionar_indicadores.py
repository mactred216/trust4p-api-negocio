from datetime import datetime, timezone
from typing import Optional

from src.aplicacion.casos_uso.gestionar_consultoria import (_como_utc,
                                                            _obtener_consultor)
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.servicios.indicadores_agregados import (
    MINIMO_EMPRESAS, TAMANOS, FilaExportacion, IndicadoresAgregados,
    MuestraEmpresa, calcular_indicadores, calcular_indicadores_empresa,
    clasificar_tamano, filas_para_exportacion, filtrar_muestras)

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
                empresa_id=empresa_id,
                empresa_nombre=empresa.nombre,
            )
        )
    return muestras


class EmpresaFueraDeAlcance(Exception):
    """La empresa pedida no existe o no está dentro del alcance de quien consulta."""


class ConsultarIndicadoresAgregados:
    """RF-22 (HU-023): tablero de indicadores. Alcance según el rol: el
    consultor ve las empresas con asignación vigente y el administrador todas
    las activas. Se filtra por sector y tamaño, o se ve una sola empresa.

    Confidencialidad (Gherkin HU-023 CA-01): al consultor, si el filtro agrupa
    menos de tres empresas no se le presenta el detalle agregado. El
    administrador ya accede al detalle de cada empresa, y la vista de una
    empresa son sus propios resultados: ahí no aplica."""

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
        usuario_id: str,
        sector_codigo: Optional[str] = None,
        tamano: Optional[str] = None,
        empresa_id: Optional[str] = None,
    ) -> IndicadoresAgregados:
        _validar_tamano(tamano)
        usuario = await _obtener_consultor(self._usuarios, usuario_id)
        es_administrador = usuario.rol.codigo == "administrador"

        if es_administrador:
            alcance = [e.id for e in await self._empresas.listar_activas()]
        else:
            alcance = usuario.empresas_asignadas_vigentes()

        if empresa_id is not None:
            if empresa_id not in alcance:
                raise EmpresaFueraDeAlcance()
            muestras = await _recolectar_muestras(
                self._empresas, self._diagnosticos, [empresa_id]
            )
            if not muestras:
                return IndicadoresAgregados(
                    detalle_disponible=False,
                    ambito="empresa",
                    mensaje="La empresa aún no tiene un diagnóstico evaluado",
                )
            return calcular_indicadores_empresa(muestras[0])

        muestras = await _recolectar_muestras(
            self._empresas, self._diagnosticos, alcance
        )
        minimo = 1 if es_administrador else MINIMO_EMPRESAS
        return calcular_indicadores(
            filtrar_muestras(muestras, sector_codigo, tamano), minimo
        )


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
