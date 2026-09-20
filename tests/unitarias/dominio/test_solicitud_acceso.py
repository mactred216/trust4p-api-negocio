import pytest

from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudAcceso)


def crear_solicitud_prueba():
    return SolicitudAcceso(
        id=None,
        nombre_empresa="InnovaTech S.A.S.",
        correo_solicitante="ana.perez@innovatech.com",
        nombre_solicitante="Ana Pérez",
    )


def test_solicitud_nueva_nace_pendiente():
    solicitud = crear_solicitud_prueba()
    assert solicitud.estado == EstadoSolicitud.PENDIENTE


def test_aprobar_solicitud_pendiente():
    solicitud = crear_solicitud_prueba()
    solicitud.aprobar(empresa_id="emp-123")
    assert solicitud.estado == EstadoSolicitud.APROBADA
    assert solicitud.empresa_id == "emp-123"
    assert solicitud.resuelto_en is not None


def test_no_se_puede_aprobar_dos_veces():
    solicitud = crear_solicitud_prueba()
    solicitud.aprobar(empresa_id="emp-123")
    with pytest.raises(ValueError):
        solicitud.aprobar(empresa_id="emp-456")


def test_rechazar_solicitud_pendiente_con_motivo():
    solicitud = crear_solicitud_prueba()
    solicitud.rechazar(motivo="La empresa no cumple el criterio de tamaño")
    assert solicitud.estado == EstadoSolicitud.RECHAZADA
    assert solicitud.motivo_rechazo == "La empresa no cumple el criterio de tamaño"


def test_rechazar_sin_motivo_falla():
    solicitud = crear_solicitud_prueba()
    with pytest.raises(ValueError):
        solicitud.rechazar(motivo="")


def test_rechazar_con_motivo_solo_espacios_falla():
    solicitud = crear_solicitud_prueba()
    with pytest.raises(ValueError):
        solicitud.rechazar(motivo="   ")


def test_no_se_puede_rechazar_una_ya_aprobada():
    solicitud = crear_solicitud_prueba()
    solicitud.aprobar(empresa_id="emp-123")
    with pytest.raises(ValueError):
        solicitud.rechazar(motivo="Cambio de decisión")
