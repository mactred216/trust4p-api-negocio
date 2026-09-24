from abc import ABC, abstractmethod


class ServicioCorreo(ABC):
    """Puerto de salida hacia un proveedor de envío de correo electrónico."""

    @abstractmethod
    async def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None: ...
