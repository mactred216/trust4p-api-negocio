import os

from src.api.middleware.limite_peticiones import (LimitadorPeticiones,
                                                  limitar_peticiones)

"""RNF-09: topes de peticiones por IP de origen en los endpoints públicos o de
autenticación. Complementan el bloqueo por cuenta (HU-004). Todos ajustables
por entorno; la memoria es por instancia (ver limite_peticiones)."""


def _entero(nombre: str, defecto: str) -> int:
    return int(os.getenv(nombre, defecto))


limite_login = limitar_peticiones(
    LimitadorPeticiones(
        _entero("LIMITE_LOGIN_MAX", "30"), _entero("LIMITE_LOGIN_VENTANA", "60")
    )
)
limite_envio_correo = limitar_peticiones(
    LimitadorPeticiones(
        _entero("LIMITE_CORREO_MAX", "5"), _entero("LIMITE_CORREO_VENTANA", "900")
    )
)
limite_token = limitar_peticiones(
    LimitadorPeticiones(
        _entero("LIMITE_TOKEN_MAX", "15"), _entero("LIMITE_TOKEN_VENTANA", "900")
    )
)
limite_solicitudes = limitar_peticiones(
    LimitadorPeticiones(
        _entero("LIMITE_SOLICITUDES_MAX", "10"),
        _entero("LIMITE_SOLICITUDES_VENTANA", "3600"),
    )
)

# Lectura pública de la estructura del modelo (página de inicio): holgado, pero
# acotado por origen.
limite_modelo_publico = limitar_peticiones(
    LimitadorPeticiones(
        _entero("LIMITE_MODELO_PUBLICO_MAX", "120"),
        _entero("LIMITE_MODELO_PUBLICO_VENTANA", "60"),
    )
)
