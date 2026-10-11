from decimal import Decimal
from typing import Optional

from bson import Decimal128, ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.modelo_madurez import (CondicionActivacion,
                                                  Dimension, EjePerfilCultural,
                                                  ModeloMadurez, Nivel,
                                                  OpcionPregunta,
                                                  PerfilCulturaCatalogo,
                                                  Pregunta)
from src.dominio.puertos.repositorio_modelo_madurez import \
    RepositorioModeloMadurez


class RepositorioMongoModeloMadurez(RepositorioModeloMadurez):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["modelos_madurez"]

    async def guardar(self, modelo: ModeloMadurez) -> ModeloMadurez:
        doc = self._a_documento(modelo)
        resultado = await self._coleccion.insert_one(doc)
        modelo.id = str(resultado.inserted_id)
        return modelo

    async def obtener_por_id(self, modelo_id: str) -> Optional[ModeloMadurez]:
        try:
            id_valido = ObjectId(modelo_id)
        except InvalidId:
            # RNF-07: un id con formato inválido no debe filtrar detalles internos;
            # se trata igual que "no encontrado".
            return None
        doc = await self._coleccion.find_one({"_id": id_valido})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def obtener_por_version(self, version: str) -> Optional[ModeloMadurez]:
        doc = await self._coleccion.find_one({"version": version})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def obtener_vigente(self) -> Optional[ModeloMadurez]:
        doc = await self._coleccion.find_one(
            {"publicado": True}, sort=[("publicado_en", -1)]
        )
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def actualizar(self, modelo: ModeloMadurez) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(modelo.id)},
            {"$set": self._a_documento(modelo)},
        )

    async def listar(self) -> list[ModeloMadurez]:
        cursor = self._coleccion.find().sort("creado_en", -1)
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> ModeloMadurez:
        return ModeloMadurez(
            id=str(doc["_id"]),
            version=doc["version"],
            nombre=doc["nombre"],
            descripcion=doc.get("descripcion"),
            escala_min=doc.get("escala_min", 1),
            escala_max=doc.get("escala_max", 10),
            publicado=doc.get("publicado", False),
            publicado_en=doc.get("publicado_en"),
            publicado_por=doc.get("publicado_por"),
            dimensiones=[
                Dimension(
                    codigo=d["codigo"],
                    nombre=d["nombre"],
                    descripcion=d.get("descripcion"),
                    peso=self._decimal(d["peso"]),
                    orden=d["orden"],
                )
                for d in doc.get("dimensiones", [])
            ],
            niveles=[
                Nivel(
                    nivel=n["nivel"],
                    nombre=n["nombre"],
                    descripcion=n["descripcion"],
                    umbral_min=self._decimal(n["umbral_min"]),
                    umbral_max=self._decimal(n["umbral_max"]),
                )
                for n in doc.get("niveles", [])
            ],
            preguntas=[
                Pregunta(
                    codigo=p["codigo"],
                    dimension_codigo=p["dimension_codigo"],
                    enunciado=p["enunciado"],
                    tipo=p["tipo"],
                    obligatoria=p["obligatoria"],
                    peso=self._decimal(p["peso"]),
                    en_demo=p["en_demo"],
                    orden=p["orden"],
                    ayuda=p.get("ayuda"),
                    opciones=[
                        OpcionPregunta(
                            codigo=o["codigo"],
                            etiqueta=o["etiqueta"],
                            valor=self._decimal(o["valor"]),
                        )
                        for o in p.get("opciones", [])
                    ],
                    condicion=(
                        CondicionActivacion(**p["condicion"])
                        if p.get("condicion")
                        else None
                    ),
                    activo=p.get("activo", True),
                )
                for p in doc.get("preguntas", [])
            ],
            ejes_perfil_cultural=[
                EjePerfilCultural(
                    codigo=e["codigo"],
                    nombre=e["nombre"],
                    polo_alto_codigo=e["polo_alto_codigo"],
                    polo_alto_nombre=e["polo_alto_nombre"],
                    polo_bajo_codigo=e["polo_bajo_codigo"],
                    polo_bajo_nombre=e["polo_bajo_nombre"],
                    dimension_codigo=e["dimension_codigo"],
                    umbral=self._decimal(e["umbral"]),
                )
                for e in doc.get("ejes_perfil_cultural", [])
            ],
            perfiles_cultura=[
                PerfilCulturaCatalogo(
                    codigo=c["codigo"],
                    nombre=c["nombre"],
                    descripcion=c["descripcion"],
                    activo=c.get("activo", True),
                )
                for c in doc.get("perfiles_cultura", [])
            ],
            creado_en=doc["creado_en"],
        )

    def _a_documento(self, modelo: ModeloMadurez) -> dict:
        return {
            "version": modelo.version,
            "nombre": modelo.nombre,
            "descripcion": modelo.descripcion,
            "escala_min": modelo.escala_min,
            "escala_max": modelo.escala_max,
            "publicado": modelo.publicado,
            "publicado_en": modelo.publicado_en,
            "publicado_por": modelo.publicado_por,
            "dimensiones": [
                {
                    "codigo": d.codigo,
                    "nombre": d.nombre,
                    "descripcion": d.descripcion,
                    "peso": Decimal128(d.peso),
                    "orden": d.orden,
                }
                for d in modelo.dimensiones
            ],
            "niveles": [
                {
                    "nivel": n.nivel,
                    "nombre": n.nombre,
                    "descripcion": n.descripcion,
                    "umbral_min": Decimal128(n.umbral_min),
                    "umbral_max": Decimal128(n.umbral_max),
                }
                for n in modelo.niveles
            ],
            "preguntas": [
                {
                    "codigo": p.codigo,
                    "dimension_codigo": p.dimension_codigo,
                    "enunciado": p.enunciado,
                    "ayuda": p.ayuda,
                    "tipo": p.tipo,
                    "obligatoria": p.obligatoria,
                    "peso": Decimal128(p.peso),
                    "en_demo": p.en_demo,
                    "orden": p.orden,
                    "opciones": [
                        {
                            "codigo": o.codigo,
                            "etiqueta": o.etiqueta,
                            "valor": Decimal128(o.valor),
                        }
                        for o in p.opciones
                    ],
                    "condicion": (
                        {
                            "pregunta_codigo": p.condicion.pregunta_codigo,
                            "operador": p.condicion.operador,
                            "valor": p.condicion.valor,
                        }
                        if p.condicion
                        else None
                    ),
                    "activo": p.activo,
                }
                for p in modelo.preguntas
            ],
            "ejes_perfil_cultural": [
                {
                    "codigo": e.codigo,
                    "nombre": e.nombre,
                    "polo_alto_codigo": e.polo_alto_codigo,
                    "polo_alto_nombre": e.polo_alto_nombre,
                    "polo_bajo_codigo": e.polo_bajo_codigo,
                    "polo_bajo_nombre": e.polo_bajo_nombre,
                    "dimension_codigo": e.dimension_codigo,
                    "umbral": Decimal128(e.umbral),
                }
                for e in modelo.ejes_perfil_cultural
            ],
            "perfiles_cultura": [
                {
                    "codigo": c.codigo,
                    "nombre": c.nombre,
                    "descripcion": c.descripcion,
                    "activo": c.activo,
                }
                for c in modelo.perfiles_cultura
            ],
            "creado_en": modelo.creado_en,
        }

    @staticmethod
    def _decimal(valor) -> Decimal:
        return (
            valor.to_decimal() if isinstance(valor, Decimal128) else Decimal(str(valor))
        )
