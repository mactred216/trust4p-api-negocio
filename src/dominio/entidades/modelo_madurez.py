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
class Nivel:
    nivel: int
    nombre: str
    descripcion: str
    umbral_min: Decimal
    umbral_max: Decimal


# RF-14: los cuatro rasgos del perfil cultural de la organización innovadora
# (Calderón y Naranjo, 2007; Bridges, 2000). El conjunto es fijo — no son
# dimensiones que el administrador pueda agregar o quitar libremente, sino
# los cuatro ejes del marco teórico — pero cada uno referencia la dimensión
# del propio modelo de madurez que lo determina, y esa asociación sí la
# configura el administrador.
EJES_PERFIL_CULTURAL_CODIGOS = {
    "extroversion",
    "intuicion",
    "sentimiento",
    "percepcion",
}


# Orden en que se combinan los polos de los cuatro ejes para formar el código
# del perfil (Calderón y Naranjo, 2007; Bridges, 2000).
ORDEN_EJES_PERFIL_CULTURAL = (
    "extroversion",
    "intuicion",
    "sentimiento",
    "percepcion",
)


@dataclass
class EjePerfilCultural:
    codigo: str  # uno de EJES_PERFIL_CULTURAL_CODIGOS
    nombre: str  # p. ej. "Extroversión"
    polo_alto_codigo: str  # letra o código corto, p. ej. "E"
    polo_alto_nombre: str  # p. ej. "Extrovertida"
    polo_bajo_codigo: str  # p. ej. "I"
    polo_bajo_nombre: str  # p. ej. "Introvertida"
    dimension_codigo: str  # dimensión del modelo que determina este eje
    umbral: Decimal  # puntaje de la dimensión >= umbral -> polo alto


@dataclass
class PerfilCulturaCatalogo:
    """RF-14: nombre y descripción que el administrador da a una de las
    combinaciones de polos (p. ej. "ENFP"). Es contenido del resultado: el
    cálculo sigue saliendo de los ejes; el catálogo solo dice cómo se llama y
    se describe el perfil que resulte."""

    codigo: str  # combinación de los cuatro polos, p. ej. "ENFP"
    nombre: str
    descripcion: str
    activo: bool = True


TIPOS_CON_OPCIONES = {"seleccion_unica", "seleccion_multiple"}


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
    activo: bool = True


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
    niveles: list[Nivel] = field(default_factory=list)  # RF-32, HU-033
    preguntas: list[Pregunta] = field(
        default_factory=list
    )  # RF-28/RF-31, HU-029/HU-032
    ejes_perfil_cultural: list[EjePerfilCultural] = field(default_factory=list)  # RF-14
    perfiles_cultura: list[PerfilCulturaCatalogo] = field(default_factory=list)  # RF-14
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
        activas = [
            p.codigo
            for p in self.preguntas
            if p.dimension_codigo == codigo and p.activo
        ]
        ejes = [
            e.codigo for e in self.ejes_perfil_cultural if e.dimension_codigo == codigo
        ]
        if ejes:
            raise ValueError(
                f"No se puede quitar la dimensión '{codigo}': el perfil de cultura "
                f"({', '.join(ejes)}) la usa para determinar su eje. Asocie ese eje a "
                "otra dimensión primero"
            )
        if activas:
            raise ValueError(
                f"No se puede quitar la dimensión '{codigo}': tiene preguntas activas "
                f"({', '.join(activas)}). Desactívelas o muévalas a otra dimensión primero"
            )
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
        self._validar_opciones_de_pregunta(pregunta)
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
        opciones: Optional[list[OpcionPregunta]] = None,
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
        if opciones is not None:
            pregunta.opciones = opciones
        self._validar_opciones_de_pregunta(pregunta)

    def desactivar_pregunta(self, codigo: str) -> None:
        """RF-28: se marca inactiva sin eliminarla del histórico."""
        self._validar_editable()
        pregunta = self._buscar_pregunta(codigo)
        if not pregunta.activo:
            raise ValueError(f"La pregunta '{codigo}' ya se encuentra inactiva")
        if any(
            p.activo
            and p.condicion is not None
            and p.condicion.pregunta_codigo == codigo
            for p in self.preguntas
        ):
            raise ValueError(
                "No se puede desactivar: otra pregunta activa tiene una condición "
                "de activación que depende de esta"
            )
        pregunta.activo = False

    def reactivar_pregunta(self, codigo: str) -> None:
        self._validar_editable()
        pregunta = self._buscar_pregunta(codigo)
        if pregunta.activo:
            raise ValueError(f"La pregunta '{codigo}' ya se encuentra activa")
        pregunta.activo = True

    def _validar_opciones_de_pregunta(self, pregunta: Pregunta) -> None:
        """RF-28 paso 3: toda pregunta obligatoria de tipo cerrado debe tener
        al menos una opción de respuesta configurada."""
        if (
            pregunta.obligatoria
            and pregunta.tipo in TIPOS_CON_OPCIONES
            and not pregunta.opciones
        ):
            raise ValueError(
                f"La pregunta '{pregunta.codigo}' es obligatoria y de tipo "
                f"'{pregunta.tipo}': debe tener al menos una opción de respuesta"
            )

    def validar_pesos_preguntas(self) -> None:
        """R-03: la suma de los pesos de las preguntas activas de cada dimensión
        debe totalizar 1."""
        for dimension in self.dimensiones:
            preguntas_dimension = [
                p
                for p in self.preguntas
                if p.dimension_codigo == dimension.codigo and p.activo
            ]
            if not preguntas_dimension:
                raise ValueError(
                    f"La dimensión '{dimension.codigo}' no tiene preguntas activas asociadas"
                )
            suma = sum((p.peso for p in preguntas_dimension), Decimal("0"))
            if suma != Decimal("1"):
                raise ValueError(
                    f"La suma de los pesos de las preguntas de la dimensión "
                    f"'{dimension.codigo}' es {suma}, debe ser igual a 1"
                )

    def agregar_nivel(self, nivel: Nivel) -> None:
        self._validar_editable()
        if nivel.nivel < self.escala_min or nivel.nivel > self.escala_max:
            raise ValueError(
                f"El nivel {nivel.nivel} debe estar entre {self.escala_min} y {self.escala_max}"
            )
        if nivel.umbral_min >= nivel.umbral_max:
            raise ValueError("umbral_min debe ser menor que umbral_max")
        if any(n.nivel == nivel.nivel for n in self.niveles):
            raise ValueError(f"Ya existe un nivel {nivel.nivel} en esta versión")
        self.niveles.append(nivel)

    def editar_nivel(
        self,
        numero_nivel: int,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        umbral_min: Optional[Decimal] = None,
        umbral_max: Optional[Decimal] = None,
    ) -> None:
        self._validar_editable()
        nivel = self._buscar_nivel(numero_nivel)
        nuevo_min = umbral_min if umbral_min is not None else nivel.umbral_min
        nuevo_max = umbral_max if umbral_max is not None else nivel.umbral_max
        if nuevo_min >= nuevo_max:
            raise ValueError("umbral_min debe ser menor que umbral_max")
        if nombre is not None:
            nivel.nombre = nombre
        if descripcion is not None:
            nivel.descripcion = descripcion
        nivel.umbral_min = nuevo_min
        nivel.umbral_max = nuevo_max

    def quitar_nivel(self, numero_nivel: int) -> None:
        self._validar_editable()
        nivel = self._buscar_nivel(numero_nivel)
        self.niveles.remove(nivel)

    def validar_niveles(self) -> None:
        """R-04: los umbrales de los niveles deben cubrir la escala completa sin solapamiento."""
        if not self.niveles:
            raise ValueError("El modelo no tiene niveles de rúbrica definidos")

        ordenados = sorted(self.niveles, key=lambda n: n.umbral_min)

        if ordenados[0].umbral_min != Decimal(self.escala_min):
            raise ValueError(
                f"La rúbrica no cubre el inicio de la escala ({self.escala_min})"
            )
        if ordenados[-1].umbral_max != Decimal(self.escala_max):
            raise ValueError(
                f"La rúbrica no cubre el final de la escala ({self.escala_max})"
            )

        for actual, siguiente in zip(ordenados, ordenados[1:]):
            if actual.umbral_max < siguiente.umbral_min:
                raise ValueError(
                    f"Hay un vacío entre los niveles {actual.nivel} y {siguiente.nivel}"
                )
            if actual.umbral_max > siguiente.umbral_min:
                raise ValueError(
                    f"Los niveles {actual.nivel} y {siguiente.nivel} tienen rangos solapados"
                )

    def agregar_eje_perfil_cultural(self, eje: EjePerfilCultural) -> None:
        self._validar_editable()
        if eje.codigo not in EJES_PERFIL_CULTURAL_CODIGOS:
            raise ValueError(
                f"'{eje.codigo}' no es un eje válido; debe ser uno de "
                f"{sorted(EJES_PERFIL_CULTURAL_CODIGOS)}"
            )
        if any(e.codigo == eje.codigo for e in self.ejes_perfil_cultural):
            raise ValueError(f"El eje '{eje.codigo}' ya está configurado")
        if not any(d.codigo == eje.dimension_codigo for d in self.dimensiones):
            raise ValueError(f"No existe la dimensión '{eje.dimension_codigo}'")
        self.ejes_perfil_cultural.append(eje)

    def editar_eje_perfil_cultural(
        self,
        codigo: str,
        nombre: Optional[str] = None,
        polo_alto_codigo: Optional[str] = None,
        polo_alto_nombre: Optional[str] = None,
        polo_bajo_codigo: Optional[str] = None,
        polo_bajo_nombre: Optional[str] = None,
        dimension_codigo: Optional[str] = None,
        umbral: Optional[Decimal] = None,
    ) -> None:
        self._validar_editable()
        eje = self._buscar_eje_perfil_cultural(codigo)
        if dimension_codigo is not None:
            if not any(d.codigo == dimension_codigo for d in self.dimensiones):
                raise ValueError(f"No existe la dimensión '{dimension_codigo}'")
            eje.dimension_codigo = dimension_codigo
        if nombre is not None:
            eje.nombre = nombre
        if polo_alto_codigo is not None:
            eje.polo_alto_codigo = polo_alto_codigo
        if polo_alto_nombre is not None:
            eje.polo_alto_nombre = polo_alto_nombre
        if polo_bajo_codigo is not None:
            eje.polo_bajo_codigo = polo_bajo_codigo
        if polo_bajo_nombre is not None:
            eje.polo_bajo_nombre = polo_bajo_nombre
        if umbral is not None:
            eje.umbral = umbral

    def quitar_eje_perfil_cultural(self, codigo: str) -> None:
        self._validar_editable()
        eje = self._buscar_eje_perfil_cultural(codigo)
        self.ejes_perfil_cultural.remove(eje)

    def validar_ejes_perfil_cultural(self) -> None:
        """RF-14: deben estar configurados los cuatro ejes del marco teórico,
        ni más ni menos, cada uno con la dimensión que lo determina."""
        codigos_configurados = {e.codigo for e in self.ejes_perfil_cultural}
        faltantes = EJES_PERFIL_CULTURAL_CODIGOS - codigos_configurados
        if faltantes:
            raise ValueError(
                f"Faltan ejes de perfil cultural por configurar: {sorted(faltantes)}"
            )
        dimensiones = {d.codigo for d in self.dimensiones}
        for eje in self.ejes_perfil_cultural:
            if eje.dimension_codigo not in dimensiones:
                raise ValueError(
                    f"El eje de perfil cultural '{eje.codigo}' usa la dimensión "
                    f"'{eje.dimension_codigo}', que no existe en esta versión"
                )

    def combinaciones_perfil_cultural(self) -> list[str]:
        """Códigos de perfil posibles según los polos de los ejes configurados
        (16 con los cuatro ejes). Vacío mientras falte algún eje."""
        por_codigo = {e.codigo: e for e in self.ejes_perfil_cultural}
        if any(codigo not in por_codigo for codigo in ORDEN_EJES_PERFIL_CULTURAL):
            return []
        combinaciones = [""]
        for codigo in ORDEN_EJES_PERFIL_CULTURAL:
            eje = por_codigo[codigo]
            combinaciones = [
                previo + polo
                for previo in combinaciones
                for polo in (eje.polo_alto_codigo, eje.polo_bajo_codigo)
            ]
        return combinaciones

    def agregar_perfil_cultura(
        self, codigo: str, nombre: str, descripcion: str
    ) -> None:
        self._validar_editable()
        combinaciones = self.combinaciones_perfil_cultural()
        if not combinaciones:
            raise ValueError(
                "Configure primero los cuatro ejes del perfil de cultura: de sus "
                "polos salen los perfiles posibles"
            )
        if codigo not in combinaciones:
            raise ValueError(
                f"'{codigo}' no es una combinación válida de polos; debe ser una de "
                f"{', '.join(combinaciones)}"
            )
        if any(p.codigo == codigo for p in self.perfiles_cultura):
            raise ValueError(f"El perfil '{codigo}' ya está definido")
        self.perfiles_cultura.append(
            PerfilCulturaCatalogo(codigo=codigo, nombre=nombre, descripcion=descripcion)
        )

    def editar_perfil_cultura(
        self,
        codigo: str,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        activo: Optional[bool] = None,
    ) -> None:
        self._validar_editable()
        perfil = self._buscar_perfil_cultura(codigo)
        if nombre is not None:
            perfil.nombre = nombre
        if descripcion is not None:
            perfil.descripcion = descripcion
        if activo is not None:
            perfil.activo = activo

    def quitar_perfil_cultura(self, codigo: str) -> None:
        self._validar_editable()
        self.perfiles_cultura.remove(self._buscar_perfil_cultura(codigo))

    def perfil_cultura_para(self, codigo: str) -> Optional[PerfilCulturaCatalogo]:
        """El perfil activo del catálogo para un código, o None si no hay."""
        for perfil in self.perfiles_cultura:
            if perfil.codigo == codigo and perfil.activo:
                return perfil
        return None

    def validar_perfiles_cultura(self) -> None:
        """Los perfiles definidos deben seguir siendo combinaciones válidas de
        los polos de los ejes (que se pueden haber cambiado después)."""
        combinaciones = set(self.combinaciones_perfil_cultural())
        invalidos = sorted(
            p.codigo for p in self.perfiles_cultura if p.codigo not in combinaciones
        )
        if invalidos:
            raise ValueError(
                f"Los perfiles de cultura {invalidos} ya no corresponden a los polos "
                "de los ejes; quítelos o vuelva a definirlos"
            )

    def _buscar_perfil_cultura(self, codigo: str) -> PerfilCulturaCatalogo:
        for perfil in self.perfiles_cultura:
            if perfil.codigo == codigo:
                return perfil
        raise ValueError(f"No existe el perfil de cultura '{codigo}'")

    def _buscar_eje_perfil_cultural(self, codigo: str) -> EjePerfilCultural:
        for eje in self.ejes_perfil_cultural:
            if eje.codigo == codigo:
                return eje
        raise ValueError(f"No existe el eje de perfil cultural '{codigo}'")

    def publicar(self, publicado_por: str) -> None:
        """RF-33/RF-34: publica la versión vigente. Ensambla R-02, R-03 y R-04;
        a partir de aquí la versión queda inmutable (ver _validar_editable)."""
        if self.publicado:
            raise ValueError("La versión ya fue publicada")
        self.validar_pesos_dimensiones()
        self.validar_pesos_preguntas()
        self.validar_niveles()
        self.validar_ejes_perfil_cultural()
        self.validar_perfiles_cultura()
        self.publicado = True
        self.publicado_en = datetime.now(timezone.utc)
        self.publicado_por = publicado_por

    def _buscar_nivel(self, numero_nivel: int) -> Nivel:
        for nivel in self.niveles:
            if nivel.nivel == numero_nivel:
                return nivel
        raise ValueError(f"No existe el nivel {numero_nivel} en esta versión")

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
