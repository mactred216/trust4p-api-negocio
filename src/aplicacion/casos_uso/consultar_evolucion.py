from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico
from src.dominio.puertos.repositorio_usuario import RepositorioUsuario


@dataclass
class PuntoEvolucion:
    diagnostico_id: str
    consecutivo: int
    modelo_version: str
    generado_en: datetime
    indice_global: Decimal
    nivel: int
    dimensiones: dict[str, Decimal]


@dataclass
class VariacionDimension:
    codigo: str
    puntaje_anterior: Decimal
    puntaje_actual: Decimal
    variacion: Decimal


@dataclass
class ComparacionEvolucion:
    diagnostico_anterior_id: str
    diagnostico_actual_id: str
    indice_global_anterior: Decimal
    indice_global_actual: Decimal
    variacion_indice_global: Decimal
    variaciones_por_dimension: list[VariacionDimension]
    versiones_equivalentes: bool
    advertencia: Optional[str]


@dataclass
class EvolucionDiagnosticos:
    historial: list[PuntoEvolucion]
    comparacion: Optional[ComparacionEvolucion]


class ConsultarEvolucionDiagnosticos:
    """RF-18 (HU-019): compara el nivel de madurez global y el puntaje por
    dimensión entre los diagnósticos de la empresa que ya tienen un
    resultado calculado. Incluye también los diagnósticos 'fallido' — su
    índice determinístico ya quedó persistido antes de que el agente
    fallara (ASR-02), así que siguen siendo un punto de comparación válido
    aunque les falte la interpretación narrativa."""

    def __init__(
        self, repo_diagnostico: RepositorioDiagnostico, repo_usuario: RepositorioUsuario
    ):
        self._diagnosticos = repo_diagnostico
        self._usuarios = repo_usuario

    async def ejecutar(self, usuario_id: str) -> EvolucionDiagnosticos:
        usuario = await self._usuarios.obtener_por_id(usuario_id)
        if usuario is None or usuario.empresa_id is None:
            raise ValueError("El usuario no tiene una empresa asociada")

        diagnosticos = await self._diagnosticos.listar_por_empresa(usuario.empresa_id)
        con_resultado = sorted(
            (d for d in diagnosticos if d.resultado is not None),
            key=lambda d: d.consecutivo,
        )

        historial = [
            PuntoEvolucion(
                diagnostico_id=d.id,
                consecutivo=d.consecutivo,
                modelo_version=d.modelo_version,
                generado_en=d.resultado.generado_en,
                indice_global=d.resultado.indice_global,
                nivel=d.resultado.nivel,
                dimensiones={
                    dim.codigo: dim.puntaje for dim in d.resultado.dimensiones
                },
            )
            for d in con_resultado
        ]

        comparacion = None
        if len(con_resultado) >= 2:
            anterior, actual = con_resultado[-2], con_resultado[-1]
            puntajes_anterior = {
                dim.codigo: dim.puntaje for dim in anterior.resultado.dimensiones
            }
            puntajes_actual = {
                dim.codigo: dim.puntaje for dim in actual.resultado.dimensiones
            }
            codigos_comunes = sorted(set(puntajes_anterior) & set(puntajes_actual))
            variaciones = [
                VariacionDimension(
                    codigo=codigo,
                    puntaje_anterior=puntajes_anterior[codigo],
                    puntaje_actual=puntajes_actual[codigo],
                    variacion=puntajes_actual[codigo] - puntajes_anterior[codigo],
                )
                for codigo in codigos_comunes
            ]
            versiones_equivalentes = anterior.modelo_version == actual.modelo_version
            comparacion = ComparacionEvolucion(
                diagnostico_anterior_id=anterior.id,
                diagnostico_actual_id=actual.id,
                indice_global_anterior=anterior.resultado.indice_global,
                indice_global_actual=actual.resultado.indice_global,
                variacion_indice_global=(
                    actual.resultado.indice_global - anterior.resultado.indice_global
                ),
                variaciones_por_dimension=variaciones,
                versiones_equivalentes=versiones_equivalentes,
                advertencia=(
                    None
                    if versiones_equivalentes
                    else "Los diagnósticos comparados usan versiones distintas del "
                    "modelo de madurez; las escalas pueden no ser equivalentes."
                ),
            )

        return EvolucionDiagnosticos(historial=historial, comparacion=comparacion)
