from src.aplicacion.casos_uso.gestionar_diagnostico import NoHayVersionVigente
from src.dominio.entidades.modelo_madurez import Pregunta
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez
from src.dominio.servicios.diagnostico_demo import (RespuestaDemo,
                                                    ResultadoDemo,
                                                    calcular_resultado_demo,
                                                    preguntas_de_demostracion)


class DemostracionNoDisponible(Exception):
    pass


class ObtenerPreguntasDemo:
    """RF-49 paso 1: subconjunto público del modelo vigente, sin autenticar."""

    def __init__(self, repo_modelo: RepositorioModeloMadurez):
        self._modelos = repo_modelo

    async def ejecutar(self) -> tuple[str, list[Pregunta]]:
        modelo = await self._modelos.obtener_vigente()
        if modelo is None:
            raise NoHayVersionVigente()
        preguntas = preguntas_de_demostracion(modelo)
        if not preguntas:
            raise DemostracionNoDisponible()
        return modelo.version, preguntas


class CalcularResultadoDemo:
    """RF-49 pasos 3 y 4: resultado orientativo calculado al vuelo. No usa
    ningún repositorio de escritura: nada se persiste (HU-007 CA-02)."""

    def __init__(self, repo_modelo: RepositorioModeloMadurez):
        self._modelos = repo_modelo

    async def ejecutar(self, respuestas: list[RespuestaDemo]) -> ResultadoDemo:
        modelo = await self._modelos.obtener_vigente()
        if modelo is None:
            raise NoHayVersionVigente()
        if not preguntas_de_demostracion(modelo):
            raise DemostracionNoDisponible()
        return calcular_resultado_demo(modelo, respuestas)
