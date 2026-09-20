import pytest

from src.dominio.entidades.rol import RolCatalogo


def crear_rol_prueba():
    return RolCatalogo(id="rol-1", codigo="consultor", nombre="Consultor")


def test_agregar_permiso():
    rol = crear_rol_prueba()
    rol.agregar_permiso("diagnosticos.consultar")
    assert "diagnosticos.consultar" in rol.permisos


def test_agregar_permiso_duplicado_no_lo_repite():
    rol = crear_rol_prueba()
    rol.agregar_permiso("diagnosticos.consultar")
    rol.agregar_permiso("diagnosticos.consultar")
    assert rol.permisos.count("diagnosticos.consultar") == 1


def test_quitar_permiso():
    rol = crear_rol_prueba()
    rol.agregar_permiso("diagnosticos.consultar")
    rol.quitar_permiso("diagnosticos.consultar")
    assert "diagnosticos.consultar" not in rol.permisos


def test_administrador_no_puede_perder_permiso_de_gestion_de_roles():
    rol = RolCatalogo(id="rol-admin", codigo="administrador", nombre="Administrador")
    rol.agregar_permiso("roles.gestionar")
    with pytest.raises(ValueError):
        rol.quitar_permiso("roles.gestionar")


def test_rol_de_sistema_no_puede_eliminarse():
    rol = crear_rol_prueba()
    rol.es_sistema = True
    with pytest.raises(ValueError):
        rol.eliminar()


def test_rol_normal_si_puede_eliminarse():
    rol = crear_rol_prueba()
    rol.eliminar()
    assert rol.activo is False
