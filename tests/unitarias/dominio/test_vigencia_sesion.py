"""C6: una sesión solo vale mientras coincida con el estado actual del usuario."""
from src.dominio.servicios.vigencia_sesion import (EstadoAcceso,
                                                   motivo_invalidez)

SESION = {
    "usuario_id": "u-1",
    "rol_codigo": "representante",
    "empresa_id": "emp-1",
    "permisos": ["diagnosticos.iniciar", "diagnosticos.consultar"],
}


def estado(**cambios) -> EstadoAcceso:
    base = dict(
        activo=True,
        registro_pendiente=False,
        rol_codigo="representante",
        empresa_id="emp-1",
        permisos_vigentes=["diagnosticos.consultar", "diagnosticos.iniciar"],
        empresa_activa=True,
    )
    base.update(cambios)
    return EstadoAcceso(**base)


def test_sesion_que_coincide_con_el_estado_actual_es_valida():
    # el orden de los permisos no importa
    assert motivo_invalidez(SESION, estado()) is None


def test_usuario_borrado_invalida_la_sesion():
    assert motivo_invalidez(SESION, None) == "usuario_inexistente"


def test_usuario_desactivado_invalida_la_sesion():
    assert motivo_invalidez(SESION, estado(activo=False)) == "usuario_inactivo"


def test_registro_pendiente_invalida_la_sesion():
    assert motivo_invalidez(SESION, estado(registro_pendiente=True)) == "registro_pendiente"


def test_cambio_de_rol_invalida_la_sesion():
    assert motivo_invalidez(SESION, estado(rol_codigo="consultor")) == "rol_cambiado"


def test_cambio_de_empresa_invalida_la_sesion():
    assert motivo_invalidez(SESION, estado(empresa_id="emp-2")) == "empresa_cambiada"


def test_empresa_desactivada_invalida_la_sesion_del_representante():
    assert motivo_invalidez(SESION, estado(empresa_activa=False)) == "empresa_inactiva"


def test_permiso_retirado_del_rol_invalida_la_sesion():
    assert (
        motivo_invalidez(SESION, estado(permisos_vigentes=["diagnosticos.consultar"]))
        == "permisos_cambiados"
    )


def test_permiso_agregado_al_rol_tambien_obliga_a_renovar_la_sesion():
    nuevos = ["diagnosticos.consultar", "diagnosticos.iniciar", "informes.descargar"]
    assert motivo_invalidez(SESION, estado(permisos_vigentes=nuevos)) == "permisos_cambiados"


def test_sesion_anterior_a_la_regla_sin_empresa_se_descarta():
    sesion = {k: v for k, v in SESION.items() if k != "empresa_id"}
    assert motivo_invalidez(sesion, estado()) == "sesion_sin_empresa"


def test_consultor_sin_empresa_propia_es_valido():
    sesion = dict(SESION, rol_codigo="consultor", empresa_id=None)
    assert motivo_invalidez(sesion, estado(rol_codigo="consultor", empresa_id=None)) is None
