from unittest.mock import AsyncMock

import bcrypt
import pytest

from src.aplicacion.casos_uso.completar_registro import (CompletarRegistro,
                                                         TokenInvalido)
from src.aplicacion.casos_uso.gestionar_empresas import (CrearEmpresa,
                                                         EditarEmpresa,
                                                         ListarEmpresas,
                                                         NitYaRegistrado)
from src.aplicacion.casos_uso.gestionar_usuarios import (CorreoYaRegistrado,
                                                         CrearUsuario,
                                                         EditarUsuario)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario

SECTOR = Sector(id="s1", codigo="J62", nombre="Software")


def empresa(
    id="emp-1", nombre="InnovaTech", nit="900123456", activo=True, sector=SECTOR
):
    return Empresa(id=id, nombre=nombre, sector=sector, nit=nit, activo=activo)


def armar_crear_usuario(existente=None, empresa_obj="por_defecto"):
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = existente
    repo_usuario.guardar.side_effect = lambda u: setattr(u, "id", "u-1") or u
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = (
        empresa() if empresa_obj == "por_defecto" else empresa_obj
    )
    repo_token = AsyncMock()
    correo = AsyncMock()
    repo_notificacion = AsyncMock()
    caso_uso = CrearUsuario(
        repo_usuario, repo_empresa, repo_token, correo, repo_notificacion
    )
    return caso_uso, repo_usuario, repo_token, correo, repo_notificacion


# ---------------- HU-026 / RF-25 ----------------


@pytest.mark.asyncio
async def test_crea_un_consultor_pendiente_con_invitacion():
    caso_uso, repo_usuario, repo_token, correo, repo_notificacion = (
        armar_crear_usuario()
    )

    usuario = await caso_uso.ejecutar(
        "Carlos@Trust4P.com", "Carlos", "Gomez", "consultor"
    )

    assert usuario.correo == "carlos@trust4p.com"
    assert usuario.rol.codigo == "consultor" and usuario.empresa_id is None
    assert usuario.registro_pendiente is True
    token, codigo = repo_token.guardar.call_args[0]
    assert token.tipo == TipoToken.INVITACION and token.usuario_id == "u-1"
    correo.enviar.assert_called_once()
    assert codigo in correo.enviar.call_args.kwargs["cuerpo"]
    assert repo_notificacion.registrar.call_args[0][0].tipo == "invitacion"


@pytest.mark.asyncio
async def test_la_clave_inicial_no_es_utilizable():
    caso_uso, repo_usuario, *_ = armar_crear_usuario()

    usuario = await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "consultor")

    assert usuario.clave_hash.startswith("$2")
    assert not bcrypt.checkpw(b"", usuario.clave_hash.encode())


@pytest.mark.asyncio
async def test_correo_duplicado_se_rechaza_sin_crear_nada():
    """HU-026 CA-01."""
    caso_uso, repo_usuario, repo_token, correo, _ = armar_crear_usuario(
        existente=object()
    )

    with pytest.raises(CorreoYaRegistrado):
        await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "consultor")
    repo_usuario.guardar.assert_not_called()
    repo_token.guardar.assert_not_called()
    correo.enviar.assert_not_called()


@pytest.mark.asyncio
async def test_representante_requiere_empresa_existente_y_activa():
    caso_uso, *_ = armar_crear_usuario()
    with pytest.raises(ValueError, match="debe pertenecer"):
        await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "representante")

    caso_uso, *_ = armar_crear_usuario(empresa_obj=None)
    with pytest.raises(ValueError, match="no existe"):
        await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "representante", "emp-9")

    caso_uso, *_ = armar_crear_usuario(empresa_obj=empresa(activo=False))
    with pytest.raises(ValueError, match="inactiva"):
        await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "representante", "emp-1")


@pytest.mark.asyncio
async def test_consultor_y_administrador_no_llevan_empresa():
    caso_uso, *_ = armar_crear_usuario()
    with pytest.raises(ValueError, match="Solo el representante"):
        await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "consultor", "emp-1")


@pytest.mark.asyncio
async def test_rol_invalido_se_rechaza():
    caso_uso, *_ = armar_crear_usuario()
    with pytest.raises(ValueError, match="Rol inválido"):
        await caso_uso.ejecutar("a@x.com", "Ana", "Perez", "superusuario")


@pytest.mark.asyncio
async def test_crea_representante_con_empresa():
    caso_uso, *_ = armar_crear_usuario()
    usuario = await caso_uso.ejecutar(
        "r@x.com", "Rita", "Lopez", "representante", "emp-1"
    )
    assert usuario.empresa_id == "emp-1"


# ---------------- completar registro de un usuario creado por el admin ----------------


def pendiente():
    return Usuario(
        id="u-1",
        correo="c@x.com",
        clave_hash="inutil",
        nombres="C",
        apellidos="C",
        rol=Rol(codigo="consultor"),
        registro_pendiente=True,
    )


def armar_completar(usuario, token):
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    return (
        CompletarRegistro(repo_token, repo_usuario, AsyncMock()),
        repo_token,
        repo_usuario,
    )


@pytest.mark.asyncio
async def test_completar_registro_de_usuario_creado_por_el_administrador():
    usuario = pendiente()
    token = TokenVerificacion(
        id="t", tipo=TipoToken.INVITACION, correo_destino="c@x.com", usuario_id="u-1"
    )
    caso_uso, repo_token, repo_usuario = armar_completar(usuario, token)

    resultado = await caso_uso.ejecutar(
        "codigo", "NuevaClave!2026a", "Carlos", "Gomez", True
    )

    assert resultado.registro_pendiente is False
    assert bcrypt.checkpw(b"NuevaClave!2026a", resultado.clave_hash.encode())
    assert resultado.acepto_tratamiento_en is not None
    assert token.usado_en is not None
    repo_usuario.actualizar.assert_called_once()
    repo_usuario.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_token_de_otro_tipo_no_completa_el_registro():
    token = TokenVerificacion(
        id="t",
        tipo=TipoToken.RESTABLECER_CLAVE,
        correo_destino="c@x.com",
        usuario_id="u-1",
    )
    caso_uso, *_ = armar_completar(pendiente(), token)
    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("codigo", "NuevaClave!2026a", "C", "G", True)


@pytest.mark.asyncio
async def test_usuario_que_ya_completo_su_registro_no_reutiliza_la_invitacion():
    usuario = pendiente()
    usuario.registro_pendiente = False
    token = TokenVerificacion(
        id="t", tipo=TipoToken.INVITACION, correo_destino="c@x.com", usuario_id="u-1"
    )
    caso_uso, *_ = armar_completar(usuario, token)
    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("codigo", "NuevaClave!2026a", "C", "G", True)


# ---------------- editar usuario (empresa asignada) ----------------


def representante():
    return Usuario(
        id="u-2",
        correo="r@x.com",
        clave_hash="h",
        nombres="R",
        apellidos="R",
        rol=Rol(codigo="representante"),
        empresa_id="emp-1",
    )


@pytest.mark.asyncio
async def test_cambiar_la_empresa_de_un_representante():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = representante()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = empresa(id="emp-2")

    usuario = await EditarUsuario(repo_usuario, repo_empresa).ejecutar(
        "u-2", empresa_id="emp-2"
    )

    assert usuario.empresa_id == "emp-2"


@pytest.mark.asyncio
async def test_cambiar_a_una_empresa_inexistente_falla():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = representante()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = None

    with pytest.raises(ValueError, match="no existe"):
        await EditarUsuario(repo_usuario, repo_empresa).ejecutar("u-2", empresa_id="x")
    repo_usuario.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_pasar_a_consultor_quita_la_empresa():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = representante()

    usuario = await EditarUsuario(repo_usuario, AsyncMock()).ejecutar(
        "u-2", rol_codigo="consultor"
    )

    assert usuario.rol.codigo == "consultor" and usuario.empresa_id is None


@pytest.mark.asyncio
async def test_editar_solo_el_nombre_no_toca_la_empresa():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = representante()

    usuario = await EditarUsuario(repo_usuario).ejecutar("u-2", nombres="Nuevo")

    assert usuario.empresa_id == "emp-1" and usuario.nombres == "Nuevo"


# ---------------- RF-24 empresas ----------------


@pytest.mark.asyncio
async def test_crear_empresa():
    repo = AsyncMock()
    repo.obtener_por_nit.return_value = None
    repo.guardar.side_effect = lambda e: setattr(e, "id", "e-1") or e

    creada = await CrearEmpresa(repo).ejecutar(
        "900123456", "Nueva SAS", SECTOR, 25, "Cali"
    )

    assert (
        creada.id == "e-1"
        and creada.nit == "900123456"
        and creada.numero_empleados == 25
    )


@pytest.mark.asyncio
async def test_crear_empresa_con_nit_existente_falla():
    repo = AsyncMock()
    repo.obtener_por_nit.return_value = empresa()

    with pytest.raises(NitYaRegistrado):
        await CrearEmpresa(repo).ejecutar("900123456", "Otra", SECTOR, 10)
    repo.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_editar_nit_a_uno_de_otra_empresa_falla():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = empresa(id="emp-1", nit="111111")
    repo.obtener_por_nit.return_value = empresa(id="emp-2", nit="222222")

    with pytest.raises(NitYaRegistrado):
        await EditarEmpresa(repo).ejecutar("emp-1", nit="222222")


@pytest.mark.asyncio
async def test_editar_nit_sin_cambios_no_choca_consigo_mismo():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = empresa(id="emp-1", nit="111111")

    await EditarEmpresa(repo).ejecutar("emp-1", nit="111111", ciudad="Cali")

    repo.obtener_por_nit.assert_not_called()


def listado():
    return [
        empresa("1", "Alfa Software", "1", True, Sector("a", "J62", "Software")),
        empresa("2", "Beta Manufactura", "2", True, Sector("b", "C10", "Manufactura")),
        empresa("3", "Gamma Software", "3", False, Sector("a", "J62", "Software")),
    ]


def repo_listado():
    repo = AsyncMock()
    repo.listar_todas.return_value = listado()
    repo.listar_activas.return_value = [e for e in listado() if e.activo]
    return repo


@pytest.mark.asyncio
async def test_listado_por_defecto_solo_muestra_activas():
    assert [e.id for e in await ListarEmpresas(repo_listado()).ejecutar()] == ["1", "2"]


@pytest.mark.asyncio
async def test_filtros_por_nombre_sector_y_estado():
    caso_uso = ListarEmpresas(repo_listado())
    assert [
        e.id for e in await caso_uso.ejecutar(solo_activas=False, nombre="software")
    ] == ["1", "3"]
    assert [e.id for e in await caso_uso.ejecutar(sector_codigo="C10")] == ["2"]
    assert [e.id for e in await caso_uso.ejecutar(estado="inactiva")] == ["3"]
    assert [e.id for e in await caso_uso.ejecutar(estado="activa", nombre="alfa")] == [
        "1"
    ]


@pytest.mark.asyncio
async def test_estado_invalido_se_rechaza():
    with pytest.raises(ValueError):
        await ListarEmpresas(repo_listado()).ejecutar(estado="rara")
