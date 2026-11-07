from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from src.dominio.entidades.diagnostico import Diagnostico


class RepositorioDiagnostico(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-011)."""

    @abstractmethod
    async def guardar(self, diagnostico: Diagnostico) -> Diagnostico: ...

    @abstractmethod
    async def obtener_por_id(self, diagnostico_id: str) -> Optional[Diagnostico]: ...

    @abstractmethod
    async def actualizar(self, diagnostico: Diagnostico) -> None: ...

    @abstractmethod
    async def obtener_en_curso_por_empresa(
        self, empresa_id: str
    ) -> Optional[Diagnostico]:
        """R-05: a lo sumo un diagnóstico sin cerrar por empresa."""
        ...

    @abstractmethod
    async def contar_por_empresa(self, empresa_id: str) -> int:
        """RF-12 (dictionary): base para asignar el siguiente consecutivo."""
        ...

    @abstractmethod
    async def listar_por_empresa(self, empresa_id: str) -> list[Diagnostico]: ...

    @abstractmethod
    async def listar_por_estado(self, estado: str) -> list[Diagnostico]:
        """Diagnósticos en un estado dado (p. ej. los 'fallido' por reprocesar),
        del más antiguo al más reciente."""
        ...

    @abstractmethod
    async def listar_por_modelo_version(self, modelo_version: str) -> list[Diagnostico]:
        """RF-35: diagnósticos históricos calculados con una versión del modelo."""
        ...

    # ---- C7: evaluación en segundo plano sin duplicados y recuperable ----
    # Los adaptadores deben resolver cada una en una sola operación atómica.
    # Estas versiones por omisión no lo son y solo sirven para dobles de prueba.

    async def actualizar_si_estado(
        self, diagnostico: Diagnostico, estado_esperado: str
    ) -> bool:
        """Guarda el diagnóstico solo si en la base sigue en estado_esperado.
        Devuelve False si otra petición lo cambió antes."""
        await self.actualizar(diagnostico)
        return True

    async def reclamar_evaluacion(
        self, diagnostico_id: str, token: str, vence_en: datetime
    ) -> bool:
        """Marca que una evaluación empezó (hasta vence_en). Falla si el
        diagnóstico no está 'completado' o si otra evaluación vigente ya lo
        tiene, de modo que nunca corren dos a la vez."""
        return True

    async def liberar_evaluacion(self, diagnostico_id: str, token: str) -> None:
        """Retira la marca puesta con ese mismo token (idempotente)."""
        return None

    async def marcar_evaluaciones_interrumpidas(
        self, en_cola_antes_de: datetime, motivo: str
    ) -> list[str]:
        """Pasa a 'fallido', con el motivo, los diagnósticos que siguen
        'completado' desde antes de en_cola_antes_de y sin una evaluación
        vigente: su evaluación se perdió (p. ej. terminó la instancia).
        Devuelve sus identificadores."""
        return []
