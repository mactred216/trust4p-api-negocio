from datetime import datetime, timedelta, timezone

import pytest

from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)


def crear_token_prueba():
    return TokenVerificacion(
        id=None,
        tipo=TipoToken.INVITACION,
        correo_destino="ana@innovatech.com",
    )


def test_token_nuevo_esta_vigente():
    token = crear_token_prueba()
    assert token.esta_vigente() is True


def test_token_expirado_no_esta_vigente():
    token = crear_token_prueba()
    token.expira_en = datetime.now(timezone.utc) - timedelta(hours=1)
    assert token.esta_vigente() is False


def test_marcar_usado_invalida_el_token():
    token = crear_token_prueba()
    token.marcar_usado()
    assert token.esta_vigente() is False


def test_no_se_puede_usar_un_token_ya_usado():
    token = crear_token_prueba()
    token.marcar_usado()
    with pytest.raises(ValueError):
        token.marcar_usado()


def test_no_se_puede_usar_un_token_expirado():
    token = crear_token_prueba()
    token.expira_en = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(ValueError):
        token.marcar_usado()
