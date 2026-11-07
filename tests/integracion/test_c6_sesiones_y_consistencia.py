"""C6: consistencia de rol, empresa y permisos frente a fallos intermedios,
cambios de empresa, revocación y concurrencia, contra MongoDB real.

Cada caso reproduce una ventana de la Tabla 18 y comprueba que, aunque el paso
de revocación falle o llegue tarde, la sesión con el acceso anterior ya no se
acepta (bloqueo seguro)."""
import asyncio

import pytest

from src.aplicacion.casos_uso.completar_registro import (CompletarRegistro,
                                                         TokenInvalido)
from src.aplicacion.casos_uso.gestionar_empresas import DesactivarEmpresa
from src.aplicacion.casos_uso.gestionar_roles import QuitarPermisoDeRol
from src.aplicacion.casos_uso.gestionar_usuarios import (DesactivarUsuario,
                                                         EditarUsuario)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.rol import RolCatalogo
from src.dominio.entidades.solicitud_acceso import SolicitudAcceso
from src.dominio.entidades.token_verificacion import (TipoToken,
                                                      TokenVerificacion)
from src.dominio.entidades.usuario import Rol, Usuario
from src.infraestructura.persistencia.repositorio_mongo_empresa import \
    RepositorioMongoEmpresa
from src.infraestructura.persistencia.repositorio_mongo_rol import \
    RepositorioMongoRol
from src.infraestructura.persistencia.repositorio_mongo_sesion import \
    RepositorioMongoSesion
from src.infraestructura.persistencia.repositorio_mongo_solicitud import \
    RepositorioMongoSolicitud
from src.infraestructura.persistencia.repositorio_mongo_token import \
    RepositorioMongoToken
from src.infraestructura.persistencia.repositorio_mongo_usuario import \
    RepositorioMongoUsuario

SECTOR = Sector(id="sec-1", codigo="servicios", nombre="Servicios")
PERMISOS_CONSULTOR = ["diagnosticos.consultar", "recomendaciones.registrar"]
PERMISOS_REPRESENTANTE = ["diagnosticos.iniciar", "diagnosticos.consultar"]


class RevocacionQueFalla(RepositorioMongoSesion):
    """Simula la caída de la base justo en el paso de revocación."""

    async def revocar_todas_de_usuario(self, usuario_id: str) -> None:
        raise RuntimeError("fallo simulado al revocar")


async def sembrar(db):
    roles = RepositorioMongoRol(db)
    await roles.guardar(
        RolCatalogo(id=None, codigo="consultor", nombre="Consultor", permisos=list(PERMISOS_CONSULTOR))
    )
    await roles.guardar(
        RolCatalogo(id=None, codigo="representante", nombre="Representante", permisos=list(PERMISOS_REPRESENTANTE))
    )
    empresas = RepositorioMongoEmpresa(db)
    emp_a = await empresas.guardar(Empresa(id=None, nombre="QA Empresa A", sector=SECTOR))
    emp_b = await empresas.guardar(Empresa(id=None, nombre="QA Empresa B", sector=SECTOR))
    return emp_a, emp_b


async def nuevo_usuario(db, correo, rol, permisos, empresa_id=None) -> Usuario:
    return await RepositorioMongoUsuario(db).guardar(
        Usuario(
            id=None,
            correo=correo,
            clave_hash="x",
            nombres="QA",
            apellidos="Prueba",
            rol=Rol(codigo=rol, permisos=list(permisos)),
            empresa_id=empresa_id,
        )
    )


@pytest.mark.asyncio
async def test_cambio_de_empresa_con_revocacion_fallida_no_deja_la_sesion_vigente(db):
    emp_a, emp_b = await sembrar(db)
    rep = await nuevo_usuario(db, "qa.rep@prueba.local", "representante", PERMISOS_REPRESENTANTE, emp_a.id)
    sesiones = RepositorioMongoSesion(db)
    token = await sesiones.crear(rep)
    assert await sesiones.obtener_sesion_por_token(token) is not None

    editar = EditarUsuario(RepositorioMongoUsuario(db), RepositorioMongoEmpresa(db), RevocacionQueFalla(db))
    with pytest.raises(RuntimeError):
        await editar.ejecutar(rep.id, empresa_id=emp_b.id)

    # el usuario quedó en la empresa B y la revocación no se hizo...
    assert (await RepositorioMongoUsuario(db).obtener_por_id(rep.id)).empresa_id == emp_b.id
    # ...pero la sesión de la empresa A ya no se acepta y se elimina
    assert await sesiones.obtener_sesion_por_token(token) is None
    assert await db["sesiones"].count_documents({"usuario_id": rep.id}) == 0
    # una sesión nueva, con la empresa B, sí es válida
    actual = await RepositorioMongoUsuario(db).obtener_por_id(rep.id)
    nuevo = await sesiones.crear(actual)
    sesion = await sesiones.obtener_sesion_por_token(nuevo)
    assert sesion is not None and sesion["empresa_id"] == emp_b.id


@pytest.mark.asyncio
async def test_cambio_de_rol_con_revocacion_fallida_no_deja_la_sesion_vigente(db):
    await sembrar(db)
    usuario = await nuevo_usuario(db, "qa.c@prueba.local", "consultor", PERMISOS_CONSULTOR)
    sesiones = RepositorioMongoSesion(db)
    token = await sesiones.crear(usuario)

    editar = EditarUsuario(RepositorioMongoUsuario(db), RepositorioMongoEmpresa(db), RevocacionQueFalla(db))
    with pytest.raises(RuntimeError):
        await editar.ejecutar(usuario.id, rol_codigo="administrador")

    assert await sesiones.obtener_sesion_por_token(token) is None


@pytest.mark.asyncio
async def test_desactivar_usuario_con_revocacion_fallida_bloquea_la_sesion(db):
    await sembrar(db)
    usuario = await nuevo_usuario(db, "qa.d@prueba.local", "consultor", PERMISOS_CONSULTOR)
    sesiones = RepositorioMongoSesion(db)
    token = await sesiones.crear(usuario)

    with pytest.raises(RuntimeError):
        await DesactivarUsuario(RepositorioMongoUsuario(db), RevocacionQueFalla(db)).ejecutar(usuario.id)

    assert await sesiones.obtener_usuario_id_por_token(token) is None


@pytest.mark.asyncio
async def test_desactivar_la_empresa_cierra_la_sesion_de_su_representante(db):
    """DesactivarEmpresa no revoca sesiones; la revalidación lo cubre."""
    emp_a, _ = await sembrar(db)
    rep = await nuevo_usuario(db, "qa.rep2@prueba.local", "representante", PERMISOS_REPRESENTANTE, emp_a.id)
    sesiones = RepositorioMongoSesion(db)
    token = await sesiones.crear(rep)

    await DesactivarEmpresa(RepositorioMongoEmpresa(db)).ejecutar(emp_a.id)

    assert await sesiones.obtener_sesion_por_token(token) is None


@pytest.mark.asyncio
async def test_quitar_permiso_con_fallo_a_mitad_de_la_sincronizacion(db):
    """El rol se actualiza y la sincronización se cae en el primer usuario:
    las sesiones de todos los consultores dejan de valer de inmediato, y
    repetir la operación completa la sincronización (idempotente)."""
    await sembrar(db)
    c1 = await nuevo_usuario(db, "qa.c1@prueba.local", "consultor", PERMISOS_CONSULTOR)
    c2 = await nuevo_usuario(db, "qa.c2@prueba.local", "consultor", PERMISOS_CONSULTOR)
    sesiones = RepositorioMongoSesion(db)
    t1, t2 = await sesiones.crear(c1), await sesiones.crear(c2)

    quitar = QuitarPermisoDeRol(RepositorioMongoRol(db), RepositorioMongoUsuario(db), RevocacionQueFalla(db))
    with pytest.raises(RuntimeError):
        await quitar.ejecutar("consultor", "recomendaciones.registrar")

    assert await sesiones.obtener_sesion_por_token(t1) is None
    assert await sesiones.obtener_sesion_por_token(t2) is None

    reintento = QuitarPermisoDeRol(RepositorioMongoRol(db), RepositorioMongoUsuario(db), sesiones)
    await reintento.ejecutar("consultor", "recomendaciones.registrar")
    for u in (c1, c2):
        actual = await RepositorioMongoUsuario(db).obtener_por_id(u.id)
        assert actual.rol.permisos == ["diagnosticos.consultar"]


@pytest.mark.asyncio
async def test_inicio_de_sesion_concurrente_con_el_cambio_de_rol(db):
    """Carrera: el inicio de sesión leyó al usuario con el rol anterior y crea
    la sesión después de que el administrador lo cambió y revocó. Antes, esa
    sesión quedaba vigente hasta vencer; ahora se rechaza en su primer uso."""
    await sembrar(db)
    usuario = await nuevo_usuario(db, "qa.carrera@prueba.local", "consultor", PERMISOS_CONSULTOR)
    leido_por_el_login = await RepositorioMongoUsuario(db).obtener_por_id(usuario.id)
    sesiones = RepositorioMongoSesion(db)

    await EditarUsuario(RepositorioMongoUsuario(db), RepositorioMongoEmpresa(db), sesiones).ejecutar(
        usuario.id, rol_codigo="administrador"
    )
    token_tardio = await sesiones.crear(leido_por_el_login)

    assert await sesiones.obtener_sesion_por_token(token_tardio) is None


@pytest.mark.asyncio
async def test_peticiones_simultaneas_durante_la_desactivacion(db):
    """Tras terminar la desactivación, ninguna petición posterior pasa."""
    await sembrar(db)
    usuario = await nuevo_usuario(db, "qa.conc@prueba.local", "consultor", PERMISOS_CONSULTOR)
    sesiones = RepositorioMongoSesion(db)
    token = await sesiones.crear(usuario)

    async def peticiones(n):
        return [await sesiones.obtener_usuario_id_por_token(token) for _ in range(n)]

    await asyncio.gather(
        peticiones(20),
        DesactivarUsuario(RepositorioMongoUsuario(db), sesiones).ejecutar(usuario.id),
    )
    posteriores = await asyncio.gather(*[sesiones.obtener_usuario_id_por_token(token) for _ in range(20)])
    assert all(r is None for r in posteriores)


@pytest.mark.asyncio
async def test_sesion_creada_antes_de_la_revalidacion_se_descarta_una_vez(db):
    await sembrar(db)
    usuario = await nuevo_usuario(db, "qa.vieja@prueba.local", "consultor", PERMISOS_CONSULTOR)
    sesiones = RepositorioMongoSesion(db)
    token = await sesiones.crear(usuario)
    await db["sesiones"].update_one({"usuario_id": usuario.id}, {"$unset": {"empresa_id": ""}})

    assert await sesiones.obtener_sesion_por_token(token) is None
    assert await sesiones.obtener_sesion_por_token(await sesiones.crear(usuario)) is not None


# ---------------- invitaciones ----------------


async def invitacion_de_solicitud(db, emp_id, correo="qa.nuevo@prueba.local"):
    solicitud = SolicitudAcceso(
        id=None, nombre_empresa="QA Empresa A", correo_solicitante=correo, nombre_solicitante="QA Nuevo"
    )
    solicitud.aprobar(empresa_id=emp_id)
    solicitud = await RepositorioMongoSolicitud(db).guardar(solicitud)
    codigo = TokenVerificacion.generar_codigo()
    await RepositorioMongoToken(db).guardar(
        TokenVerificacion(id=None, tipo=TipoToken.INVITACION, correo_destino=correo, solicitud_id=solicitud.id),
        codigo,
    )
    return codigo


def completar(db, repo_usuario=None):
    return CompletarRegistro(
        RepositorioMongoToken(db), repo_usuario or RepositorioMongoUsuario(db), RepositorioMongoSolicitud(db)
    )


@pytest.mark.asyncio
async def test_dos_envios_simultaneos_de_la_misma_invitacion_crean_una_sola_cuenta(db):
    emp_a, _ = await sembrar(db)
    codigo = await invitacion_de_solicitud(db, emp_a.id)

    resultados = await asyncio.gather(
        *[completar(db).ejecutar(codigo, "ClaveSegura!2026", "QA", "Nuevo", True) for _ in range(5)],
        return_exceptions=True,
    )

    exitos = [r for r in resultados if isinstance(r, Usuario)]
    rechazos = [r for r in resultados if isinstance(r, TokenInvalido)]
    assert len(exitos) == 1 and len(rechazos) == 4
    assert await db["usuarios"].count_documents({"correo": "qa.nuevo@prueba.local"}) == 1


@pytest.mark.asyncio
async def test_el_enlace_deja_de_valer_antes_de_que_exista_la_cuenta(db):
    """Mientras se crea la cuenta, el mismo enlace ya no sirve."""
    emp_a, _ = await sembrar(db)
    codigo = await invitacion_de_solicitud(db, emp_a.id)
    observado = {}

    class UsuarioQueObserva(RepositorioMongoUsuario):
        async def guardar(self, usuario):
            observado["token_vigente"] = (
                await RepositorioMongoToken(db).obtener_por_codigo(codigo)
            ).esta_vigente()
            return await super().guardar(usuario)

    await completar(db, UsuarioQueObserva(db)).ejecutar(codigo, "ClaveSegura!2026", "QA", "Nuevo", True)
    assert observado["token_vigente"] is False


@pytest.mark.asyncio
async def test_fallo_al_crear_la_cuenta_libera_la_invitacion_para_reintentar(db):
    emp_a, _ = await sembrar(db)
    codigo = await invitacion_de_solicitud(db, emp_a.id)

    class CaidaAlGuardar(RepositorioMongoUsuario):
        async def guardar(self, usuario):
            raise RuntimeError("fallo simulado al crear la cuenta")

    with pytest.raises(RuntimeError):
        await completar(db, CaidaAlGuardar(db)).ejecutar(codigo, "ClaveSegura!2026", "QA", "Nuevo", True)
    assert (await RepositorioMongoToken(db).obtener_por_codigo(codigo)).esta_vigente()

    usuario = await completar(db).ejecutar(codigo, "ClaveSegura!2026", "QA", "Nuevo", True)
    assert usuario.id is not None
    assert not (await RepositorioMongoToken(db).obtener_por_codigo(codigo)).esta_vigente()


@pytest.mark.asyncio
async def test_liberar_la_invitacion_es_idempotente_y_no_pisa_un_consumo_posterior(db):
    emp_a, _ = await sembrar(db)
    codigo = await invitacion_de_solicitud(db, emp_a.id)
    tokens = RepositorioMongoToken(db)

    primero = await tokens.consumir(codigo, TipoToken.INVITACION)
    copia = TokenVerificacion(**{**primero.__dict__})
    await tokens.liberar(primero)
    await tokens.liberar(primero)  # repetir no cambia nada
    segundo = await tokens.consumir(codigo, TipoToken.INVITACION)
    assert segundo is not None
    await tokens.liberar(copia)  # la compensación tardía del primer consumo
    assert not (await tokens.obtener_por_codigo(codigo)).esta_vigente()
