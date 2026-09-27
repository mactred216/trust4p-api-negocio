import re
from decimal import Decimal
from typing import Optional

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  OpcionPregunta, Pregunta)
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
        opciones: Optional[list[dict]] = None,
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
            opciones=(
                [OpcionPregunta(**o) for o in opciones]
                if opciones is not None
                else None
            ),
        )
        await self._modelos.actualizar(modelo)
        return modelo


class DesactivarPregunta:
    """RF-28: se marca inactiva sin eliminarla del histórico (en vez de un
    borrado físico)."""

    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, codigo: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.desactivar_pregunta(codigo)
        await self._modelos.actualizar(modelo)
        return modelo


class ReactivarPregunta:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, codigo: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.reactivar_pregunta(codigo)
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


class AgregarEjePerfilCultural:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        codigo: str,
        nombre: str,
        polo_alto_codigo: str,
        polo_alto_nombre: str,
        polo_bajo_codigo: str,
        polo_bajo_nombre: str,
        dimension_codigo: str,
        umbral: Decimal,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.agregar_eje_perfil_cultural(
            EjePerfilCultural(
                codigo=codigo,
                nombre=nombre,
                polo_alto_codigo=polo_alto_codigo,
                polo_alto_nombre=polo_alto_nombre,
                polo_bajo_codigo=polo_bajo_codigo,
                polo_bajo_nombre=polo_bajo_nombre,
                dimension_codigo=dimension_codigo,
                umbral=umbral,
            )
        )
        await self._modelos.actualizar(modelo)
        return modelo


class EditarEjePerfilCultural:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(
        self,
        modelo_id: str,
        codigo: str,
        nombre: Optional[str] = None,
        polo_alto_codigo: Optional[str] = None,
        polo_alto_nombre: Optional[str] = None,
        polo_bajo_codigo: Optional[str] = None,
        polo_bajo_nombre: Optional[str] = None,
        dimension_codigo: Optional[str] = None,
        umbral: Optional[Decimal] = None,
    ) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.editar_eje_perfil_cultural(
            codigo,
            nombre=nombre,
            polo_alto_codigo=polo_alto_codigo,
            polo_alto_nombre=polo_alto_nombre,
            polo_bajo_codigo=polo_bajo_codigo,
            polo_bajo_nombre=polo_bajo_nombre,
            dimension_codigo=dimension_codigo,
            umbral=umbral,
        )
        await self._modelos.actualizar(modelo)
        return modelo


class QuitarEjePerfilCultural:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, codigo: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.quitar_eje_perfil_cultural(codigo)
        await self._modelos.actualizar(modelo)
        return modelo


class Publicar:
    """RF-33/RF-34: publica la versión vigente, ensamblando R-02, R-03 y R-04."""

    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str, publicado_por: str) -> ModeloMadurez:
        modelo = await self._modelos.obtener_por_id(modelo_id)
        if modelo is None:
            raise ModeloNoEncontrado()

        modelo.publicar(publicado_por)
        await self._modelos.actualizar(modelo)
        return modelo


class ObtenerVersionVigente:
    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self) -> ModeloMadurez:
        modelo = await self._modelos.obtener_vigente()
        if modelo is None:
            raise ModeloNoEncontrado()
        return modelo


def _siguiente_version(version_actual: str) -> str:
    """RF-33 paso 1: incrementa el número de versión anterior. Si el
    identificador termina en un número, lo incrementa; si no, le añade '-2'
    (el campo es un identificador legible en texto libre, no un entero)."""
    coincidencia = re.search(r"(\d+)$", version_actual)
    if coincidencia:
        numero = int(coincidencia.group(1)) + 1
        return version_actual[: coincidencia.start()] + str(numero)
    return f"{version_actual}-2"


class CrearNuevaVersion:
    """RF-34 paso 2: la vía prescrita para modificar una versión publicada —
    clona su configuración completa (dimensiones, niveles, preguntas) en una
    versión nueva, sin publicar, lista para editarse."""

    def __init__(self, repo: RepositorioModeloMadurez):
        self._modelos = repo

    async def ejecutar(self, modelo_id: str) -> ModeloMadurez:
        origen = await self._modelos.obtener_por_id(modelo_id)
        if origen is None:
            raise ModeloNoEncontrado()

        nueva_version = _siguiente_version(origen.version)
        while await self._modelos.obtener_por_version(nueva_version) is not None:
            nueva_version = _siguiente_version(nueva_version)

        clon = ModeloMadurez(
            id=None,
            version=nueva_version,
            nombre=origen.nombre,
            descripcion=origen.descripcion,
            escala_min=origen.escala_min,
            escala_max=origen.escala_max,
            dimensiones=[
                Dimension(
                    codigo=d.codigo,
                    nombre=d.nombre,
                    descripcion=d.descripcion,
                    peso=d.peso,
                    orden=d.orden,
                )
                for d in origen.dimensiones
            ],
            niveles=[
                Nivel(
                    nivel=n.nivel,
                    nombre=n.nombre,
                    descripcion=n.descripcion,
                    umbral_min=n.umbral_min,
                    umbral_max=n.umbral_max,
                )
                for n in origen.niveles
            ],
            preguntas=[
                Pregunta(
                    codigo=p.codigo,
                    dimension_codigo=p.dimension_codigo,
                    enunciado=p.enunciado,
                    tipo=p.tipo,
                    obligatoria=p.obligatoria,
                    peso=p.peso,
                    en_demo=p.en_demo,
                    orden=p.orden,
                    ayuda=p.ayuda,
                    opciones=[
                        OpcionPregunta(
                            codigo=o.codigo, etiqueta=o.etiqueta, valor=o.valor
                        )
                        for o in p.opciones
                    ],
                    condicion=(
                        CondicionActivacion(
                            pregunta_codigo=p.condicion.pregunta_codigo,
                            operador=p.condicion.operador,
                            valor=p.condicion.valor,
                        )
                        if p.condicion
                        else None
                    ),
                )
                for p in origen.preguntas
            ],
        )
        return await self._modelos.guardar(clon)
