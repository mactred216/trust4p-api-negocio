import copy
from dataclasses import dataclass
from decimal import Decimal

from src.dominio.entidades.diagnostico import Diagnostico
from src.dominio.entidades.modelo_madurez import ModeloMadurez
from src.dominio.servicios.motor_calculo import calcular_resultado

"""RF-35 (HU-035): simulación del efecto de otra configuración de pesos por
dimensión sobre diagnósticos históricos. Es una función pura: trabaja sobre
una copia profunda del modelo y reutiliza el motor de cálculo determinístico
(ADR-005), de modo que el 'entorno separado' del RF es la propia memoria del
proceso y ningún dato persistido se toca (HU-035 CA-01)."""


def modelo_con_pesos_simulados(
    modelo: ModeloMadurez, pesos: dict[str, Decimal]
) -> ModeloMadurez:
    """Copia del modelo con los pesos de dimensión propuestos. Exige que se
    informen exactamente las dimensiones del modelo y que sumen 1 (R-02)."""
    codigos_modelo = {d.codigo for d in modelo.dimensiones}
    faltantes = codigos_modelo - pesos.keys()
    sobrantes = pesos.keys() - codigos_modelo
    if faltantes:
        raise ValueError(
            f"Faltan pesos para las dimensiones: {', '.join(sorted(faltantes))}"
        )
    if sobrantes:
        raise ValueError(
            f"Dimensiones inexistentes en el modelo: {', '.join(sorted(sobrantes))}"
        )

    simulado = copy.deepcopy(modelo)
    for dimension in simulado.dimensiones:
        dimension.peso = pesos[dimension.codigo]
    simulado.validar_pesos_dimensiones()
    return simulado


@dataclass
class ComparacionDiagnostico:
    diagnostico_id: str
    empresa_id: str
    empresa_nombre: str
    consecutivo: int
    indice_original: Decimal
    nivel_original: int
    indice_simulado: Decimal
    nivel_simulado: int
    variacion_indice: Decimal
    cambia_de_nivel: bool


def simular_diagnostico(
    diagnostico: Diagnostico, modelo_simulado: ModeloMadurez
) -> ComparacionDiagnostico:
    original = diagnostico.resultado
    calculo = calcular_resultado(diagnostico, modelo_simulado)
    indice_simulado = calculo.indice_global.quantize(Decimal("0.01"))
    indice_original = original.indice_global.quantize(Decimal("0.01"))
    return ComparacionDiagnostico(
        diagnostico_id=diagnostico.id,
        empresa_id=diagnostico.empresa_id,
        empresa_nombre=diagnostico.empresa_nombre,
        consecutivo=diagnostico.consecutivo,
        indice_original=indice_original,
        nivel_original=original.nivel,
        indice_simulado=indice_simulado,
        nivel_simulado=calculo.nivel,
        variacion_indice=indice_simulado - indice_original,
        cambia_de_nivel=calculo.nivel != original.nivel,
    )
