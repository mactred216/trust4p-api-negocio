from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.puertos.repositorio_auditoria import RepositorioAuditoria


async def registrar_accion(
    repo_auditoria: RepositorioAuditoria,
    usuario_id: str | None,
    entidad: str,
    entidad_id: str | None,
    accion: str,
    valores_anteriores: dict | None = None,
    valores_nuevos: dict | None = None,
) -> None:
    """
    Punto único de registro de auditoría. Nunca incluir clave_hash, token_hash
    ni codigo_hash en valores_anteriores/valores_nuevos (regla de seguridad).
    """
    registro = RegistroAuditoria(
        id=None,
        usuario_id=usuario_id,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        valores_anteriores=valores_anteriores,
        valores_nuevos=valores_nuevos,
    )
    await repo_auditoria.registrar(registro)


def _valor_serializable(valor):
    """Convierte a tipos que Mongo y JSON aceptan (Decimal -> str, fechas ISO,
    enumeraciones por su valor, dataclasses anidadas por sus campos)."""
    from dataclasses import asdict, is_dataclass
    from datetime import datetime
    from decimal import Decimal
    from enum import Enum

    if is_dataclass(valor) and not isinstance(valor, type):
        return _valor_serializable(asdict(valor))
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, Enum):
        return valor.value
    if isinstance(valor, dict):
        return {k: _valor_serializable(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_valor_serializable(v) for v in valor]
    return valor


CAMPOS_SENSIBLES = {"clave_hash", "historial_claves", "token_hash", "codigo_hash"}


def instantanea(objeto, campos: list[str] | None = None) -> dict | None:
    """Estado serializable de un objeto (dataclass, dict u objeto con atributos)
    para compararlo antes/después. Nunca incluye campos sensibles."""
    if objeto is None:
        return None
    if isinstance(objeto, dict):
        base = objeto
    else:
        from dataclasses import asdict, is_dataclass

        base = asdict(objeto) if is_dataclass(objeto) else vars(objeto)
    nombres = campos if campos is not None else list(base)
    return {
        n: _valor_serializable(base.get(n))
        for n in nombres
        if n not in CAMPOS_SENSIBLES
    }


def diferencias(antes: dict | None, despues: dict | None) -> tuple[dict, dict]:
    """Solo los campos que cambiaron: (valores anteriores, valores nuevos).
    Si no existía antes (alta) o ya no existe (baja), devuelve el estado
    completo del lado que existe."""
    if antes is None:
        return {}, dict(despues or {})
    if despues is None:
        return dict(antes), {}
    claves = [k for k in despues if antes.get(k) != despues.get(k)]
    return {k: antes.get(k) for k in claves}, {k: despues.get(k) for k in claves}


async def registrar_cambio(
    repo_auditoria: RepositorioAuditoria,
    usuario_id: str | None,
    entidad: str,
    entidad_id: str | None,
    antes: dict | None,
    despues: dict | None,
    accion: str = "actualizar",
    extra: dict | None = None,
) -> None:
    """RF-29/HU-030: registra la acción con el valor anterior y el nuevo de
    cada campo modificado."""
    anteriores, nuevos = diferencias(antes, despues)
    if extra:
        anteriores = {**extra, **anteriores} if anteriores else anteriores
        nuevos = {**extra, **nuevos} if nuevos else nuevos
    await registrar_accion(
        repo_auditoria,
        usuario_id,
        entidad,
        entidad_id,
        accion,
        valores_anteriores=anteriores or None,
        valores_nuevos=nuevos or None,
    )


async def registrar_cambio_elemento_modelo(
    repo_auditoria: RepositorioAuditoria,
    usuario_id: str | None,
    modelo_id: str,
    etiqueta: str,
    antes_modelo,
    despues_modelo,
    coleccion: str,
    atributo: str,
    valor,
    operacion: str,
) -> None:
    """Cambio de un elemento (dimensión, pregunta, nivel o eje) del modelo de
    madurez, con su estado anterior y nuevo."""

    def buscar(modelo):
        if modelo is None:
            return None
        for e in getattr(modelo, coleccion):
            if str(getattr(e, atributo)) == str(valor):
                return e
        return None

    await registrar_cambio(
        repo_auditoria,
        usuario_id,
        "modelos_madurez",
        modelo_id,
        instantanea(buscar(antes_modelo)),
        instantanea(buscar(despues_modelo)),
        extra={
            "elemento": f"{etiqueta}:{valor}",
            "operacion": f"{etiqueta}_{operacion}",
        },
    )
