from datetime import datetime, timezone

import pytest

from src.dominio.entidades.usuario import Rol, Usuario
from src.infraestructura.persistencia.repositorio_mongo_usuario import \
    RepositorioMongoUsuario


def crear_usuario_prueba(
    correo="integracion@trust4p.com", codigo_rol="consultor"
) -> Usuario:
    return Usuario(
        id=None,
        correo=correo,
        clave_hash="hash-de-prueba",
        nombres="Prueba",
        apellidos="Integración",
        rol=Rol(codigo=codigo_rol, permisos=["diagnosticos.consultar"]),
        historial_claves=["hash-anterior-1", "hash-anterior-2"],
    )


@pytest.mark.asyncio
async def test_guardar_y_obtener_por_correo_conserva_historial_claves(db):
    repo = RepositorioMongoUsuario(db)
    await repo.guardar(crear_usuario_prueba())

    recuperado = await repo.obtener_por_correo("integracion@trust4p.com")

    assert recuperado is not None
    assert recuperado.historial_claves == ["hash-anterior-1", "hash-anterior-2"]
    assert recuperado.rol.permisos == ["diagnosticos.consultar"]


@pytest.mark.asyncio
async def test_listar_por_rol(db):
    repo = RepositorioMongoUsuario(db)
    await repo.guardar(crear_usuario_prueba("consultor1@trust4p.com", "consultor"))
    await repo.guardar(crear_usuario_prueba("admin1@trust4p.com", "administrador"))

    consultores = await repo.listar_por_rol("consultor")

    assert len(consultores) == 1
    assert consultores[0].correo == "consultor1@trust4p.com"


@pytest.mark.asyncio
async def test_actualizar_persiste_nuevo_hash_e_historial(db):
    repo = RepositorioMongoUsuario(db)
    usuario = await repo.guardar(crear_usuario_prueba())

    usuario.registrar_clave("hash-nuevo")
    await repo.actualizar(usuario)

    recuperado = await repo.obtener_por_correo(usuario.correo)
    assert recuperado.clave_hash == "hash-nuevo"
    assert recuperado.historial_claves[0] == "hash-de-prueba"


@pytest.mark.asyncio
async def test_obtener_por_id_con_formato_invalido_devuelve_none(db):
    repo = RepositorioMongoUsuario(db)

    assert await repo.obtener_por_id("no-es-un-object-id") is None


@pytest.mark.asyncio
async def test_guardar_y_obtener_conserva_autorizacion_tratamiento_datos(db):
    """RF-43: la aceptación del tratamiento de datos se persiste con fecha y
    versión de la política, no solo se valida como compuerta efímera."""
    repo = RepositorioMongoUsuario(db)
    fecha = datetime.now(timezone.utc)
    usuario = crear_usuario_prueba("consentimiento@trust4p.com")
    usuario.acepto_tratamiento_en = fecha
    usuario.version_politica_aceptada = "1.0"
    await repo.guardar(usuario)

    recuperado = await repo.obtener_por_correo("consentimiento@trust4p.com")

    assert recuperado.version_politica_aceptada == "1.0"
    assert recuperado.acepto_tratamiento_en is not None
