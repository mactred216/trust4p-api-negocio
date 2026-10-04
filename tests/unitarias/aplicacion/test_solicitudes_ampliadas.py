from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.completar_registro import (ConsultarInvitacion,
                                                         TokenInvalido)
from src.aplicacion.casos_uso.consultar_solicitudes import (ConsultarSolicitud,
                                                            ListarSolicitudes)
from src.aplicacion.casos_uso.radicar_solicitud import (RadicarSolicitud,
                                                        SectorInvalido,
                                                        SolicitudDuplicada)
from src.aplicacion.casos_uso.resolver_solicitud import (ResolverSolicitud,
                                                         SolicitudNoEncontrada)
from src.aplicacion.servicios.enlaces import enlace_frontend
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudAcceso)
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario

SECTOR = Sector(id="s1", codigo="logistica", nombre="Cadena de suministro")

DATOS = dict(
    nombre_empresa="LogiTrans SAS",
    correo_solicitante="mariana@logitrans.com",
    nombre_solicitante="Mariana Silva",
    nit="900842119",
    sector_codigo="logistica",
    numero_empleados=120,
    ciudad="Bogotá",
    cargo="VP de Transformación",
    telefono="3001234567",
    acepto_tratamiento=True,
)


def armar(
    correo_existente=None, nit_pendiente=False, empresa_con_nit=None, sector=SECTOR
):
    repo_solicitud = AsyncMock()
    repo_solicitud.existe_pendiente_con_correo.return_value = False
    repo_solicitud.existe_pendiente_con_nit.return_value = nit_pendiente
    repo_solicitud.guardar.side_effect = lambda s: setattr(s, "id", "s-1") or s
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = correo_existente
    repo_usuario.listar_por_rol.return_value = []
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_nit.return_value = empresa_con_nit
    repo_sector = AsyncMock()
    repo_sector.obtener_por_codigo.return_value = sector
    caso = RadicarSolicitud(
        repo_solicitud,
        repo_usuario,
        AsyncMock(),
        AsyncMock(),
        repo_empresa,
        repo_sector,
    )
    return caso, repo_solicitud


@pytest.mark.asyncio
async def test_radicar_guarda_todos_los_datos_de_rf_01():
    caso, repo = armar()

    s = await caso.ejecutar(**DATOS)

    assert (s.nit, s.sector_codigo, s.sector_nombre) == (
        "900842119",
        "logistica",
        "Cadena de suministro",
    )
    assert (s.numero_empleados, s.cargo, s.telefono, s.ciudad) == (
        120,
        "VP de Transformación",
        "3001234567",
        "Bogotá",
    )
    assert s.estado == EstadoSolicitud.PENDIENTE
    assert s.acepto_tratamiento_en is not None and s.version_politica_aceptada


@pytest.mark.asyncio
async def test_sector_inexistente_se_rechaza_sin_guardar():
    caso, repo = armar(sector=None)
    with pytest.raises(SectorInvalido):
        await caso.ejecutar(**DATOS)
    repo.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_correo_de_un_usuario_existente_es_duplicidad():
    caso, repo = armar(correo_existente=object())
    with pytest.raises(SolicitudDuplicada):
        await caso.ejecutar(**DATOS)
    repo.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_nit_con_solicitud_pendiente_es_duplicidad():
    caso, _ = armar(nit_pendiente=True)
    with pytest.raises(SolicitudDuplicada):
        await caso.ejecutar(**DATOS)


@pytest.mark.asyncio
async def test_nit_de_una_empresa_registrada_es_duplicidad():
    caso, _ = armar(
        empresa_con_nit=Empresa(id="e", nombre="X", sector=SECTOR, nit="900842119")
    )
    with pytest.raises(SolicitudDuplicada):
        await caso.ejecutar(**DATOS)


# ---------------- aprobar con los datos de la solicitud ----------------


def solicitud_completa():
    return SolicitudAcceso(
        id="s-1",
        nombre_empresa="LogiTrans SAS",
        correo_solicitante="m@x.com",
        nombre_solicitante="Mariana",
        nit="900842119",
        sector_codigo="logistica",
        sector_nombre="Cadena de suministro",
        numero_empleados=120,
        ciudad="Bogotá",
        cargo="VP",
        telefono="300",
    )


def armar_resolver(solicitud, sector=SECTOR):
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = solicitud
    repo_empresa = AsyncMock()
    repo_empresa.guardar.side_effect = lambda e: setattr(e, "id", "e-1") or e
    repo_sector = AsyncMock()
    repo_sector.obtener_por_codigo.return_value = sector
    correo = AsyncMock()
    caso = ResolverSolicitud(
        repo_solicitud, repo_empresa, AsyncMock(), correo, AsyncMock(), repo_sector
    )
    return caso, repo_empresa, correo


@pytest.mark.asyncio
async def test_aprobar_crea_la_empresa_con_los_datos_de_la_solicitud():
    caso, repo_empresa, correo = armar_resolver(solicitud_completa())

    empresa, codigo = await caso.aprobar("s-1")

    assert (empresa.nit, empresa.numero_empleados, empresa.ciudad) == (
        "900842119",
        120,
        "Bogotá",
    )
    assert empresa.sector.codigo == "logistica"
    cuerpo = correo.enviar.call_args.kwargs["cuerpo"]
    assert f"/registro?codigo={codigo}" in cuerpo and codigo in cuerpo


@pytest.mark.asyncio
async def test_aprobar_con_un_sector_indicado_lo_prefiere():
    caso, _, _ = armar_resolver(solicitud_completa())
    otro = Sector("s2", "fintech", "Fintech")

    empresa, _ = await caso.aprobar("s-1", otro)

    assert empresa.sector.codigo == "fintech"


@pytest.mark.asyncio
async def test_aprobar_sin_sector_declarado_ni_indicado_falla_sin_crear_empresa():
    solicitud = solicitud_completa()
    solicitud.sector_codigo = None
    caso, repo_empresa, _ = armar_resolver(solicitud)

    with pytest.raises(ValueError, match="sector"):
        await caso.aprobar("s-1")
    repo_empresa.guardar.assert_not_called()


# ---------------- listados ----------------


@pytest.mark.asyncio
async def test_listar_solicitudes_filtra_por_estado_valido():
    repo = AsyncMock()
    repo.listar.return_value = [solicitud_completa()]

    resultado = await ListarSolicitudes(repo).ejecutar("pendiente")

    repo.listar.assert_called_once_with("pendiente")
    assert len(resultado) == 1


@pytest.mark.asyncio
async def test_listar_solicitudes_rechaza_un_estado_inventado():
    with pytest.raises(ValueError):
        await ListarSolicitudes(AsyncMock()).ejecutar("rara")


@pytest.mark.asyncio
async def test_consultar_solicitud_inexistente():
    repo = AsyncMock()
    repo.obtener_por_id.return_value = None
    with pytest.raises(SolicitudNoEncontrada):
        await ConsultarSolicitud(repo).ejecutar("x")


# ---------------- invitación ----------------


def armar_invitacion(token, solicitud=None, usuario=None, empresa=None):
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = solicitud
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = usuario
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = empresa
    return ConsultarInvitacion(repo_token, repo_usuario, repo_solicitud, repo_empresa)


@pytest.mark.asyncio
async def test_invitacion_de_una_solicitud_aprobada():
    token = TokenVerificacion(
        id="t", tipo=TipoToken.INVITACION, correo_destino="m@x.com", solicitud_id="s-1"
    )

    datos = await armar_invitacion(token, solicitud=solicitud_completa()).ejecutar(
        "codigo-largo-123"
    )

    assert (datos.correo, datos.nombre, datos.rol_codigo) == (
        "m@x.com",
        "Mariana",
        "representante",
    )
    assert (datos.empresa_nombre, datos.empresa_nit) == ("LogiTrans SAS", "900842119")


@pytest.mark.asyncio
async def test_invitacion_de_un_usuario_creado_por_el_administrador():
    token = TokenVerificacion(
        id="t", tipo=TipoToken.INVITACION, correo_destino="c@x.com", usuario_id="u-1"
    )
    usuario = Usuario(
        id="u-1",
        correo="c@x.com",
        clave_hash="h",
        nombres="Carlos",
        apellidos="Gómez",
        rol=Rol("consultor"),
        registro_pendiente=True,
    )

    datos = await armar_invitacion(token, usuario=usuario).ejecutar("codigo-largo-123")

    assert (datos.nombre, datos.rol_codigo, datos.empresa_nombre) == (
        "Carlos Gómez",
        "consultor",
        None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "variante", ["inexistente", "usada", "vencida", "de_otro_tipo"]
)
async def test_invitacion_invalida(variante):
    base = dict(id="t", correo_destino="m@x.com", solicitud_id="s-1")
    token = {
        "inexistente": None,
        "usada": TokenVerificacion(
            tipo=TipoToken.INVITACION, usado_en=datetime.now(timezone.utc), **base
        ),
        "vencida": TokenVerificacion(
            tipo=TipoToken.INVITACION,
            expira_en=datetime.now(timezone.utc) - timedelta(hours=1),
            **base,
        ),
        "de_otro_tipo": TokenVerificacion(tipo=TipoToken.RESTABLECER_CLAVE, **base),
    }[variante]

    with pytest.raises(TokenInvalido):
        await armar_invitacion(token, solicitud=solicitud_completa()).ejecutar(
            "codigo-largo-123"
        )


# ---------------- enlaces ----------------


def test_enlace_usa_la_url_del_frontend_de_el_entorno(monkeypatch):
    monkeypatch.setenv("URL_FRONTEND", "https://app.trust4p.com/")
    assert (
        enlace_frontend("/registro", "abc-DEF_123")
        == "https://app.trust4p.com/registro?codigo=abc-DEF_123"
    )


def test_enlace_por_defecto_apunta_al_frontend_local(monkeypatch):
    monkeypatch.delenv("URL_FRONTEND", raising=False)
    assert enlace_frontend("/restablecer", "x").startswith(
        "http://localhost:5173/restablecer?codigo="
    )
