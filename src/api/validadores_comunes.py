import re
from decimal import Decimal
from typing import Optional


def clave_cumple_politica(v: str) -> str:
    """RF-48: política mínima de complejidad de contraseña (12 caracteres,
    al menos 3 de mayúsculas/minúsculas/números/especiales)."""
    if len(v) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")

    tiene_mayuscula = re.search(r"[A-Z]", v) is not None
    tiene_minuscula = re.search(r"[a-z]", v) is not None
    tiene_numero = re.search(r"\d", v) is not None
    tiene_especial = re.search(r"[^A-Za-z0-9]", v) is not None

    tipos_presentes = sum(
        [tiene_mayuscula, tiene_minuscula, tiene_numero, tiene_especial]
    )
    if tipos_presentes < 3:
        raise ValueError(
            "La contraseña debe combinar al menos tres de los siguientes: "
            "mayúsculas, minúsculas, números y caracteres especiales"
        )
    return v


def texto_no_vacio(v: str, minimo: int = 1, maximo: int = 500) -> str:
    """Validador reutilizable para campos de texto obligatorios."""
    v = v.strip()
    if not v:
        raise ValueError("Este campo no puede estar vacío")
    if len(v) < minimo:
        raise ValueError(f"Debe tener al menos {minimo} caracteres")
    if len(v) > maximo:
        raise ValueError(f"No puede exceder {maximo} caracteres")
    return v


def texto_opcional_no_vacio(
    v: Optional[str], minimo: int = 1, maximo: int = 500
) -> Optional[str]:
    """Validador reutilizable para campos de texto opcionales (PATCH): si se
    envía, debe cumplir las mismas reglas que texto_no_vacio."""
    if v is None:
        return v
    v = v.strip()
    if not v:
        raise ValueError("Si se envía este campo, no puede estar vacío")
    if len(v) < minimo:
        raise ValueError(f"Debe tener al menos {minimo} caracteres")
    if len(v) > maximo:
        raise ValueError(f"No puede exceder {maximo} caracteres")
    return v


def descripcion_opcional(v: Optional[str], maximo: int = 1000) -> Optional[str]:
    """Validador para campos descriptivos libres: pueden venir vacíos (se
    normalizan a None), solo se limita su longitud máxima."""
    if v is None:
        return v
    v = v.strip()
    if len(v) > maximo:
        raise ValueError(f"No puede exceder {maximo} caracteres")
    return v or None


def peso_valido(v: Decimal) -> Decimal:
    """Un peso relativo (dimensión o pregunta) debe estar en (0, 1]."""
    if v <= 0 or v > 1:
        raise ValueError("El peso debe ser mayor que 0 y menor o igual a 1")
    return v


def peso_opcional_valido(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is None:
        return v
    return peso_valido(v)


def entero_positivo(v: int) -> int:
    if v <= 0:
        raise ValueError("Debe ser un entero positivo")
    return v


def entero_positivo_opcional(v: Optional[int]) -> Optional[int]:
    if v is None:
        return v
    return entero_positivo(v)
