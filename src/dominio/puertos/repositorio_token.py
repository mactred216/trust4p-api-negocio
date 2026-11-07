from abc import ABC, abstractmethod
from typing import Optional

from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)


class RepositorioToken(ABC):
    """Puerto del dominio. Ningún adaptador se referencia aquí (ADR-011)."""

    @abstractmethod
    async def guardar(
        self, token: TokenVerificacion, codigo: str
    ) -> TokenVerificacion: ...

    @abstractmethod
    async def obtener_por_codigo(self, codigo: str) -> Optional[TokenVerificacion]: ...

    @abstractmethod
    async def actualizar(self, token: TokenVerificacion) -> None: ...

    async def consumir(
        self, codigo: str, tipo: TipoToken
    ) -> Optional[TokenVerificacion]:
        """Marca como usado un token vigente del tipo indicado y lo devuelve;
        None si no existe, es de otro tipo, venció o ya se usó. Los adaptadores
        deben hacerlo en una sola operación atómica, para que dos peticiones
        simultáneas con el mismo código no lo consuman ambas. Esta versión por
        omisión no es atómica y solo sirve para dobles de prueba."""
        token = await self.obtener_por_codigo(codigo)
        if token is None or token.tipo != tipo or not token.esta_vigente():
            return None
        token.marcar_usado()
        await self.actualizar(token)
        return token

    async def liberar(self, token: TokenVerificacion) -> None:
        """Compensación de consumir(): devuelve el token a vigente si la
        operación que lo consumió no pudo completarse. Es idempotente."""
        token.usado_en = None
        await self.actualizar(token)
