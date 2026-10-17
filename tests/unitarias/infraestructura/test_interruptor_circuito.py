from src.infraestructura.clientes.interruptor_circuito import \
    InterruptorDeCircuito


class RelojFalso:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def crear(umbral=3, enfriamiento=60.0):
    reloj = RelojFalso()
    return InterruptorDeCircuito(umbral, enfriamiento, reloj), reloj


def test_cerrado_permite_las_llamadas():
    interruptor, _ = crear()
    assert interruptor.estado == "cerrado"
    assert interruptor.permitir()


def test_se_abre_tras_el_umbral_de_fallos_seguidos():
    interruptor, _ = crear(umbral=3)
    for _ in range(2):
        interruptor.registrar_fallo()
    assert interruptor.permitir()
    interruptor.registrar_fallo()
    assert interruptor.estado == "abierto"
    assert not interruptor.permitir()


def test_un_exito_reinicia_la_cuenta_de_fallos():
    interruptor, _ = crear(umbral=3)
    interruptor.registrar_fallo()
    interruptor.registrar_fallo()
    interruptor.registrar_exito()
    interruptor.registrar_fallo()
    interruptor.registrar_fallo()
    assert interruptor.estado == "cerrado"


def test_pasado_el_enfriamiento_deja_pasar_una_sola_llamada_de_sondeo():
    interruptor, reloj = crear(umbral=1, enfriamiento=60)
    interruptor.registrar_fallo()
    reloj.t += 59
    assert not interruptor.permitir()
    reloj.t += 2
    assert interruptor.estado == "semiabierto"
    assert interruptor.permitir()
    assert not interruptor.permitir()


def test_el_sondeo_exitoso_cierra_el_circuito():
    interruptor, reloj = crear(umbral=1, enfriamiento=60)
    interruptor.registrar_fallo()
    reloj.t += 61
    assert interruptor.permitir()
    interruptor.registrar_exito()
    assert interruptor.estado == "cerrado"
    assert interruptor.permitir()


def test_el_sondeo_fallido_vuelve_a_abrir_el_circuito():
    interruptor, reloj = crear(umbral=3, enfriamiento=60)
    for _ in range(3):
        interruptor.registrar_fallo()
    reloj.t += 61
    assert interruptor.permitir()
    interruptor.registrar_fallo()
    assert interruptor.estado == "abierto"
    assert not interruptor.permitir()
    reloj.t += 61
    assert interruptor.permitir()


def test_segundos_para_reintento():
    interruptor, reloj = crear(umbral=1, enfriamiento=60)
    assert interruptor.segundos_para_reintento() == 0
    interruptor.registrar_fallo()
    reloj.t += 20
    assert 40 <= interruptor.segundos_para_reintento() <= 41
