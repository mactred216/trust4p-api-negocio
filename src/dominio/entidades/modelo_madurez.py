from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass
class Dimension:
    codigo: str
    nombre: str
    peso: Decimal
    orden: int
    descripcion: Optional[str] = None


@dataclass
class ModeloMadurez:
    id: Optional[str]
    version: str
    nombre: str
    descripcion: Optional[str] = None
    escala_min: int = 1
    escala_max: int = 10
    publicado: bool = False
    publicado_en: Optional[datetime] = None
    publicado_por: Optional[str] = None
    dimensiones: list[Dimension] = field(default_factory=list)
    niveles: list = field(default_factory=list)  # RF-32, HU-033
    preguntas: list = field(default_factory=list)  # RF-29/RF-31, HU-032
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def agregar_dimension(self, dimension: Dimension) -> None:
        self._validar_editable()
        if any(d.codigo == dimension.codigo for d in self.dimensiones):
            raise ValueError(
                f"Ya existe una dimensión con código '{dimension.codigo}' en esta versión"
            )
        self.dimensiones.append(dimension)

    def editar_dimension(
        self,
        codigo: str,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        peso: Optional[Decimal] = None,
        orden: Optional[int] = None,
    ) -> None:
        self._validar_editable()
        dimension = self._buscar_dimension(codigo)
        if nombre is not None:
            dimension.nombre = nombre
        if descripcion is not None:
            dimension.descripcion = descripcion
        if peso is not None:
            dimension.peso = peso
        if orden is not None:
            dimension.orden = orden

    def quitar_dimension(self, codigo: str) -> None:
        self._validar_editable()
        dimension = self._buscar_dimension(codigo)
        self.dimensiones.remove(dimension)

    def validar_pesos_dimensiones(self) -> None:
        """R-02: la suma de los pesos de las dimensiones debe totalizar 1."""
        if not self.dimensiones:
            raise ValueError("El modelo no tiene dimensiones definidas")
        suma = sum((d.peso for d in self.dimensiones), Decimal("0"))
        if suma != Decimal("1"):
            raise ValueError(
                f"La suma de los pesos de las dimensiones es {suma}, debe ser igual a 1"
            )

    def _buscar_dimension(self, codigo: str) -> Dimension:
        for dimension in self.dimensiones:
            if dimension.codigo == codigo:
                return dimension
        raise ValueError(
            f"No existe una dimensión con código '{codigo}' en esta versión"
        )

    def _validar_editable(self) -> None:
        """RF-34/ASR-04: una versión publicada es inmutable; se debe crear una nueva."""
        if self.publicado:
            raise ValueError(
                "La versión ya fue publicada y es inmutable; cree una versión nueva para modificarla"
            )
