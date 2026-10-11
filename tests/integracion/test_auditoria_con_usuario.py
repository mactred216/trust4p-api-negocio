import pytest

from src.dominio.entidades.registro_auditoria import RegistroAuditoria
from src.dominio.entidades.usuario import Rol, Usuario
from src.infraestructura.persistencia.repositorio_mongo_auditoria import \
    RepositorioMongoAuditoria
from src.infraestructura.persistencia.repositorio_mongo_usuario import \
    RepositorioMongoUsuario


def nuevo(correo, nombres, apellidos, activo=True):
    return Usuario(
        id=None,
        correo=correo,
        clave_hash="h",
        nombres=nombres,
        apellidos=apellidos,
        rol=Rol(codigo="consultor"),
        activo=activo,
    )


async def crear(repo, *usuarios):
    return [await repo.guardar(u) for u in usuarios]


@pytest.mark.asyncio
async def test_listar_por_ids_incluye_inactivos_e_ignora_ids_invalidos(db):
    repo = RepositorioMongoUsuario(db)
    ana, luis = await crear(
        repo,
        nuevo("ana@x.com", "Ana", "Pérez"),
        nuevo("luis@x.com", "Luis", "Gómez", activo=False),
    )

    encontrados = await repo.listar_por_ids([ana.id, luis.id, "no-es-un-id"])

    assert {u.correo for u in encontrados} == {"ana@x.com", "luis@x.com"}
    assert await repo.listar_por_ids([]) == []
    assert await repo.listar_por_ids(["no-es-un-id"]) == []


@pytest.mark.asyncio
async def test_buscar_por_nombre_apellido_o_correo_sin_distinguir_mayusculas(db):
    repo = RepositorioMongoUsuario(db)
    await crear(
        repo,
        nuevo("julia.herrera@x.com", "Julia", "Herrera"),
        nuevo("pedro@x.com", "Pedro", "Herrera"),
        nuevo("otra@x.com", "Otra", "Persona", activo=False),
    )

    assert {u.correo for u in await repo.buscar("JULIA")} == {"julia.herrera@x.com"}
    assert {u.correo for u in await repo.buscar("herrera")} == {"julia.herrera@x.com", "pedro@x.com"}
    assert {u.correo for u in await repo.buscar("pedro@x")} == {"pedro@x.com"}
    # varias palabras: todas deben aparecer (nombre completo)
    assert {u.correo for u in await repo.buscar("julia herrera")} == {"julia.herrera@x.com"}
    assert await repo.buscar("julia persona") == []
    # incluye a los inactivos: su historial sigue siendo consultable
    assert {u.correo for u in await repo.buscar("otra")} == {"otra@x.com"}


@pytest.mark.asyncio
async def test_buscar_trata_el_texto_como_literal_y_un_texto_vacio_no_trae_a_todos(db):
    repo = RepositorioMongoUsuario(db)
    await crear(repo, nuevo("ana@x.com", "Ana", "Pérez"))

    assert await repo.buscar(".*") == []
    assert await repo.buscar("a.a") == []
    assert await repo.buscar("   ") == []


@pytest.mark.asyncio
async def test_la_bitacora_se_filtra_por_varios_usuarios(db):
    repo = RepositorioMongoAuditoria(db)
    for i, usuario_id in enumerate(["u-1", "u-2", "u-3", None]):
        await repo.registrar(
            RegistroAuditoria(id=None, usuario_id=usuario_id, entidad="empresas", entidad_id=f"e-{i}", accion="actualizar")
        )

    dos = await repo.listar(usuario_ids=["u-1", "u-3"])
    assert {r.usuario_id for r in dos} == {"u-1", "u-3"}
    assert await repo.listar(usuario_ids=[]) == []
    assert len(await repo.listar()) == 4
    # el filtro por id y el de varios se combinan como intersección
    assert {r.usuario_id for r in await repo.listar(usuario_id="u-1", usuario_ids=["u-1", "u-3"])} == {"u-1"}
    assert await repo.listar(usuario_id="u-2", usuario_ids=["u-1", "u-3"]) == []
