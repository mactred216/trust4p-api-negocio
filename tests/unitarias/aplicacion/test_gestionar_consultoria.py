from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.gestionar_consultoria import (
    ConsultarDiagnosticoAsignado, ListarDiagnosticosDeEmpresaAsignada,
    ListarEmpresasAsignadas, RegistrarRecomendacion)
from src.aplicacion.casos_uso.gestionar_diagnostico import (
    AccesoNoAutorizado, DiagnosticoNoEncontrado)
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.entidades.empresa import Empresa, Sector
from src.dominio.entidades.usuario import Asignacion, Rol, Usuario


def crear_consultor(empresas=("emp-1",), finalizadas=()):
    asignaciones = [Asignacion(empresa_id=e) for e in empresas] + [
        Asignacion(empresa_id=e, finalizado_en=datetime.now(timezone.utc))
        for e in finalizadas
    ]
    return Usuario(
        id="consultor-1",
        correo="carlos@trust4p.com",
        clave_hash="hash",
        nombres="Carlos",
        apellidos="Gómez",
        rol=Rol(codigo="consultor"),
        asignaciones=asignaciones,
    )


def crear_representante():
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id="emp-1",
    )


def crear_diagnostico(
    id="diag-1",
    empresa_id="emp-1",
    consecutivo=1,
    estado="evaluado",
    con_resultado=True,
):
    diagnostico = Diagnostico(
        id=id,
        empresa_id=empresa_id,
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=consecutivo,
        estado="completado",
        porcentaje_avance=100,
    )
    if con_resultado:
        diagnostico.registrar_resultado_calculado(
            ResultadoDiagnostico(
                indice_global=Decimal("7"),
                nivel=2,
                nivel_descripcion="...",
                dimensiones=[
                    DimensionResultado(codigo="innovacion", puntaje=Decimal("7"))
                ],
                perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
            )
        )
    diagnostico.estado = estado
    return diagnostico


def crear_empresa(id="emp-1", nombre="InnovaTech"):
    return Empresa(
        id=id, nombre=nombre, sector=Sector(id="s", codigo="J62", nombre="SW")
    )


# ---------------- HU-020 ----------------


@pytest.mark.asyncio
async def test_listar_empresas_asignadas_muestra_estado_y_nivel():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = crear_empresa()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [
        crear_diagnostico(id="d1", consecutivo=1, estado="cerrado"),
        crear_diagnostico(id="d2", consecutivo=2, estado="evaluado"),
    ]

    caso_uso = ListarEmpresasAsignadas(repo_usuario, repo_empresa, repo_diagnostico)
    resumenes = await caso_uso.ejecutar("consultor-1")

    assert len(resumenes) == 1
    assert resumenes[0].diagnostico_id == "d2"
    assert resumenes[0].estado == "evaluado"
    assert resumenes[0].nivel == 2


@pytest.mark.asyncio
async def test_empresa_con_asignacion_finalizada_no_aparece():
    """HU-020 CA-01."""
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor(
        empresas=(), finalizadas=("emp-1",)
    )
    repo_empresa = AsyncMock()
    repo_diagnostico = AsyncMock()

    caso_uso = ListarEmpresasAsignadas(repo_usuario, repo_empresa, repo_diagnostico)

    assert await caso_uso.ejecutar("consultor-1") == []


@pytest.mark.asyncio
async def test_listar_empresas_filtra_por_estado():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = crear_empresa()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [crear_diagnostico()]

    caso_uso = ListarEmpresasAsignadas(repo_usuario, repo_empresa, repo_diagnostico)

    assert await caso_uso.ejecutar("consultor-1", estado="cerrado") == []
    assert len(await caso_uso.ejecutar("consultor-1", estado="evaluado")) == 1


@pytest.mark.asyncio
async def test_listar_empresas_filtra_por_rango_de_fechas():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = crear_empresa()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [crear_diagnostico()]

    caso_uso = ListarEmpresasAsignadas(repo_usuario, repo_empresa, repo_diagnostico)
    manana = datetime.now(timezone.utc) + timedelta(days=1)

    assert await caso_uso.ejecutar("consultor-1", fecha_desde=manana) == []
    assert (
        len(
            await caso_uso.ejecutar(
                "consultor-1", fecha_desde=manana - timedelta(days=2)
            )
        )
        == 1
    )


@pytest.mark.asyncio
async def test_empresa_sin_diagnosticos_aparece_sin_estado():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor()
    repo_empresa = AsyncMock()
    repo_empresa.obtener_por_id.return_value = crear_empresa()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = []

    caso_uso = ListarEmpresasAsignadas(repo_usuario, repo_empresa, repo_diagnostico)
    resumenes = await caso_uso.ejecutar("consultor-1")

    assert resumenes[0].estado is None
    assert resumenes[0].nivel is None


# ---------------- HU-021 ----------------


@pytest.mark.asyncio
async def test_consultar_diagnostico_de_empresa_asignada():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = crear_diagnostico()

    caso_uso = ConsultarDiagnosticoAsignado(repo_usuario, repo_diagnostico)

    assert (await caso_uso.ejecutar("consultor-1", "diag-1")).id == "diag-1"


@pytest.mark.asyncio
async def test_consultar_diagnostico_sin_asignacion_vigente_se_deniega():
    """HU-021 CA-01."""
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor(
        empresas=(), finalizadas=("emp-1",)
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = crear_diagnostico()

    caso_uso = ConsultarDiagnosticoAsignado(repo_usuario, repo_diagnostico)

    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("consultor-1", "diag-1")


@pytest.mark.asyncio
async def test_consultar_diagnostico_inexistente():
    repo_usuario = AsyncMock()
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = None

    caso_uso = ConsultarDiagnosticoAsignado(repo_usuario, repo_diagnostico)

    with pytest.raises(DiagnosticoNoEncontrado):
        await caso_uso.ejecutar("consultor-1", "no-existe")


@pytest.mark.asyncio
async def test_listar_diagnosticos_de_empresa_ajena_se_deniega():
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_consultor(empresas=("emp-1",))
    repo_diagnostico = AsyncMock()

    caso_uso = ListarDiagnosticosDeEmpresaAsignada(repo_usuario, repo_diagnostico)

    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("consultor-1", "emp-ajena")
    repo_diagnostico.listar_por_empresa.assert_not_called()


# ---------------- HU-022 ----------------


def armar_registrar(diagnostico, consultor):
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.side_effect = lambda uid: (
        consultor if uid == "consultor-1" else crear_representante()
    )
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = diagnostico
    servicio_correo = AsyncMock()
    repo_notificacion = AsyncMock()
    caso_uso = RegistrarRecomendacion(
        repo_usuario, repo_diagnostico, servicio_correo, repo_notificacion
    )
    return caso_uso, repo_diagnostico, servicio_correo, repo_notificacion


@pytest.mark.asyncio
async def test_registrar_recomendacion_persiste_con_autor_y_notifica():
    diagnostico = crear_diagnostico()
    caso_uso, repo_diagnostico, servicio_correo, repo_notificacion = armar_registrar(
        diagnostico, crear_consultor()
    )

    recomendacion = await caso_uso.ejecutar(
        "consultor-1",
        "diag-1",
        titulo="Formalizar el comité",
        contenido="Documentar actas y responsables.",
        dimension_codigo="innovacion",
    )

    assert recomendacion.origen == "consultor"
    assert recomendacion.autor_id == "consultor-1"
    assert diagnostico.recomendaciones == [recomendacion]
    repo_diagnostico.actualizar.assert_called_once_with(diagnostico)
    servicio_correo.enviar.assert_called_once()
    assert (
        servicio_correo.enviar.call_args.kwargs["destinatario"] == "ana@innovatech.com"
    )
    assert (
        repo_notificacion.registrar.call_args[0][0].tipo == "recomendacion_registrada"
    )


@pytest.mark.asyncio
async def test_recomendacion_no_visible_no_notifica():
    caso_uso, _, servicio_correo, _ = armar_registrar(
        crear_diagnostico(), crear_consultor()
    )

    await caso_uso.ejecutar(
        "consultor-1", "diag-1", titulo="Borrador", contenido="Texto", visible=False
    )

    servicio_correo.enviar.assert_not_called()


@pytest.mark.asyncio
async def test_registrar_recomendacion_en_diagnostico_cerrado_falla():
    """HU-024 CA-01."""
    caso_uso, repo_diagnostico, _, _ = armar_registrar(
        crear_diagnostico(estado="cerrado"), crear_consultor()
    )

    with pytest.raises(ValueError, match="cerrado"):
        await caso_uso.ejecutar("consultor-1", "diag-1", titulo="T", contenido="C")
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_registrar_recomendacion_sin_asignacion_se_deniega():
    caso_uso, repo_diagnostico, _, _ = armar_registrar(
        crear_diagnostico(), crear_consultor(empresas=())
    )

    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("consultor-1", "diag-1", titulo="T", contenido="C")
    repo_diagnostico.actualizar.assert_not_called()


@pytest.mark.asyncio
async def test_registrar_recomendacion_con_dimension_inexistente_falla():
    caso_uso, _, _, _ = armar_registrar(crear_diagnostico(), crear_consultor())

    with pytest.raises(ValueError, match="dimensión"):
        await caso_uso.ejecutar(
            "consultor-1", "diag-1", titulo="T", contenido="C", dimension_codigo="x"
        )
