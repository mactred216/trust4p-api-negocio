from unittest.mock import AsyncMock

import bcrypt
import pytest

from src.aplicacion.casos_uso.iniciar_sesion import (
    BloqueoCorreosDesconocidos, CredencialesInvalidas, CuentaBloqueada,
    CuentaInactiva, IniciarSesion)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.rol import RolCatalogo
from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario(clave="claveSegura123", empresa_id=None):
    return Usuario(
        id="1",
        correo="admin@trust4p.com",
        clave_hash=bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode(),
        nombres="Admin",
        apellidos="Trust4P",
        rol=Rol(codigo="administrador"),
        empresa_id=empresa_id,
    )


def repo_usuario_con(usuario):
    repo = AsyncMock()
    repo.obtener_por_correo.return_value = usuario
    return repo


@pytest.mark.asyncio
async def test_los_permisos_de_la_sesion_se_resuelven_desde_el_catalogo_de_roles():
    """R-16 / HU-028: no se usa una copia desactualizada guardada en el usuario."""
    usuario = crear_usuario()
    usuario.rol.permisos = ["copia.desactualizada"]
    repo_sesion = AsyncMock()
    repo_sesion.crear.return_value = "t"
    repo_rol = AsyncMock()
    repo_rol.obtener_por_codigo.return_value = RolCatalogo(
        id="r", codigo="administrador", nombre="Admin", permisos=["a.b", "c.d"]
    )

    await IniciarSesion(repo_usuario_con(usuario), repo_sesion, repo_rol).ejecutar(
        "admin@trust4p.com", "claveSegura123"
    )

    assert repo_sesion.crear.call_args[0][0].rol.permisos == ["a.b", "c.d"]


@pytest.mark.asyncio
async def test_correo_inexistente_se_bloquea_como_uno_existente_tras_cinco_intentos():
    """HU-004 CA-02: el bloqueo no permite distinguir si el correo existe."""
    caso_uso = IniciarSesion(repo_usuario_con(None), AsyncMock())

    for _ in range(5):
        with pytest.raises(CredencialesInvalidas):
            await caso_uso.ejecutar("fantasma@trust4p.com", "x")
    with pytest.raises(CuentaBloqueada):
        await caso_uso.ejecutar("fantasma@trust4p.com", "x")


@pytest.mark.asyncio
async def test_secuencia_de_respuestas_igual_para_correo_existente_y_no_existente():
    existente = crear_usuario()

    async def secuencia(repo, correo):
        caso_uso = IniciarSesion(repo, AsyncMock())
        resultado = []
        for _ in range(7):
            try:
                await caso_uso.ejecutar(correo, "mala")
                resultado.append("ok")
            except CredencialesInvalidas:
                resultado.append("401")
            except CuentaBloqueada:
                resultado.append("423")
        return resultado

    con_cuenta = await secuencia(repo_usuario_con(existente), existente.correo)
    sin_cuenta = await secuencia(repo_usuario_con(None), "otro@trust4p.com")

    assert con_cuenta == sin_cuenta == ["401"] * 5 + ["423"] * 2


def test_bloqueo_de_correos_desconocidos_no_distingue_mayusculas():
    bloqueo = BloqueoCorreosDesconocidos()
    for _ in range(5):
        bloqueo.registrar_fallo("A@x.com")
    assert bloqueo.esta_bloqueado("a@X.com")
    assert not bloqueo.esta_bloqueado("b@x.com")


@pytest.mark.asyncio
async def test_empresa_desactivada_impide_el_inicio_de_sesion():
    """RF-24 paso 4."""
    repo_sesion = AsyncMock()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = Empresa(
        id="emp-1", nombre="X", sector=Sector("s", "c", "n"), activo=False
    )

    with pytest.raises(CuentaInactiva):
        await IniciarSesion(
            repo_usuario_con(crear_usuario(empresa_id="emp-1")),
            repo_sesion,
            repo_empresa=repo_empresa,
        ).ejecutar("admin@trust4p.com", "claveSegura123")
    repo_sesion.crear.assert_not_called()


@pytest.mark.asyncio
async def test_empresa_activa_permite_el_inicio_de_sesion():
    repo_sesion = AsyncMock()
    repo_sesion.crear.return_value = "t"
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = Empresa(
        id="emp-1", nombre="X", sector=Sector("s", "c", "n")
    )

    token = await IniciarSesion(
        repo_usuario_con(crear_usuario(empresa_id="emp-1")),
        repo_sesion,
        repo_empresa=repo_empresa,
    ).ejecutar("admin@trust4p.com", "claveSegura123")

    assert token == "t"
