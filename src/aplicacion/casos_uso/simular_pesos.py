from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from src.aplicacion.casos_uso.gestionar_modelo_madurez import \
    ModeloNoEncontrado
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.servicios.motor_calculo import RubricaNoCubreElIndice
from src.dominio.servicios.simulacion_pesos import (ComparacionDiagnostico,
                                                    modelo_con_pesos_simulados,
                                                    simular_diagnostico)

ESTADOS_CON_RESULTADO = ("evaluado", "fallido", "cerrado")


class SinDiagnosticosParaSimular(Exception):
    pass


@dataclass
class DiagnosticoNoSimulable:
    diagnostico_id: str
    motivo: str


@dataclass
class ResultadoSimulacion:
    modelo_version: str
    comparaciones: list[ComparacionDiagnostico]
    no_simulables: list[DiagnosticoNoSimulable] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.comparaciones)

    @property
    def con_cambio_de_nivel(self) -> int:
        return sum(1 for c in self.comparaciones if c.cambia_de_nivel)

    @property
    def variacion_promedio(self) -> Decimal:
        if not self.comparaciones:
            return Decimal("0.00")
        suma = sum((c.variacion_indice for c in self.comparaciones), Decimal("0"))
        return (suma / len(self.comparaciones)).quantize(Decimal("0.01"))


class SimularPesosModelo:
    """RF-35 (HU-035): recalcula, solo en memoria, los diagnósticos históricos
    de una versión del modelo con otra configuración de pesos por dimensión y
    los compara con el resultado almacenado. No escribe en ninguna colección."""

    def __init__(
        self,
        repo_modelo: RepositorioModeloMadurez,
        repo_diagnostico: RepositorioDiagnostico,
    ):
        self._modelos = repo_modelo
        self._diagnosticos = repo_diagnostico

    async def ejecutar(
        self,
        modelo_id: str,
        pesos: dict[str, Decimal],
        diagnostico_ids: Optional[list[str]] = None,
    ) -> ResultadoSimulacion:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()
        modelo_simulado = modelo_con_pesos_simulados(modelo, pesos)

        elegibles = [
            d
            for d in await self._diagnosticos.listar_por_modelo_version(modelo.version)
            if d.estado in ESTADOS_CON_RESULTADO and d.resultado is not None
        ]
        if diagnostico_ids is not None:
            solicitados = set(diagnostico_ids)
            ajenos = solicitados - {d.id for d in elegibles}
            if ajenos:
                raise ValueError(
                    "Diagnósticos que no pertenecen a esta versión o no tienen "
                    f"resultado calculado: {', '.join(sorted(ajenos))}"
                )
            elegibles = [d for d in elegibles if d.id in solicitados]
        if not elegibles:
            raise SinDiagnosticosParaSimular(
                f"No hay diagnósticos históricos calculados con la versión {modelo.version}"
            )

        resultado = ResultadoSimulacion(modelo_version=modelo.version, comparaciones=[])
        for diagnostico in elegibles:
            try:
                resultado.comparaciones.append(
                    simular_diagnostico(diagnostico, modelo_simulado)
                )
            except RubricaNoCubreElIndice as e:
                resultado.no_simulables.append(
                    DiagnosticoNoSimulable(diagnostico.id, str(e))
                )
        return resultado
