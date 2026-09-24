import pytest

from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario_prueba():
    return Usuario(
        id=None,
        correo="test@trust4p.com",
        clave_hash="hash",
        nombres="Test",
        apellidos="Usuario",
        rol=Rol(codigo="representante"),
    )


def test_usuario_se_bloquea_tras_cinco_intentos():
    usuario = crear_usuario_prueba()
    for _ in range(5):
        usuario.registrar_intento_fallido()
    assert usuario.puede_intentar_acceso() is False


def test_usuario_reinicia_intentos_tras_acceso_exitoso():
    usuario = crear_usuario_prueba()
    usuario.registrar_intento_fallido()
    usuario.reiniciar_intentos()
    assert usuario.intentos_fallidos == 0


def test_usuario_con_menos_de_cinco_intentos_puede_acceder():
    usuario = crear_usuario_prueba()
    usuario.registrar_intento_fallido()
    usuario.registrar_intento_fallido()
    assert usuario.puede_intentar_acceso() is True


# RF-48: historial de las últimas 5 contraseñas
def test_registrar_clave_mueve_la_actual_al_historial():
    usuario = crear_usuario_prueba()
    usuario.registrar_clave("hash-nuevo")
    assert usuario.clave_hash == "hash-nuevo"
    assert usuario.historial_claves == ["hash"]


def test_hashes_recientes_incluye_actual_y_pasadas():
    usuario = crear_usuario_prueba()
    usuario.registrar_clave("hash-2")
    usuario.registrar_clave("hash-3")
    assert usuario.hashes_recientes() == ["hash-3", "hash-2", "hash"]


def test_historial_de_claves_no_excede_el_maximo():
    usuario = crear_usuario_prueba()
    for i in range(10):
        usuario.registrar_clave(f"hash-{i}")
    assert len(usuario.hashes_recientes()) == Usuario.HISTORIAL_CLAVES_MAXIMO


# HU-006: gestión de perfil (RF-06)
def test_actualizar_perfil_actualiza_solo_campos_enviados():
    usuario = crear_usuario_prueba()
    usuario.actualizar_perfil(cargo="Gerente de innovación")
    assert usuario.cargo == "Gerente de innovación"
    assert usuario.nombres == "Test"  # no se tocó
    assert usuario.telefono is None


def test_actualizar_perfil_actualiza_varios_campos():
    usuario = crear_usuario_prueba()
    usuario.actualizar_perfil(
        nombres="Nuevo", apellidos="Apellido", cargo="CTO", telefono="3001234567"
    )
    assert usuario.nombres == "Nuevo"
    assert usuario.apellidos == "Apellido"
    assert usuario.cargo == "CTO"
    assert usuario.telefono == "3001234567"


# RF-44: eliminación de datos personales
def test_anonimizar_elimina_datos_identificables_y_desactiva():
    usuario = crear_usuario_prueba()
    usuario.cargo = "CTO"
    usuario.telefono = "3001234567"

    usuario.anonimizar()

    assert usuario.activo is False
    assert usuario.correo != "test@trust4p.com"
    assert "anonimo" in usuario.correo
    assert usuario.nombres != "Test"
    assert usuario.cargo is None
    assert usuario.telefono is None


def test_anonimizar_cuenta_ya_inactiva_falla():
    usuario = crear_usuario_prueba()
    usuario.desactivar()

    with pytest.raises(ValueError):
        usuario.anonimizar()
