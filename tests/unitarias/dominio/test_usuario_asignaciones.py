import pytest

from src.dominio.entidades.usuario import Rol, Usuario


def crear_consultor_prueba():
    return Usuario(
        id="cons-1",
        correo="carlos@trust4p.com",
        clave_hash="hash",
        nombres="Carlos",
        apellidos="Gómez",
        rol=Rol(codigo="consultor"),
    )


def test_asignar_empresa_a_consultor():
    consultor = crear_consultor_prueba()
    consultor.asignar_empresa("emp-1")
    assert "emp-1" in consultor.empresas_asignadas_vigentes()


def test_no_se_puede_asignar_dos_veces_la_misma_empresa():
    consultor = crear_consultor_prueba()
    consultor.asignar_empresa("emp-1")
    with pytest.raises(ValueError):
        consultor.asignar_empresa("emp-1")


def test_solo_consultor_puede_recibir_asignaciones():
    representante = Usuario(
        id="rep-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
    )
    with pytest.raises(ValueError):
        representante.asignar_empresa("emp-1")


def test_finalizar_asignacion_la_quita_de_vigentes():
    consultor = crear_consultor_prueba()
    consultor.asignar_empresa("emp-1")
    consultor.finalizar_asignacion("emp-1")
    assert "emp-1" not in consultor.empresas_asignadas_vigentes()


def test_finalizar_asignacion_inexistente_falla():
    consultor = crear_consultor_prueba()
    with pytest.raises(ValueError):
        consultor.finalizar_asignacion("emp-inexistente")


def test_reasignar_empresa_ya_finalizada_es_valido():
    """Se puede volver a asignar una empresa cuya asignación anterior ya terminó."""
    consultor = crear_consultor_prueba()
    consultor.asignar_empresa("emp-1")
    consultor.finalizar_asignacion("emp-1")
    consultor.asignar_empresa("emp-1")  # no debe lanzar excepción
    assert "emp-1" in consultor.empresas_asignadas_vigentes()
