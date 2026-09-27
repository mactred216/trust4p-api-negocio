from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.dominio.entidades.diagnostico import Diagnostico, Recomendacion
from src.dominio.entidades.modelo_madurez import ModeloMadurez
from src.dominio.servicios.motor_calculo import ResultadoCalculo


class ServicioAgenteError(Exception):
    """Fallo al invocar trust4p-servicio-agente: HTTP no exitoso, tiempo de
    espera agotado o error de red. RF-40: el diagnóstico se marca como
    fallido en vez de propagar el error a quien completó el diagnóstico
    (la evaluación ocurre en segundo plano, ASR-02)."""


@dataclass
class RespuestaAgente:
    """Contenido narrativo que produce trust4p-servicio-agente a partir del
    resultado_calculo (ADR-005): nunca determinaciones numéricas o
    categóricas, solo texto."""

    perfil_cultura_descripcion: str
    dimensiones_observaciones: dict[str, str]
    lienzo_negocio: dict[str, str]
    sintesis: str
    recomendaciones: list[Recomendacion]


class ClienteServicioAgente(ABC):
    """Puerto del dominio (ADR-002): ningún adaptador HTTP se referencia
    aquí."""

    @abstractmethod
    async def evaluar(
        self,
        diagnostico: Diagnostico,
        modelo: ModeloMadurez,
        resultado_calculo: ResultadoCalculo,
    ) -> RespuestaAgente: ...
