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
