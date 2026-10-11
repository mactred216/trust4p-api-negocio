from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

"""RF-22/RF-46 (HU-023): indicadores agregados por sector, tamaño de empresa y
nivel de madurez. Función pura sobre una muestra con UNA fila por empresa (su
diagnóstico más reciente con resultado), de modo que ninguna empresa pese dos
veces. Confidencialidad (Gherkin HU-023 CA-01): ningún agregado se presenta si
resume a menos de MINIMO_EMPRESAS empresas; la supresión se aplica al total y
también a cada grupo, para que restar grupos no revele a una empresa."""

MINIMO_EMPRESAS = 3

TAMANOS = ("micro", "pequena", "mediana", "grande")

MENSAJE_CONFIDENCIALIDAD = (
    f"El filtro aplicado agrupa menos de {MINIMO_EMPRESAS} empresas; el detalle "
    "agregado no se presenta para preservar la confidencialidad"
)


def clasificar_tamano(numero_empleados: Optional[int]) -> Optional[str]:
    """Clasificación por planta de personal (Ley 590 de 2000, art. 2, criterio
    de empleados): micro hasta 10, pequeña hasta 50, mediana hasta 200,
    grande más de 200. None si la empresa no informó su planta."""
    if numero_empleados is None:
        return None
    if numero_empleados <= 10:
        return "micro"
    if numero_empleados <= 50:
        return "pequena"
    if numero_empleados <= 200:
        return "mediana"
    return "grande"


@dataclass(frozen=True)
class MuestraEmpresa:
    sector_codigo: str
    sector_nombre: str
    tamano: Optional[str]
    nivel: int
    indice_global: Decimal
    puntajes_dimension: dict[str, Decimal] = field(default_factory=dict)
    empresa_id: Optional[str] = None
    empresa_nombre: Optional[str] = None


@dataclass
class GrupoIndicador:
    clave: str
    etiqueta: str
    empresas: int
    porcentaje: Decimal
    indice_promedio: Decimal


@dataclass
class IndicadoresAgregados:
    detalle_disponible: bool
    mensaje: Optional[str] = None
    # "total" (todas las empresas del alcance) o "empresa" (una sola).
    ambito: str = "total"
    empresa_nombre: Optional[str] = None
    total_empresas: Optional[int] = None
    indice_promedio: Optional[Decimal] = None
    por_nivel: list[GrupoIndicador] = field(default_factory=list)
    por_sector: list[GrupoIndicador] = field(default_factory=list)
    por_tamano: list[GrupoIndicador] = field(default_factory=list)
    promedio_por_dimension: dict[str, Decimal] = field(default_factory=dict)


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _promedio(valores: list[Decimal]) -> Decimal:
    return _redondear(sum(valores, Decimal("0")) / len(valores))


def _agrupar(
    muestras: list[MuestraEmpresa], clave_de, etiqueta_de, minimo: int = MINIMO_EMPRESAS
) -> list[GrupoIndicador]:
    grupos: dict[str, list[MuestraEmpresa]] = {}
    for muestra in muestras:
        clave = clave_de(muestra)
        if clave is None:
            continue
        grupos.setdefault(str(clave), []).append(muestra)
    total = len(muestras)
    resultado = []
    for clave, miembros in grupos.items():
        if len(miembros) < minimo:
            continue
        resultado.append(
            GrupoIndicador(
                clave=clave,
                etiqueta=etiqueta_de(miembros[0]),
                empresas=len(miembros),
                porcentaje=_redondear(Decimal(len(miembros)) * 100 / total),
                indice_promedio=_promedio([m.indice_global for m in miembros]),
            )
        )
    return sorted(resultado, key=lambda g: g.clave)


def filtrar_muestras(
    muestras: list[MuestraEmpresa],
    sector_codigo: Optional[str] = None,
    tamano: Optional[str] = None,
) -> list[MuestraEmpresa]:
    return [
        m
        for m in muestras
        if (sector_codigo is None or m.sector_codigo == sector_codigo)
        and (tamano is None or m.tamano == tamano)
    ]


def calcular_indicadores(
    muestras: list[MuestraEmpresa], minimo: int = MINIMO_EMPRESAS
) -> IndicadoresAgregados:
    """`minimo` es el tope de confidencialidad: el consultor lo aplica (HU-023
    CA-01). El administrador ya accede al detalle de cada empresa, por lo que
    para él no hay nada que proteger con la supresión (minimo=1)."""
    if not muestras or len(muestras) < minimo:
        return IndicadoresAgregados(
            detalle_disponible=False,
            mensaje=(
                MENSAJE_CONFIDENCIALIDAD
                if muestras
                else "No hay empresas con un diagnóstico evaluado para este filtro"
            ),
        )

    por_dimension: dict[str, list[Decimal]] = {}
    for muestra in muestras:
        for codigo, puntaje in muestra.puntajes_dimension.items():
            por_dimension.setdefault(codigo, []).append(puntaje)

    return IndicadoresAgregados(
        detalle_disponible=True,
        total_empresas=len(muestras),
        indice_promedio=_promedio([m.indice_global for m in muestras]),
        por_nivel=_agrupar(
            muestras, lambda m: m.nivel, lambda m: f"Nivel {m.nivel}", minimo
        ),
        por_sector=_agrupar(
            muestras, lambda m: m.sector_codigo, lambda m: m.sector_nombre, minimo
        ),
        por_tamano=_agrupar(muestras, lambda m: m.tamano, lambda m: m.tamano, minimo),
        promedio_por_dimension={
            codigo: _promedio(valores)
            for codigo, valores in sorted(por_dimension.items())
            if len(valores) >= minimo
        },
    )


def calcular_indicadores_empresa(muestra: MuestraEmpresa) -> IndicadoresAgregados:
    """Tablero de UNA empresa: son sus propios resultados (que su consultor o el
    administrador ya pueden consultar en el detalle del diagnóstico), no un
    agregado que pueda ocultar a nadie: no aplica el tope de confidencialidad."""
    return IndicadoresAgregados(
        detalle_disponible=True,
        ambito="empresa",
        empresa_nombre=muestra.empresa_nombre,
        total_empresas=1,
        indice_promedio=_redondear(muestra.indice_global),
        por_nivel=[
            GrupoIndicador(
                clave=str(muestra.nivel),
                etiqueta=f"Nivel {muestra.nivel}",
                empresas=1,
                porcentaje=Decimal("100.00"),
                indice_promedio=_redondear(muestra.indice_global),
            )
        ],
        por_sector=[
            GrupoIndicador(
                clave=muestra.sector_codigo,
                etiqueta=muestra.sector_nombre,
                empresas=1,
                porcentaje=Decimal("100.00"),
                indice_promedio=_redondear(muestra.indice_global),
            )
        ],
        por_tamano=(
            [
                GrupoIndicador(
                    clave=muestra.tamano,
                    etiqueta=muestra.tamano,
                    empresas=1,
                    porcentaje=Decimal("100.00"),
                    indice_promedio=_redondear(muestra.indice_global),
                )
            ]
            if muestra.tamano
            else []
        ),
        promedio_por_dimension={
            codigo: _redondear(puntaje)
            for codigo, puntaje in sorted(muestra.puntajes_dimension.items())
        },
    )


@dataclass
class FilaExportacion:
    sector_codigo: str
    sector_nombre: str
    tamano: str
    nivel: int
    empresas: int
    indice_promedio: Decimal


def filas_para_exportacion(muestras: list[MuestraEmpresa]) -> list[FilaExportacion]:
    """RF-46: datos agregados y anonimizados (sin identificar empresas) por
    sector x tamaño x nivel. Las celdas con menos de MINIMO_EMPRESAS empresas
    se omiten por la misma regla de confidencialidad del tablero."""
    celdas: dict[tuple, list[MuestraEmpresa]] = {}
    for muestra in muestras:
        llave = (
            muestra.sector_codigo,
            muestra.tamano or "sin_dato",
            muestra.nivel,
        )
        celdas.setdefault(llave, []).append(muestra)
    filas = [
        FilaExportacion(
            sector_codigo=llave[0],
            sector_nombre=miembros[0].sector_nombre,
            tamano=llave[1],
            nivel=llave[2],
            empresas=len(miembros),
            indice_promedio=_promedio([m.indice_global for m in miembros]),
        )
        for llave, miembros in celdas.items()
        if len(miembros) >= MINIMO_EMPRESAS
    ]
    return sorted(filas, key=lambda f: (f.sector_codigo, f.tamano, f.nivel))
