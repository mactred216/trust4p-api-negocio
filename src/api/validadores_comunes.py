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
