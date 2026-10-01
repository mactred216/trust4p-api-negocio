from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.aplicacion.casos_uso.generar_informe import (
    DiagnosticoSinResultado, GenerarInformeDiagnostico)
from src.aplicacion.casos_uso.gestionar_diagnostico import AccesoNoAutorizado
from src.dominio.entidades.diagnostico import (Diagnostico, DimensionResultado,
                                               PerfilCulturaResultado,
                                               ResultadoDiagnostico)
from src.dominio.entidades.usuario import Rol, Usuario
from src.infraestructura.informes.generador_informe_pdf import \
    generar_informe_pdf


def crear_usuario_prueba(empresa_id="emp-1"):
    return Usuario(
        id="user-1",
        correo="ana@innovatech.com",
        clave_hash="hash",
        nombres="Ana",
        apellidos="Pérez",
        rol=Rol(codigo="representante"),
        empresa_id=empresa_id,
    )


def crear_diagnostico_evaluado(empresa_id="emp-1") -> Diagnostico:
    diagnostico = Diagnostico(
        id="diag-1",
        empresa_id=empresa_id,
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=1,
        estado="completado",
        porcentaje_avance=100,
    )
    diagnostico.registrar_resultado_calculado(
        ResultadoDiagnostico(
            indice_global=Decimal("8.5"),
            nivel=3,
            nivel_descripcion="Avanzado",
            dimensiones=[DimensionResultado(codigo="innovacion", puntaje=Decimal("9"))],
            perfil_cultura=PerfilCulturaResultado(codigo="ENFP"),
        )
    )
    diagnostico.marcar_evaluado(
        perfil_cultura_descripcion="Descripción del perfil",
        dimensiones_observaciones={"innovacion": "Observación"},
        lienzo_negocio={"segmentos_clientes": "..."},
        sintesis="Síntesis",
        recomendaciones=[],
    )
    return diagnostico


@pytest.mark.asyncio
async def test_generar_informe_de_diagnostico_evaluado():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = crear_diagnostico_evaluado()
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = GenerarInformeDiagnostico(repo_diagnostico, repo_usuario)
    diagnostico = await caso_uso.ejecutar("user-1", "diag-1")

    assert diagnostico.resultado is not None


@pytest.mark.asyncio
async def test_generar_informe_sin_resultado_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = Diagnostico(
        id="diag-1",
        empresa_id="emp-1",
        empresa_nombre="InnovaTech",
        usuario_id="user-1",
        modelo_version="1",
        consecutivo=1,
        estado="completado",
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba()

    caso_uso = GenerarInformeDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(DiagnosticoSinResultado):
        await caso_uso.ejecutar("user-1", "diag-1")


@pytest.mark.asyncio
async def test_generar_informe_de_otra_empresa_falla():
    repo_diagnostico = AsyncMock()
    repo_diagnostico.obtener_por_id.return_value = crear_diagnostico_evaluado(
        empresa_id="emp-otra"
    )
    repo_usuario = AsyncMock()
    repo_usuario.obtener_por_id.return_value = crear_usuario_prueba(empresa_id="emp-1")

    caso_uso = GenerarInformeDiagnostico(repo_diagnostico, repo_usuario)
    with pytest.raises(AccesoNoAutorizado):
        await caso_uso.ejecutar("user-1", "diag-1")


def test_generar_informe_pdf_produce_bytes_no_vacios():
    contenido = generar_informe_pdf(crear_diagnostico_evaluado())
    assert isinstance(contenido, bytes)
    assert contenido.startswith(b"%PDF")
    assert len(contenido) > 100
