from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.completar_registro import (AutorizacionRequerida,
                                                         CompletarRegistro,
                                                         TokenInvalido)
from src.dominio.entidades.solicitud_acceso import SolicitudAcceso
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_token_prueba():
    return TokenVerificacion(
        id="tok-1",
        tipo=TipoToken.INVITACION,
        correo_destino="ana@innovatech.com",
        solicitud_id="sol-1",
    )


def crear_solicitud_aprobada():
    solicitud = SolicitudAcceso(
        id="sol-1",
        nombre_empresa="InnovaTech",
        correo_solicitante="ana@innovatech.com",
        nombre_solicitante="Ana Pérez",
    )
    solicitud.aprobar(empresa_id="emp-1")
    return solicitud


@pytest.mark.asyncio
async def test_completar_registro_exitoso():
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = crear_token_prueba()
    repo_usuario = AsyncMock()
    repo_usuario.guardar.side_effect = lambda u: u
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = crear_solicitud_aprobada()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)
    usuario = await caso_uso.ejecutar(
        codigo_token="codigo-valido",
        clave="ClaveSegura123",
        nombres="Ana",
        apellidos="Pérez",
        acepto_tratamiento=True,
    )

    assert usuario.correo == "ana@innovatech.com"
    assert usuario.empresa_id == "emp-1"
    assert usuario.rol.codigo == "representante"
    assert usuario.acepto_tratamiento_en is not None
    assert usuario.version_politica_aceptada == "1.0"
    repo_token.actualizar.assert_called_once()


@pytest.mark.asyncio
async def test_sin_autorizacion_tratamiento_falla():
    repo_token = AsyncMock()
    repo_usuario = AsyncMock()
    repo_solicitud = AsyncMock()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)

    with pytest.raises(AutorizacionRequerida):
        await caso_uso.ejecutar(
            codigo_token="cualquiera",
            clave="clave",
            nombres="A",
            apellidos="B",
            acepto_tratamiento=False,
        )
    repo_usuario.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_token_inexistente_falla():
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = None
    repo_usuario = AsyncMock()
    repo_solicitud = AsyncMock()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar(
            codigo_token="codigo-invalido",
            clave="clave",
            nombres="A",
            apellidos="B",
            acepto_tratamiento=True,
        )


@pytest.mark.asyncio
async def test_token_ya_usado_falla():
    token = crear_token_prueba()
    token.marcar_usado()
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_usuario = AsyncMock()
    repo_solicitud = AsyncMock()

    caso_uso = CompletarRegistro(repo_token, repo_usuario, repo_solicitud)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar(
            codigo_token="codigo-usado",
            clave="clave",
            nombres="A",
            apellidos="B",
            acepto_tratamiento=True,
        )


# ---------------- Datos de la invitación (pantalla de registro) ----------------


def armar_consultar_invitacion(token, usuario=None, solicitud=None, empresa=None):
    from src.aplicacion.casos_uso.completar_registro import ConsultarInvitacion

    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = solicitud
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = empresa
    return ConsultarInvitacion(repo_token, repo_usuario, repo_solicitud, repo_empresa)


@pytest.mark.asyncio
async def test_consultar_invitacion_de_solicitud_aprobada():
    solicitud = crear_solicitud_aprobada()
    solicitud.nit = "900123456-7"
    caso_uso = armar_consultar_invitacion(crear_token_prueba(), solicitud=solicitud)

    datos = await caso_uso.ejecutar("codigo")

    assert datos.correo == "ana@innovatech.com"
    assert datos.nombre == "Ana Pérez"
    assert datos.rol_codigo == "representante"
    assert datos.empresa_nombre == "InnovaTech"
    assert datos.empresa_nit == "900123456-7"


@pytest.mark.asyncio
async def test_consultar_invitacion_de_usuario_creado_por_el_administrador():
    from src.dominio.entidades.empresa import Empresa, Sector

    token = crear_token_prueba()
    token.solicitud_id = None
    token.usuario_id = "u-1"
    usuario = Usuario(
        id="u-1",
        correo="ana@innovatech.com",
        clave_hash="x",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id="emp-1",
        registro_pendiente=True,
    )
    empresa = Empresa(
        id="emp-1",
        nombre="InnovaTech",
        nit="900123456-7",
        sector=Sector("s", "tecnologia", "Tecnología"),
    )
    caso_uso = armar_consultar_invitacion(token, usuario=usuario, empresa=empresa)

    datos = await caso_uso.ejecutar("codigo")

    assert datos.nombre == "Ana Pérez"
    assert datos.empresa_nombre == "InnovaTech"


@pytest.mark.asyncio
async def test_consultar_invitacion_rechaza_codigo_inexistente():
    caso_uso = armar_consultar_invitacion(None)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("no-existe")


@pytest.mark.asyncio
async def test_consultar_invitacion_rechaza_token_de_otro_tipo():
    token = crear_token_prueba()
    token.tipo = TipoToken.RESTABLECER_CLAVE
    caso_uso = armar_consultar_invitacion(token, solicitud=crear_solicitud_aprobada())

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("codigo")


@pytest.mark.asyncio
async def test_consultar_invitacion_rechaza_usuario_que_ya_completo_su_registro():
    token = crear_token_prueba()
    token.solicitud_id = None
    token.usuario_id = "u-1"
    usuario = Usuario(
        id="u-1",
        correo="ana@innovatech.com",
        clave_hash="x",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        registro_pendiente=False,
    )
    caso_uso = armar_consultar_invitacion(token, usuario=usuario)

    with pytest.raises(TokenInvalido):
        await caso_uso.ejecutar("codigo")
