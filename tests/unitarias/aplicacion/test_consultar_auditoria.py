from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.consultar_auditoria import ConsultarAuditoria
from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.entidades.usuario import Rol, Usuario

# La bitácora guarda el id de quien actuó; al consultarla se muestra su nombre y
# su correo (único), y se puede filtrar por ellos.


def usuario(id, nombres, apellidos, correo):
    return Usuario(
        id=id,
        correo=correo,
        clave_hash="h",
        nombres=nombres,
        apellidos=apellidos,
        rol=Rol(codigo="administrador"),
    )


def registro(id, usuario_id):
    return RegistroAuditoria(
        id=id, usuario_id=usuario_id, entidad="empresas", entidad_id="e-1", accion="actualizar"
    )


ELENA = usuario("u-1", "Elena", "Rostova", "elena@trust4p.com")
JULIA = usuario("u-2", "Julia", "Herrera", "julia@trust4p.com")


def caso_uso(registros, usuarios=(ELENA, JULIA)):
    repo_auditoria = AsyncMock()
    repo_auditoria.listar.return_value = registros
    repo_usuario = AsyncMock()
    repo_usuario.listar_por_ids.side_effect = lambda ids: [u for u in usuarios if u.id in ids]
    repo_usuario.buscar.side_effect = lambda texto, limite=200: [
        u for u in usuarios if texto.lower() in f"{u.nombres} {u.apellidos} {u.correo}".lower()
    ]
    return ConsultarAuditoria(repo_auditoria, repo_usuario), repo_auditoria, repo_usuario


@pytest.mark.asyncio
async def test_cada_registro_trae_nombre_y_correo_de_quien_actuo():
    consulta, _, _ = caso_uso([registro("r1", "u-1"), registro("r2", "u-2")])

    entradas = await consulta.ejecutar()

    assert [(e.registro.id, e.usuario_nombre, e.usuario_correo) for e in entradas] == [
        ("r1", "Elena Rostova", "elena@trust4p.com"),
        ("r2", "Julia Herrera", "julia@trust4p.com"),
    ]


@pytest.mark.asyncio
async def test_resuelve_cada_usuario_una_sola_vez_aunque_aparezca_muchas():
    consulta, _, repo_usuario = caso_uso([registro(f"r{i}", "u-1") for i in range(30)])

    await consulta.ejecutar()

    repo_usuario.listar_por_ids.assert_awaited_once()
    assert set(repo_usuario.listar_por_ids.await_args.args[0]) == {"u-1"}


@pytest.mark.asyncio
async def test_una_accion_del_sistema_no_tiene_usuario_y_no_se_consulta_nada():
    consulta, _, repo_usuario = caso_uso([registro("r1", None)])

    entradas = await consulta.ejecutar()

    assert entradas[0].usuario_nombre is None and entradas[0].usuario_correo is None
    repo_usuario.listar_por_ids.assert_not_awaited()


@pytest.mark.asyncio
async def test_un_usuario_que_ya_no_existe_se_devuelve_sin_nombre_ni_correo():
    consulta, _, _ = caso_uso([registro("r1", "u-borrado")])

    entradas = await consulta.ejecutar()

    assert entradas[0].registro.usuario_id == "u-borrado"
    assert entradas[0].usuario_nombre is None and entradas[0].usuario_correo is None


@pytest.mark.asyncio
async def test_filtrar_por_nombre_o_correo_consulta_solo_a_esos_usuarios():
    consulta, repo_auditoria, _ = caso_uso([registro("r2", "u-2")])

    await consulta.ejecutar(usuario="  julia  ")

    assert repo_auditoria.listar.await_args.kwargs["usuario_ids"] == ["u-2"]


@pytest.mark.asyncio
async def test_si_nadie_coincide_no_hay_registros_y_ni_siquiera_se_consulta_la_bitacora():
    consulta, repo_auditoria, _ = caso_uso([registro("r1", "u-1")])

    assert await consulta.ejecutar(usuario="inexistente") == []
    repo_auditoria.listar.assert_not_awaited()


@pytest.mark.asyncio
async def test_un_texto_vacio_no_filtra():
    consulta, repo_auditoria, repo_usuario = caso_uso([registro("r1", "u-1")])

    await consulta.ejecutar(usuario="   ")

    repo_usuario.buscar.assert_not_awaited()
    assert repo_auditoria.listar.await_args.kwargs["usuario_ids"] is None


@pytest.mark.asyncio
async def test_los_demas_filtros_se_conservan():
    consulta, repo_auditoria, _ = caso_uso([])

    await consulta.ejecutar(entidad="empresas", entidad_id="e-1", usuario_id="u-1", limite=25)

    assert repo_auditoria.listar.await_args.kwargs == {
        "entidad": "empresas",
        "entidad_id": "e-1",
        "usuario_id": "u-1",
        "limite": 25,
        "usuario_ids": None,
    }
