from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.aplicacion.casos_uso.generar_informe import DiagnosticoSinResultado
from src.aplicacion.casos_uso.gestionar_consultoria import _obtener_consultor
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.dominio.entidades.diagnostico import Diagnostico
from src.dominio.entidades.usuario import Usuario
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_empresa import RepositorioEmpresa
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario
from src.dominio.servicios.indicadores_agregados import (TAMANOS,
                                                         clasificar_tamano)

# Un informe solo se genera sobre un diagnóstico cuya evaluación ya terminó. El
# "fallido" tiene puntajes válidos pero no la interpretación del agente.
ESTADOS_CON_INFORME = ("evaluado", "cerrado")


class FiltroInvalido(Exception):
    pass


@dataclass
class DiagnosticoDeReporte:
    id: str
    consecutivo: int
    estado: str
    nivel: int
    indice_global: object
    evaluado_en: Optional[datetime]


@dataclass
class EmpresaDeReporte:
    empresa_id: str
    nombre: str
    nit: Optional[str]
    sector_codigo: str
    sector_nombre: str
    numero_empleados: Optional[int]
    tamano: Optional[str]
    diagnosticos: list[DiagnosticoDeReporte]


def _alcance_de(usuario: Usuario) -> Optional[set[str]]:
    """None = todas las empresas (administrador); si no, las asignadas vigentes."""
    if usuario.rol.codigo == "administrador":
        return None
    return set(usuario.empresas_asignadas_vigentes())


class ListarEmpresasParaReporte:
    """Empresas dentro del alcance de quien consulta (el administrador todas;
    el consultor solo las que tiene asignadas), filtrables por nombre, sector y
    tamaño, con los diagnósticos de los que se puede descargar el informe."""

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
        nombre: Optional[str] = None,
        sector_codigo: Optional[str] = None,
        tamano: Optional[str] = None,
    ) -> list[EmpresaDeReporte]:
        if tamano is not None and tamano not in TAMANOS:
            raise FiltroInvalido(f"Tamaño inválido; use uno de: {', '.join(TAMANOS)}")
        usuario = await _obtener_consultor(self._usuarios, usuario_id)
        alcance = _alcance_de(usuario)

        resultado = []
        for empresa in await self._empresas.listar_activas():
            if alcance is not None and empresa.id not in alcance:
                continue
            tamano_empresa = clasificar_tamano(empresa.numero_empleados)
            if nombre and nombre.strip().lower() not in empresa.nombre.lower():
                continue
            if sector_codigo and empresa.sector.codigo != sector_codigo:
                continue
            if tamano and tamano_empresa != tamano:
                continue
            diagnosticos = [
                d
                for d in await self._diagnosticos.listar_por_empresa(empresa.id)
                if d.estado in ESTADOS_CON_INFORME and d.resultado is not None
            ]
            resultado.append(
                EmpresaDeReporte(
                    empresa_id=empresa.id,
                    nombre=empresa.nombre,
                    nit=empresa.nit,
                    sector_codigo=empresa.sector.codigo,
                    sector_nombre=empresa.sector.nombre,
                    numero_empleados=empresa.numero_empleados,
                    tamano=tamano_empresa,
                    diagnosticos=[
                        DiagnosticoDeReporte(
                            id=d.id,
                            consecutivo=d.consecutivo,
                            estado=d.estado,
                            nivel=d.resultado.nivel,
                            indice_global=d.resultado.indice_global,
                            evaluado_en=d.evaluado_en,
                        )
                        for d in sorted(diagnosticos, key=lambda d: -d.consecutivo)
                    ],
                )
            )
        return sorted(resultado, key=lambda e: e.nombre.lower())


class GenerarInformeDeEmpresa:
    """Autoriza la descarga del informe de un diagnóstico de cualquier empresa
    (administrador) o de una empresa con asignación vigente (consultor). La
    generación del PDF vive en infraestructura/informes."""

    def __init__(
        self, repo_usuario: RepositorioUsuario, repo_diagnostico: RepositorioDiagnostico
    ):
        self._usuarios = repo_usuario
        self._diagnosticos = repo_diagnostico

    async def ejecutar(self, usuario_id: str, diagnostico_id: str) -> Diagnostico:
        diagnostico = await self._diagnosticos.obtener_por_id(diagnostico_id)
        if diagnostico is None:
            raise DiagnosticoNoEncontrado()

        usuario = await _obtener_consultor(self._usuarios, usuario_id)
        alcance = _alcance_de(usuario)
        if alcance is not None and diagnostico.empresa_id not in alcance:
            raise AccesoNoAutorizado()

        if (
            diagnostico.estado not in ESTADOS_CON_INFORME
            or diagnostico.resultado is None
        ):
            raise DiagnosticoSinResultado()
        return diagnostico
