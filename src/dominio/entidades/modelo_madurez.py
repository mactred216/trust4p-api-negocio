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
class OpcionPregunta:
    codigo: str
    etiqueta: str
    valor: Decimal


@dataclass
class CondicionActivacion:
    pregunta_codigo: str
    operador: str  # igual | diferente | mayor_que | menor_que | contiene
    valor: str


@dataclass
class Pregunta:
    codigo: str
    dimension_codigo: str
    enunciado: str
    tipo: str  # seleccion_unica | seleccion_multiple | escala | numerica | texto_libre
    obligatoria: bool
    peso: Decimal
    en_demo: bool
    orden: int
    ayuda: Optional[str] = None
    opciones: list[OpcionPregunta] = field(default_factory=list)
    condicion: Optional[CondicionActivacion] = None


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
    preguntas: list[Pregunta] = field(default_factory=list)  # RF-29/RF-31, HU-032
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

    def agregar_pregunta(self, pregunta: Pregunta) -> None:
        self._validar_editable()
        if not any(d.codigo == pregunta.dimension_codigo for d in self.dimensiones):
            raise ValueError(
                f"No existe la dimensión '{pregunta.dimension_codigo}' en esta versión"
            )
        if any(p.codigo == pregunta.codigo for p in self.preguntas):
            raise ValueError(
                f"Ya existe una pregunta con código '{pregunta.codigo}' en esta versión"
            )
        if pregunta.condicion is not None and not any(
            p.codigo == pregunta.condicion.pregunta_codigo for p in self.preguntas
        ):
            raise ValueError(
                f"La condición de activación referencia una pregunta inexistente: "
                f"'{pregunta.condicion.pregunta_codigo}'"
            )
        self.preguntas.append(pregunta)

    def editar_pregunta(
        self,
        codigo: str,
        dimension_codigo: Optional[str] = None,
        enunciado: Optional[str] = None,
        ayuda: Optional[str] = None,
        tipo: Optional[str] = None,
        obligatoria: Optional[bool] = None,
        peso: Optional[Decimal] = None,
        en_demo: Optional[bool] = None,
        orden: Optional[int] = None,
    ) -> None:
        self._validar_editable()
        pregunta = self._buscar_pregunta(codigo)
        if dimension_codigo is not None:
            if not any(d.codigo == dimension_codigo for d in self.dimensiones):
                raise ValueError(
                    f"No existe la dimensión '{dimension_codigo}' en esta versión"
                )
            pregunta.dimension_codigo = dimension_codigo
        if enunciado is not None:
            pregunta.enunciado = enunciado
        if ayuda is not None:
            pregunta.ayuda = ayuda
        if tipo is not None:
            pregunta.tipo = tipo
        if obligatoria is not None:
            pregunta.obligatoria = obligatoria
        if peso is not None:
            pregunta.peso = peso
        if en_demo is not None:
            pregunta.en_demo = en_demo
        if orden is not None:
            pregunta.orden = orden

    def quitar_pregunta(self, codigo: str) -> None:
        self._validar_editable()
        pregunta = self._buscar_pregunta(codigo)
        if any(
            p.condicion is not None and p.condicion.pregunta_codigo == codigo
            for p in self.preguntas
        ):
            raise ValueError(
                "No se puede quitar: otra pregunta tiene una condición de activación "
                "que depende de esta"
            )
        self.preguntas.remove(pregunta)

    def validar_pesos_preguntas(self) -> None:
        """R-03: la suma de los pesos de las preguntas de cada dimensión debe totalizar 1."""
        for dimension in self.dimensiones:
            preguntas_dimension = [
                p for p in self.preguntas if p.dimension_codigo == dimension.codigo
            ]
            if not preguntas_dimension:
                raise ValueError(
                    f"La dimensión '{dimension.codigo}' no tiene preguntas asociadas"
                )
            suma = sum((p.peso for p in preguntas_dimension), Decimal("0"))
            if suma != Decimal("1"):
                raise ValueError(
                    f"La suma de los pesos de las preguntas de la dimensión "
                    f"'{dimension.codigo}' es {suma}, debe ser igual a 1"
                )

    def _buscar_pregunta(self, codigo: str) -> Pregunta:
        for pregunta in self.preguntas:
            if pregunta.codigo == codigo:
                return pregunta
        raise ValueError(
            f"No existe una pregunta con código '{codigo}' en esta versión"
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
