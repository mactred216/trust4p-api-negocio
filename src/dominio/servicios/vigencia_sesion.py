"""Revalidación de la sesión en cada petición (R-16, R-17).

La sesión guarda el rol, la empresa y los permisos con que se inició. Revocarla
al cambiar cualquiera de ellos es un paso aparte que puede fallar o llegar
tarde (por ejemplo, si el inicio de sesión ocurre mientras el administrador
edita al usuario). Por eso, antes de aceptar una sesión, se compara con el
estado actual del usuario, de su rol y de su empresa: si algo cambió, la
sesión deja de valer aunque la revocación no se haya ejecutado. Ante la duda
se niega el acceso.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EstadoAcceso:
    """Lo que hoy determina el acceso de un usuario, leído de la base."""

    activo: bool
    registro_pendiente: bool
    rol_codigo: str
    empresa_id: Optional[str]
    permisos_vigentes: list[str] = field(default_factory=list)
    empresa_activa: bool = True


def motivo_invalidez(sesion: dict, estado: Optional[EstadoAcceso]) -> Optional[str]:
    """Devuelve None si la sesión sigue siendo válida o el motivo por el que
    debe descartarse."""
    if estado is None:
        return "usuario_inexistente"
    if not estado.activo:
        return "usuario_inactivo"
    if estado.registro_pendiente:
        return "registro_pendiente"
    if sesion.get("rol_codigo") != estado.rol_codigo:
        return "rol_cambiado"
    # Las sesiones creadas antes de esta regla no guardan la empresa: se
    # descartan una vez y el usuario vuelve a iniciar sesión.
    if "empresa_id" not in sesion:
        return "sesion_sin_empresa"
    if sesion.get("empresa_id") != estado.empresa_id:
        return "empresa_cambiada"
    if estado.empresa_id is not None and not estado.empresa_activa:
        return "empresa_inactiva"
    if set(sesion.get("permisos") or []) != set(estado.permisos_vigentes):
        return "permisos_cambiados"
    return None
