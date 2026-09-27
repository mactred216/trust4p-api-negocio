from decimal import Decimal
from typing import Optional

from bson import Decimal128, ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.dominio.entidades.diagnostico import (ESTADO_CERRADO, Diagnostico,
                                               DimensionResultado,
                                               Recomendacion, Respuesta,
                                               ResultadoDiagnostico)
from src.dominio.puertos.repositorio_diagnostico import RepositorioDiagnostico


class RepositorioMongoDiagnostico(RepositorioDiagnostico):

    def __init__(self, db: AsyncIOMotorDatabase):
        self._coleccion = db["diagnosticos"]

    async def guardar(self, diagnostico: Diagnostico) -> Diagnostico:
        doc = self._a_documento(diagnostico)
        resultado = await self._coleccion.insert_one(doc)
        diagnostico.id = str(resultado.inserted_id)
        return diagnostico

    async def obtener_por_id(self, diagnostico_id: str) -> Optional[Diagnostico]:
        try:
            id_valido = ObjectId(diagnostico_id)
        except InvalidId:
            return None
        doc = await self._coleccion.find_one({"_id": id_valido})
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def actualizar(self, diagnostico: Diagnostico) -> None:
        await self._coleccion.update_one(
            {"_id": ObjectId(diagnostico.id)},
            {"$set": self._a_documento(diagnostico)},
        )

    async def obtener_en_curso_por_empresa(
        self, empresa_id: str
    ) -> Optional[Diagnostico]:
        doc = await self._coleccion.find_one(
            {"empresa_id": empresa_id, "estado": {"$ne": ESTADO_CERRADO}}
        )
        if doc is None:
            return None
        return self._a_entidad(doc)

    async def contar_por_empresa(self, empresa_id: str) -> int:
        return await self._coleccion.count_documents({"empresa_id": empresa_id})

    async def listar_por_empresa(self, empresa_id: str) -> list[Diagnostico]:
        cursor = self._coleccion.find({"empresa_id": empresa_id}).sort(
            "consecutivo", -1
        )
        documentos = await cursor.to_list(length=None)
        return [self._a_entidad(doc) for doc in documentos]

    def _a_entidad(self, doc: dict) -> Diagnostico:
        return Diagnostico(
            id=str(doc["_id"]),
            empresa_id=doc["empresa_id"],
            empresa_nombre=doc["empresa_nombre"],
            usuario_id=doc["usuario_id"],
            modelo_version=doc["modelo_version"],
            consecutivo=doc["consecutivo"],
            estado=doc.get("estado", "borrador"),
            porcentaje_avance=doc.get("porcentaje_avance", 0),
            respuestas=[
                Respuesta(
                    pregunta_codigo=r["pregunta_codigo"],
                    dimension_codigo=r["dimension_codigo"],
                    opciones_codigo=r.get("opciones_codigo", []),
                    valor=self._decimal(r.get("valor")),
                    texto=r.get("texto"),
                    respondida_en=r["respondida_en"],
                )
                for r in doc.get("respuestas", [])
            ],
            resultado=self._resultado_a_entidad(doc.get("resultado")),
            recomendaciones=[
                Recomendacion(
                    dimension_codigo=r["dimension_codigo"],
                    titulo=r["titulo"],
                    contenido=r["contenido"],
                    prioridad=r["prioridad"],
                )
                for r in doc.get("recomendaciones", [])
            ],
            motivo_fallo=doc.get("motivo_fallo"),
            iniciado_en=doc["iniciado_en"],
            completado_en=doc.get("completado_en"),
            evaluado_en=doc.get("evaluado_en"),
            cerrado_en=doc.get("cerrado_en"),
        )

    def _resultado_a_entidad(
        self, doc: Optional[dict]
    ) -> Optional[ResultadoDiagnostico]:
        if doc is None:
            return None
        return ResultadoDiagnostico(
            indice_global=self._decimal(doc["indice_global"]),
            nivel=doc["nivel"],
            nivel_nombre=doc["nivel_nombre"],
            nivel_descripcion=doc["nivel_descripcion"],
            dimensiones=[
                DimensionResultado(
                    codigo=d["codigo"], puntaje=self._decimal(d["puntaje"])
                )
                for d in doc["dimensiones"]
            ],
            perfil_cultural_codigo=doc["perfil_cultural_codigo"],
            perfil_cultura_descripcion=doc["perfil_cultura_descripcion"],
            dimensiones_observaciones=doc["dimensiones_observaciones"],
            lienzo_negocio=doc["lienzo_negocio"],
            sintesis=doc["sintesis"],
        )

    def _a_documento(self, diagnostico: Diagnostico) -> dict:
        return {
            "empresa_id": diagnostico.empresa_id,
            "empresa_nombre": diagnostico.empresa_nombre,
            "usuario_id": diagnostico.usuario_id,
            "modelo_version": diagnostico.modelo_version,
            "consecutivo": diagnostico.consecutivo,
            "estado": diagnostico.estado,
            "porcentaje_avance": diagnostico.porcentaje_avance,
            "respuestas": [
                {
                    "pregunta_codigo": r.pregunta_codigo,
                    "dimension_codigo": r.dimension_codigo,
                    "opciones_codigo": r.opciones_codigo,
                    "valor": Decimal128(r.valor) if r.valor is not None else None,
                    "texto": r.texto,
                    "respondida_en": r.respondida_en,
                }
                for r in diagnostico.respuestas
            ],
            "resultado": self._resultado_a_documento(diagnostico.resultado),
            "recomendaciones": [
                {
                    "dimension_codigo": r.dimension_codigo,
                    "titulo": r.titulo,
                    "contenido": r.contenido,
                    "prioridad": r.prioridad,
                }
                for r in diagnostico.recomendaciones
            ],
            "motivo_fallo": diagnostico.motivo_fallo,
            "iniciado_en": diagnostico.iniciado_en,
            "completado_en": diagnostico.completado_en,
            "evaluado_en": diagnostico.evaluado_en,
            "cerrado_en": diagnostico.cerrado_en,
        }

    def _resultado_a_documento(
        self, resultado: Optional[ResultadoDiagnostico]
    ) -> Optional[dict]:
        if resultado is None:
            return None
        return {
            "indice_global": Decimal128(resultado.indice_global),
            "nivel": resultado.nivel,
            "nivel_nombre": resultado.nivel_nombre,
            "nivel_descripcion": resultado.nivel_descripcion,
            "dimensiones": [
                {"codigo": d.codigo, "puntaje": Decimal128(d.puntaje)}
                for d in resultado.dimensiones
            ],
            "perfil_cultural_codigo": resultado.perfil_cultural_codigo,
            "perfil_cultura_descripcion": resultado.perfil_cultura_descripcion,
            "dimensiones_observaciones": resultado.dimensiones_observaciones,
            "lienzo_negocio": resultado.lienzo_negocio,
            "sintesis": resultado.sintesis,
        }

    @staticmethod
    def _decimal(valor) -> Optional[Decimal]:
        if valor is None:
            return None
        return (
            valor.to_decimal() if isinstance(valor, Decimal128) else Decimal(str(valor))
        )
