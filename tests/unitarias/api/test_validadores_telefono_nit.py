import pytest

from src.api.validadores_comunes import nit_valido, telefono_valido


@pytest.mark.parametrize(
    "v", ["3001234567", "+57 300 123 4567", "300-123-4567", "6021234567"]
)
def test_telefonos_validos(v):
    assert telefono_valido(v) == v


@pytest.mark.parametrize(
    "v", ["abc", "123", "30012345678901234", "300 ABC 4567", "++573001234567"]
)
def test_telefonos_invalidos(v):
    with pytest.raises(ValueError):
        telefono_valido(v)


def test_telefono_opcional_acepta_none_pero_no_un_texto_vacio():
    assert telefono_valido(None) is None
    with pytest.raises(ValueError):
        telefono_valido("   ")


@pytest.mark.parametrize("v", ["900123456", "900123456-7", "12345"])
def test_nits_validos(v):
    assert nit_valido(v) == v


@pytest.mark.parametrize(
    "v", ["abc", "1234", "900.123.456", "900123456-78", "9001234567890123456"]
)
def test_nits_invalidos(v):
    with pytest.raises(ValueError):
        nit_valido(v)
