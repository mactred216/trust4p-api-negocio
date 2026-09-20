from src.dominio.entidades.empresa import Empresa, Sector


def crear_empresa_prueba():
    return Empresa(
        id=None,
        nombre="InnovaTech S.A.S.",
        sector=Sector(id="1", codigo="J62", nombre="Desarrollo de software"),
    )


def test_empresa_desactivada_queda_marcada_inactiva():
    empresa = crear_empresa_prueba()
    empresa.desactivar()
    assert empresa.activo is False


def test_empresa_nueva_nace_activa():
    empresa = crear_empresa_prueba()
    assert empresa.activo is True


def test_empresa_reactivada_vuelve_a_estar_activa():
    empresa = crear_empresa_prueba()
    empresa.desactivar()
    empresa.reactivar()
    assert empresa.activo is True
