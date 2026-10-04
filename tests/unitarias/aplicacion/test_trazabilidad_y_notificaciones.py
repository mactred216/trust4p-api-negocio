from decimal import Decimal
from unittest.mock import AsyncMock

import bcrypt
import pytest

from src.api.middleware.auditoria import (diferencias, instantanea,
                                          registrar_cambio,
                                          registrar_cambio_elemento_modelo)
from src.aplicacion.casos_uso.iniciar_sesion import (CredencialesInvalidas,
                                                     IniciarSesion)
from src.aplicacion.casos_uso.radicar_solicitud import RadicarSolicitud
from src.aplicacion.casos_uso.recuperar_contrasena import RestablecerContrasena
from src.aplicacion.casos_uso.resolver_solicitud import ResolverSolicitud
from src.dominio.entidades.empresa import Sector
from src.dominio.entidades.modelo_madurez import Dimension, ModeloMadurez
from src.dominio.entidades.solicitud_acceso import (EstadoSolicitud,
                                                    SolicitudAcceso,
                                                    SolicitudYaResuelta)
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario

# ---------------- diferencias / instantaneas (RF-29, HU-030) ----------------


def test_diferencias_solo_incluye_los_campos_que_cambiaron():
    antes = {"nombres": "Ana", "apellidos": "Perez", "activo": True}
    despues = {"nombres": "Anita", "apellidos": "Perez", "activo": True}

    assert diferencias(antes, despues) == ({"nombres": "Ana"}, {"nombres": "Anita"})


def test_diferencias_en_alta_y_baja():
    assert diferencias(None, {"a": 1}) == ({}, {"a": 1})
    assert diferencias({"a": 1}, None) == ({"a": 1}, {})


def test_instantanea_serializa_decimal_y_excluye_campos_sensibles():
    d = Dimension(codigo="d1", nombre="Dim", peso=Decimal("0.5"), orden=1)
    assert instantanea(d)["peso"] == "0.5"
    usuario = {
        "correo": "a@x.com",
        "clave_hash": "$2b$secreto",
        "historial_claves": ["x"],
    }
    assert instantanea(usuario) == {"correo": "a@x.com"}


@pytest.mark.asyncio
async def test_registrar_cambio_guarda_valor_anterior_y_nuevo():
    """HU-030 CA-01."""
    repo = AsyncMock()

    await registrar_cambio(
        repo, "admin-1", "usuarios", "u-1", {"nombres": "Ana"}, {"nombres": "Anita"}
    )

    registro = repo.registrar.call_args[0][0]
    assert registro.usuario_id == "admin-1" and registro.entidad == "usuarios"
    assert registro.valores_anteriores == {"nombres": "Ana"}
    assert registro.valores_nuevos == {"nombres": "Anita"}
    assert registro.registrado_en is not None


@pytest.mark.asyncio
async def test_cambio_de_un_elemento_del_modelo_registra_antes_y_despues():
    antes = ModeloMadurez(
        id="m",
        version="1",
        nombre="M",
        dimensiones=[Dimension("d1", "Dim", Decimal("0.4"), 1)],
    )
    despues = ModeloMadurez(
        id="m",
        version="1",
        nombre="M",
        dimensiones=[Dimension("d1", "Dim", Decimal("0.6"), 1)],
    )
    repo = AsyncMock()

    await registrar_cambio_elemento_modelo(
        repo,
        "admin-1",
        "m",
        "dimension",
        antes,
        despues,
        "dimensiones",
        "codigo",
        "d1",
        "editada",
    )

    registro = repo.registrar.call_args[0][0]
    assert registro.valores_anteriores["peso"] == "0.4"
    assert registro.valores_nuevos["peso"] == "0.6"
    assert registro.valores_nuevos["elemento"] == "dimension:d1"


# ---------------- HU-001 CA-01: aviso a los administradores ----------------


def admin(id, correo, activo=True, pendiente=False):
    u = Usuario(
        id=id,
        correo=correo,
        clave_hash="h",
        nombres="Admin",
        apellidos="X",
        rol=Rol("administrador"),
        activo=activo,
    )
    u.registro_pendiente = pendiente
    return u


@pytest.mark.asyncio
async def test_radicar_notifica_a_cada_administrador_activo():
    repo_solicitud = AsyncMock()
    repo_solicitud.existe_pendiente_con_correo.return_value = False
    repo_solicitud.guardar.side_effect = lambda s: setattr(s, "id", "s-1") or s
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = None
    repo_usuario.listar_por_rol.return_value = [
        admin("1", "a1@x.com"),
        admin("2", "a2@x.com"),
        admin("3", "inactivo@x.com", activo=False),
        admin("4", "pendiente@x.com", pendiente=True),
    ]
    correo = AsyncMock()
    notificaciones = AsyncMock()

    await RadicarSolicitud(
        repo_solicitud, repo_usuario, correo, notificaciones
    ).ejecutar("Empresa SAS", "sol@x.com", "Solicitante")

    destinatarios = [c.kwargs["destinatario"] for c in correo.enviar.call_args_list]
    assert destinatarios == ["a1@x.com", "a2@x.com"]
    assert all(
        c[0][0].tipo == "solicitud_nueva"
        for c in notificaciones.registrar.call_args_list
    )


@pytest.mark.asyncio
async def test_si_el_correo_falla_la_solicitud_igual_se_radica():
    repo_solicitud = AsyncMock()
    repo_solicitud.existe_pendiente_con_correo.return_value = False
    repo_solicitud.guardar.side_effect = lambda s: setattr(s, "id", "s-1") or s
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = None
    repo_usuario.listar_por_rol.return_value = [admin("1", "a1@x.com")]
    correo = AsyncMock()
    correo.enviar.side_effect = RuntimeError("SMTP caido")
    notificaciones = AsyncMock()

    solicitud = await RadicarSolicitud(
        repo_solicitud, repo_usuario, correo, notificaciones
    ).ejecutar("Empresa SAS", "sol@x.com", "Solicitante")

    assert solicitud.id == "s-1"
    assert notificaciones.registrar.call_args[0][0].error == "SMTP caido"


@pytest.mark.asyncio
async def test_radicar_sin_dependencias_de_notificacion_sigue_funcionando():
    repo_solicitud = AsyncMock()
    repo_solicitud.existe_pendiente_con_correo.return_value = False
    repo_solicitud.guardar.side_effect = lambda s: s
    assert (
        await RadicarSolicitud(repo_solicitud).ejecutar("E", "s@x.com", "S") is not None
    )


# ---------------- HU-002: solicitud ya resuelta ----------------


def solicitud(estado=EstadoSolicitud.PENDIENTE):
    return SolicitudAcceso(
        id="s-1",
        nombre_empresa="E",
        correo_solicitante="s@x.com",
        nombre_solicitante="S",
        estado=estado,
    )


def resolver(sol):
    repo_solicitud = AsyncMock()
    repo_solicitud.obtener_por_id.return_value = sol
    repo_empresa = AsyncMock()
    return (
        ResolverSolicitud(
            repo_solicitud, repo_empresa, AsyncMock(), AsyncMock(), AsyncMock()
        ),
        repo_empresa,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "estado", [EstadoSolicitud.APROBADA, EstadoSolicitud.RECHAZADA]
)
async def test_aprobar_una_solicitud_resuelta_no_crea_empresa_huerfana(estado):
    caso_uso, repo_empresa = resolver(solicitud(estado))

    with pytest.raises(SolicitudYaResuelta):
        await caso_uso.aprobar("s-1", Sector("s", "c", "n"))
    repo_empresa.guardar.assert_not_called()


@pytest.mark.asyncio
async def test_rechazar_una_solicitud_resuelta_falla():
    caso_uso, _ = resolver(solicitud(EstadoSolicitud.APROBADA))
    with pytest.raises(SolicitudYaResuelta):
        await caso_uso.rechazar("s-1", "motivo")


def test_solicitud_ya_resuelta_sigue_siendo_un_value_error():
    assert issubclass(SolicitudYaResuelta, ValueError)


# ---------------- eventos de seguridad (RNF-22, HU-004 CA-01) ----------------


def usuario(clave="claveSegura123"):
    return Usuario(
        id="u-1",
        correo="u@x.com",
        clave_hash=bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode(),
        nombres="U",
        apellidos="X",
        rol=Rol("consultor"),
    )


def login(u, auditoria):
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = u
    repo_sesion = AsyncMock()
    repo_sesion.crear.return_value = "t"
    return IniciarSesion(repo_usuario, repo_sesion, repo_auditoria=auditoria)


@pytest.mark.asyncio
async def test_el_inicio_de_sesion_exitoso_queda_registrado_con_la_ip():
    auditoria = AsyncMock()

    await login(usuario(), auditoria).ejecutar(
        "u@x.com", "claveSegura123", ip="10.0.0.5"
    )

    registro = auditoria.registrar.call_args[0][0]
    assert registro.accion == "autenticar" and registro.usuario_id == "u-1"
    assert registro.valores_nuevos == {"resultado": "exitoso"}
    assert registro.direccion_ip == "10.0.0.5"
    assert "claveSegura123" not in str(registro)


@pytest.mark.asyncio
async def test_los_intentos_fallidos_y_el_bloqueo_quedan_registrados():
    auditoria = AsyncMock()
    caso_uso = login(usuario(), auditoria)

    for _ in range(5):
        with pytest.raises(CredencialesInvalidas):
            await caso_uso.ejecutar("u@x.com", "mala", ip="1.1.1.1")

    resultados = [
        c[0][0].valores_nuevos["resultado"] for c in auditoria.registrar.call_args_list
    ]
    assert resultados == ["fallido"] * 4 + ["cuenta_bloqueada"]


@pytest.mark.asyncio
async def test_un_correo_inexistente_no_deja_registro_con_datos_de_nadie():
    auditoria = AsyncMock()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = None

    with pytest.raises(CredencialesInvalidas):
        await IniciarSesion(
            repo_usuario, AsyncMock(), repo_auditoria=auditoria
        ).ejecutar("no@x.com", "x")

    auditoria.registrar.assert_not_called()


@pytest.mark.asyncio
async def test_restablecer_contrasena_deja_registro_sin_la_clave():
    u = usuario()
    token = TokenVerificacion(
        id="t",
        tipo=TipoToken.RESTABLECER_CLAVE,
        correo_destino=u.correo,
        usuario_id=u.id,
    )
    repo_token = AsyncMock()
    repo_token.obtener_por_codigo.return_value = token
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_correo.return_value = u
    auditoria = AsyncMock()

    await RestablecerContrasena(
        repo_usuario, repo_token, AsyncMock(), auditoria
    ).ejecutar("codigo", "NuevaClave!2026z")

    registro = auditoria.registrar.call_args[0][0]
    assert registro.usuario_id == "u-1" and registro.valores_nuevos == {
        "clave": "restablecida"
    }
    assert "NuevaClave" not in str(registro)
