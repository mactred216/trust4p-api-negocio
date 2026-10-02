from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.consultar_evolucion import \
    ConsultarEvolucionDiagnosticos
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.entidades.usuario import Rol, Usuario


def crear_usuario_prueba() -> Usuario:
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id="emp-1",
    )


def crear_diagnostico_con_resultado(
    consecutivo: int,
    indice_global: Decimal,
    puntaje_innovacion: Decimal,
    modelo_version: str = "1",
    estado: str = "evaluado",
) -> Diagnostico:
    diagnostico = Diagnostico(
        id=f"diag-{consecutivo}",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version=modelo_version,
        consecutivo=consecutivo,
        estado="completado",
        porcentaje_avance=100,
    )
    diagnostico.registrar_resultado_calculado(
        ResultadoDiagnostico(
            indice_global=indice_global,
            nivel=2,
            nivel_descripcion="...",
            dimensiones=[
                DimensionResultado(codigo="innovacion", puntaje=puntaje_innovacion)
            ],
            perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
        )
    )
    if estado == "evaluado":
        diagnostico.marcar_evaluado(
            perfil_cultura_descripcion="...",
            dimensiones_observaciones={},
            lienzo_negocio={},
            sintesis="...",
            recomendaciones=[],
        )
    elif estado == "fallido":
        diagnostico.marcar_fallido("El servicio del agente no respondió")
    return diagnostico


def crear_diagnostico_sin_resultado(consecutivo: int) -> Diagnostico:
    return Diagnostico(
        id=f"diag-sin-resultado-{consecutivo}",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=consecutivo,
        estado="borrador",
    )


@pytest.mark.asyncio
async def test_evolucion_con_dos_diagnosticos_calcula_variacion():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [
        crear_diagnostico_con_resultado(1, Decimal("6.0"), Decimal("5")),
        crear_diagnostico_con_resultado(2, Decimal("8.0"), Decimal("9")),
    ]
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)
    evolucion = await caso_uso.ejecutar("user-1")

    assert len(evolucion.historial) == 2
    assert evolucion.comparacion is not None
    assert evolucion.comparacion.variacion_indice_global == Decimal("2.0")
    assert evolucion.comparacion.variaciones_por_dimension[0].variacion == Decimal("4")
    assert evolucion.comparacion.versiones_equivalentes is True
    assert evolucion.comparacion.advertencia is None


@pytest.mark.asyncio
async def test_evolucion_advierte_si_las_versiones_difieren():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [
        crear_diagnostico_con_resultado(
            1, Decimal("6.0"), Decimal("5"), modelo_version="1"
        ),
        crear_diagnostico_con_resultado(
            2, Decimal("8.0"), Decimal("9"), modelo_version="2"
        ),
    ]
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)
    evolucion = await caso_uso.ejecutar("user-1")

    assert evolucion.comparacion.versiones_equivalentes is False
    assert evolucion.comparacion.advertencia is not None


@pytest.mark.asyncio
async def test_evolucion_incluye_diagnosticos_fallidos_por_asr_02():
    """ASR-02: un diagnóstico 'fallido' conserva su índice determinístico,
    así que sigue siendo un punto de comparación válido."""
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [
        crear_diagnostico_con_resultado(
            1, Decimal("6.0"), Decimal("5"), estado="evaluado"
        ),
        crear_diagnostico_con_resultado(
            2, Decimal("7.0"), Decimal("6"), estado="fallido"
        ),
    ]
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)
    evolucion = await caso_uso.ejecutar("user-1")

    assert len(evolucion.historial) == 2
    assert evolucion.comparacion.indice_global_actual == Decimal("7.0")


@pytest.mark.asyncio
async def test_evolucion_con_un_solo_diagnostico_no_compara():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [
        crear_diagnostico_con_resultado(1, Decimal("6.0"), Decimal("5")),
    ]
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)
    evolucion = await caso_uso.ejecutar("user-1")

    assert len(evolucion.historial) == 1
    assert evolucion.comparacion is None


@pytest.mark.asyncio
async def test_evolucion_ignora_diagnosticos_sin_resultado():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.listar_por_empresa.return_value = [
        crear_diagnostico_con_resultado(1, Decimal("6.0"), Decimal("5")),
        crear_diagnostico_sin_resultado(2),
    ]
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)
    evolucion = await caso_uso.ejecutar("user-1")

    assert len(evolucion.historial) == 1
    assert evolucion.comparacion is None


@pytest.mark.asyncio
async def test_evolucion_sin_empresa_asociada_falla():
    repo_diagnostico = AsyncMock()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = None

    caso_uso = ConsultarEvolucionDiagnosticos(repo_diagnostico, repo_usuario)
    with pytest.raises(ValueError):
        await caso_uso.ejecutar("user-sin-empresa")
