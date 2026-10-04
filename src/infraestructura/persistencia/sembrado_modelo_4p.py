"""Siembra del modelo de madurez Trust 4P (borrador) para poder operar todo el
sistema de punta a punta: 4 dimensiones (Propósito, Procesos, Personas,
Plataforma) al 25 %, escala 0-100, rúbrica N1-N4 y 16 preguntas de selección
única con cuatro niveles de respuesta.

IMPORTANTE: el enunciado de las preguntas es PROVISIONAL (PROC-01 es el del
prototipo del frontend; el resto está redactado como borrador). El banco
definitivo lo carga el administrador por la API / pantalla de gestión
(RNF-19): se crea una versión nueva y se publica. Este script no se ejecuta
solo al arrancar; se corre a mano: `python -m scripts.sembrar_modelo_4p`."""

from decimal import Decimal

from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.modelo_madurez import (Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  OpcionPregunta, Pregunta)
from src.infraestructura.persistencia.repositorio_mongo_modelo_madurez import \
    RepositorioMongoModeloMadurez

VERSION_MODELO_4P = "2026.1"

NIVELES = [
    (
        1,
        "Inicial",
        "La práctica no existe o se ejecuta de forma reactiva y aislada.",
        0,
        25,
    ),
    (
        2,
        "En desarrollo",
        "La práctica existe de manera parcial, sin periodicidad ni responsables definidos.",
        25,
        50,
    ),
    (
        3,
        "Sistemático",
        "La práctica está formalizada, se ejecuta con periodicidad y produce evidencia verificable.",
        50,
        75,
    ),
    (
        4,
        "Optimizado",
        "La práctica se mide, se compara y se ajusta de forma continua con base en resultados.",
        75,
        100,
    ),
]

DIMENSIONES = [
    ("proposito", "Propósito", "Estrategia y dirección", 1),
    ("procesos", "Procesos", "Embudos ágiles y presupuestos dinámicos", 2),
    ("personas", "Personas", "Cultura y liderazgo", 3),
    ("plataforma", "Plataforma", "Tecnología y ecosistema", 4),
]

# (código, dimensión, enunciado, ayuda, [N1, N2, N3, N4], en_demo)
PREGUNTAS = [
    (
        "PROP-01",
        "proposito",
        "¿Existe una tesis de innovación formalizada y respaldada por la alta dirección?",
        "Considere si la dirección la ha declarado por escrito y le hace seguimiento.",
        [
            "No existe una tesis de innovación declarada.",
            "Existe una intención verbal, sin documento ni responsables.",
            "Está documentada y aprobada por la dirección, con revisión anual.",
            "Está integrada a la estrategia y se revisa con indicadores de forma continua.",
        ],
        True,
    ),
    (
        "PROP-02",
        "proposito",
        "¿Qué recursos se asignan de manera explícita a la innovación?",
        "Presupuesto, tiempo de las personas y equipos dedicados.",
        [
            "No hay recursos asignados; se improvisan.",
            "Se asignan recursos por proyecto, sin criterio estable.",
            "Hay un presupuesto anual definido y responsables identificados.",
            "Los recursos se redistribuyen continuamente según resultados validados.",
        ],
        False,
    ),
    (
        "PROP-03",
        "proposito",
        "¿La junta directiva o la gerencia hace seguimiento al portafolio de iniciativas?",
        "Frecuencia y evidencia de las revisiones.",
        [
            "No se hace seguimiento.",
            "Se revisa de forma esporádica y sin registro.",
            "Se revisa periódicamente con actas y decisiones.",
            "Se gestiona como un portafolio con métricas y decisiones de continuar o detener.",
        ],
        False,
    ),
    (
        "PROP-04",
        "proposito",
        "¿Las iniciativas de innovación están alineadas con los objetivos del negocio?",
        "Relación entre las iniciativas y las metas estratégicas.",
        [
            "No hay relación entre las iniciativas y los objetivos.",
            "La alineación es parcial y depende de cada líder.",
            "Cada iniciativa declara su objetivo estratégico asociado.",
            "La alineación se verifica y se ajusta cada ciclo de planeación.",
        ],
        False,
    ),
    (
        "PROC-01",
        "procesos",
        "¿Con qué frecuencia su organización evalúa y reasigna presupuestos hacia iniciativas de innovación basadas en validación empírica?",
        "Considere el comportamiento real del capital y de los comités de aprobación durante los últimos doce meses frente a pivotes y experimentos validados.",
        [
            "El presupuesto se aprueba una vez al año y está ligado a silos funcionales, sin posibilidad de reasignación rápida.",
            "Comités semestrales revisan hitos, con ajustes menores y procesos burocráticos para redirigir fondos.",
            "Ciclos de noventa días. Los equipos acceden a micro-fondos basados en evidencia y descartan hipótesis fallidas.",
            "Gobernanza adaptativa continua. El capital fluye según tracción comprobable y aprendizaje validado.",
        ],
        True,
    ),
    (
        "PROC-02",
        "procesos",
        "¿Cómo se gestiona el recorrido de una idea desde que aparece hasta que se implementa?",
        "Existencia de etapas, criterios de paso y responsables.",
        [
            "No hay un recorrido definido; las ideas se pierden o avanzan por contactos.",
            "Hay pasos informales que cambian según el equipo.",
            "Existe un embudo con etapas, criterios y responsables documentados.",
            "El embudo se mide (tiempos, conversión) y se mejora de forma continua.",
        ],
        False,
    ),
    (
        "PROC-03",
        "procesos",
        "¿Se validan las hipótesis con experimentos antes de comprometer grandes inversiones?",
        "Uso de pruebas pequeñas, prototipos o pilotos.",
        [
            "No se experimenta; se decide por intuición.",
            "Se hacen pruebas ocasionales sin método.",
            "Hay un método de experimentación con hipótesis y criterios de éxito.",
            "Los experimentos son la norma y sus resultados alimentan las decisiones de inversión.",
        ],
        False,
    ),
    (
        "PROC-04",
        "procesos",
        "¿Cómo se capturan y reutilizan los aprendizajes de las iniciativas?",
        "Registro de resultados, incluidos los fallidos.",
        [
            "No se registran los aprendizajes.",
            "Se comentan informalmente al terminar.",
            "Se documentan en un registro accesible para los equipos.",
            "Se analizan sistemáticamente y modifican los procesos futuros.",
        ],
        False,
    ),
    (
        "PERS-01",
        "personas",
        "¿Cómo se reconoce o incentiva a las personas que proponen y prueban ideas?",
        "Esquemas formales o informales de reconocimiento.",
        [
            "No existe ningún reconocimiento.",
            "Reconocimientos ocasionales y sin criterio.",
            "Hay un esquema definido que reconoce la participación en innovación.",
            "Los incentivos premian el aprendizaje validado, incluso de las hipótesis descartadas.",
        ],
        True,
    ),
    (
        "PERS-02",
        "personas",
        "¿Qué tan seguro es para los equipos reportar errores o hipótesis fallidas?",
        "Tolerancia al error en la práctica cotidiana.",
        [
            "El error se sanciona; se oculta.",
            "Se tolera en privado, pero no se comunica.",
            "Se comunica abiertamente y se analiza sin buscar culpables.",
            "Se celebra el aprendizaje temprano y se comparte entre equipos.",
        ],
        False,
    ),
    (
        "PERS-03",
        "personas",
        "¿Qué capacitación en innovación reciben los líderes y los equipos?",
        "Formación en métodos de innovación y resolución de problemas.",
        [
            "Ninguna.",
            "Cursos aislados a solicitud de cada persona.",
            "Un plan anual de formación para líderes y equipos clave.",
            "Formación continua, medida por su efecto en los resultados.",
        ],
        False,
    ),
    (
        "PERS-04",
        "personas",
        "¿Cómo se involucra a distintas áreas en las iniciativas de innovación?",
        "Participación transversal más allá de un solo equipo.",
        [
            "La innovación es tarea de una sola persona o área.",
            "Se invita a otras áreas de forma puntual.",
            "Hay equipos multidisciplinarios con roles definidos.",
            "La innovación es una práctica transversal con redes internas activas.",
        ],
        False,
    ),
    (
        "PLAT-01",
        "plataforma",
        "¿Existe un repositorio centralizado de activos y resultados de innovación?",
        "Dónde se guardan las ideas, experimentos y aprendizajes.",
        [
            "No existe; la información está dispersa en archivos personales.",
            "Hay varias herramientas desconectadas.",
            "Existe un repositorio común con responsables de mantenerlo.",
            "El repositorio está integrado a los procesos y se consulta antes de decidir.",
        ],
        True,
    ),
    (
        "PLAT-02",
        "plataforma",
        "¿Qué herramientas de vigilancia tecnológica y de mercado se utilizan?",
        "Seguimiento de tendencias, competidores y tecnologías.",
        [
            "Ninguna.",
            "Búsquedas manuales ocasionales.",
            "Un proceso periódico con fuentes y responsables definidos.",
            "Un sistema continuo con análisis que alimenta la estrategia.",
        ],
        False,
    ),
    (
        "PLAT-03",
        "plataforma",
        "¿Cómo se gestionan los datos que sustentan las decisiones de innovación?",
        "Disponibilidad, calidad y trazabilidad de los datos.",
        [
            "No se dispone de datos confiables.",
            "Los datos existen pero están en silos y sin control de calidad.",
            "Hay datos consolidados y reglas de calidad.",
            "Los datos son trazables, se analizan automáticamente y se usan en cada decisión.",
        ],
        False,
    ),
    (
        "PLAT-04",
        "plataforma",
        "¿La organización colabora con un ecosistema externo (universidades, aliados, startups)?",
        "Alianzas activas para innovar.",
        [
            "No hay vínculos externos.",
            "Contactos ocasionales sin acuerdos.",
            "Alianzas formales con objetivos definidos.",
            "Un ecosistema activo que genera proyectos conjuntos de forma recurrente.",
        ],
        False,
    ),
]

# RF-14: dimensión del modelo que determina cada eje del perfil cultural
# (asociación provisional; la configura el administrador).
EJES = [
    (
        "extroversion",
        "Extroversión",
        "E",
        "Extrovertida",
        "I",
        "Introvertida",
        "plataforma",
    ),
    ("intuicion", "Intuición", "N", "Intuitiva", "S", "Sensorial", "proposito"),
    ("sentimiento", "Sentimiento", "F", "Sentimental", "T", "Racional", "personas"),
    ("percepcion", "Percepción", "P", "Perceptiva", "J", "Juiciosa", "procesos"),
]


def construir_modelo_4p() -> ModeloMadurez:
    modelo = ModeloMadurez(
        id=None,
        version=VERSION_MODELO_4P,
        nombre="Modelo de madurez de innovación Trust 4P (borrador)",
        descripcion="Banco de preguntas provisional para pruebas de integración.",
        escala_min=0,
        escala_max=100,
    )
    for codigo, nombre, descripcion, orden in DIMENSIONES:
        modelo.agregar_dimension(
            Dimension(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                peso=Decimal("0.25"),
                orden=orden,
            )
        )
    contador: dict[str, int] = {}
    for codigo, dimension, enunciado, ayuda, niveles, en_demo in PREGUNTAS:
        contador[dimension] = contador.get(dimension, 0) + 1
        modelo.agregar_pregunta(
            Pregunta(
                codigo=codigo,
                dimension_codigo=dimension,
                enunciado=enunciado,
                ayuda=ayuda,
                tipo="seleccion_unica",
                obligatoria=True,
                peso=Decimal("0.25"),
                en_demo=en_demo,
                orden=contador[dimension],
                opciones=[
                    OpcionPregunta(
                        codigo=f"N{i}",
                        etiqueta=descripcion,
                        valor=Decimal(25 * i),
                    )
                    for i, descripcion in enumerate(niveles, start=1)
                ],
            )
        )
    for numero, nombre, descripcion, minimo, maximo in NIVELES:
        modelo.agregar_nivel(
            Nivel(
                nivel=numero,
                nombre=nombre,
                descripcion=descripcion,
                umbral_min=Decimal(minimo),
                umbral_max=Decimal(maximo),
            )
        )
    for codigo, nombre, alto_c, alto_n, bajo_c, bajo_n, dimension in EJES:
        modelo.agregar_eje_perfil_cultural(
            EjePerfilCultural(
                codigo=codigo,
                nombre=nombre,
                polo_alto_codigo=alto_c,
                polo_alto_nombre=alto_n,
                polo_bajo_codigo=bajo_c,
                polo_bajo_nombre=bajo_n,
                dimension_codigo=dimension,
                umbral=Decimal("62.5"),
            )
        )
    return modelo


async def sembrar_modelo_4p(db: AsyncIOMotorDatabase) -> bool:
    """Crea y publica el modelo 4P si esa versión no existe. Devuelve True si lo
    creó. Idempotente."""
    repo = RepositorioMongoModeloMadurez(db)
    if await repo.obtener_por_version(VERSION_MODELO_4P) is not None:
        return False
    modelo = construir_modelo_4p()
    modelo.publicar(publicado_por="sembrado")
    await repo.guardar(modelo)
    return True
