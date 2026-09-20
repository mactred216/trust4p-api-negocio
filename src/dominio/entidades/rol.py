from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class RolCatalogo:
    id: Optional[str]
    codigo: str
    nombre: str
    descripcion: str = ""
    es_sistema: bool = False  # RF-28: los roles de sistema no se pueden eliminar
    permisos: list[str] = field(default_factory=list)  # códigos de Permiso
    activo: bool = True
    creado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def agregar_permiso(self, codigo_permiso: str) -> None:
        if codigo_permiso not in self.permisos:
            self.permisos.append(codigo_permiso)

    def quitar_permiso(self, codigo_permiso: str) -> None:
        """No se puede quitar el permiso de gestión de roles al propio rol administrador."""
        if self.codigo == "administrador" and codigo_permiso == "roles.gestionar":
            raise ValueError(
                "El rol administrador debe conservar siempre el permiso de gestión de roles"
            )
        if codigo_permiso in self.permisos:
            self.permisos.remove(codigo_permiso)

    def eliminar(self) -> None:
        if self.es_sistema:
            raise ValueError("Los roles de sistema no pueden eliminarse")
        self.activo = False
