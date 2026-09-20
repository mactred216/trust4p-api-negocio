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
