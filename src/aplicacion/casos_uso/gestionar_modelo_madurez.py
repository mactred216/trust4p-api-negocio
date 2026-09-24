from decimal import Decimal
from typing import Optional

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, ModeloMadurez,
                                                  Nivel, OpcionPregunta,
                                                  Pregunta)
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez


class ModeloNoEncontrado(Exception):
    pass


class VersionDuplicada(Exception):
    """Ya existe una versión del modelo con este identificador (RF-33: único en la colección)."""

    pass


class CrearModeloMadurez:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        version: str,
        nombre: str,
        descripcion: Optional[str] = None,
        escala_min: int = 1,
        escala_max: int = 10,
    ) -> ModeloMadurez:
        if await self._modelos.obtener_por_version(version) is not None:
            raise VersionDuplicada()

        modelo = ModeloMadurez(
            id=None,
            version=version,
            nombre=nombre,
            descripcion=descripcion,
            escala_min=escala_min,
            escala_max=escala_max,
        )
        return await self._modelos.guardar(modelo)


class ListarModelos:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self) -> list[ModeloMadurez]:
        return await self._modelos.listar()


class ConsultarModelo:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()
        return modelo


class AgregarDimension:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        codigo: str,
        nombre: str,
        peso: Decimal,
        orden: int,
        descripcion: Optional[str] = None,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.agregar_dimension(
            Dimension(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                peso=peso,
                orden=orden,
            )
        )
        await self._modelos.actualizar(modelo)
        return modelo


class EditarDimension:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        codigo: str,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        peso: Optional[Decimal] = None,
        orden: Optional[int] = None,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.editar_dimension(
            codigo, nombre=nombre, descripcion=descripcion, peso=peso, orden=orden
        )
        await self._modelos.actualizar(modelo)
        return modelo


class QuitarDimension:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, codigo: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.quitar_dimension(codigo)
        await self._modelos.actualizar(modelo)
        return modelo


class AgregarPregunta:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        codigo: str,
        dimension_codigo: str,
        enunciado: str,
        tipo: str,
        obligatoria: bool,
        peso: Decimal,
        en_demo: bool,
        orden: int,
        ayuda: Optional[str] = None,
        opciones: Optional[list[dict]] = None,
        condicion: Optional[dict] = None,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.agregar_pregunta(
            Pregunta(
                codigo=codigo,
                dimension_codigo=dimension_codigo,
                enunciado=enunciado,
                tipo=tipo,
                obligatoria=obligatoria,
                peso=peso,
                en_demo=en_demo,
                orden=orden,
                ayuda=ayuda,
                opciones=[OpcionPregunta(**o) for o in (opciones or [])],
                condicion=CondicionActivacion(**condicion) if condicion else None,
            )
        )
        await self._modelos.actualizar(modelo)
        return modelo


class EditarPregunta:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        codigo: str,
        dimension_codigo: Optional[str] = None,
        enunciado: Optional[str] = None,
        ayuda: Optional[str] = None,
        tipo: Optional[str] = None,
        obligatoria: Optional[bool] = None,
        peso: Optional[Decimal] = None,
        en_demo: Optional[bool] = None,
        orden: Optional[int] = None,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.editar_pregunta(
            codigo,
            dimension_codigo=dimension_codigo,
            enunciado=enunciado,
            ayuda=ayuda,
            tipo=tipo,
            obligatoria=obligatoria,
            peso=peso,
            en_demo=en_demo,
            orden=orden,
        )
        await self._modelos.actualizar(modelo)
        return modelo


class QuitarPregunta:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, codigo: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.quitar_pregunta(codigo)
        await self._modelos.actualizar(modelo)
        return modelo


class AgregarNivel:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        nivel: int,
        nombre: str,
        descripcion: str,
        umbral_min: Decimal,
        umbral_max: Decimal,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.agregar_nivel(
            Nivel(
                nivel=nivel,
                nombre=nombre,
                descripcion=descripcion,
                umbral_min=umbral_min,
                umbral_max=umbral_max,
            )
        )
        await self._modelos.actualizar(modelo)
        return modelo


class EditarNivel:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        numero_nivel: int,
        nombre: Optional[str] = None,
        descripcion: Optional[str] = None,
        umbral_min: Optional[Decimal] = None,
        umbral_max: Optional[Decimal] = None,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.editar_nivel(
            numero_nivel,
            nombre=nombre,
            descripcion=descripcion,
            umbral_min=umbral_min,
            umbral_max=umbral_max,
        )
        await self._modelos.actualizar(modelo)
        return modelo


class QuitarNivel:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, numero_nivel: int) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.quitar_nivel(numero_nivel)
        await self._modelos.actualizar(modelo)
        return modelo
