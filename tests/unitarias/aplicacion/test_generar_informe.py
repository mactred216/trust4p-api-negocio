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


def _texto_del_pdf(contenido: bytes) -> str:
    import io

    from pypdf import PdfReader

    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(contenido)).pages)


def test_el_informe_muestra_nombres_de_dimension_y_dos_decimales():
    diagnostico = crear_diagnostico_evaluado()
    diagnostico.resultado.indice_global = Decimal("60.9375")
    diagnostico.resultado.dimensiones[0].puntaje = Decimal("56.25")

    texto = _texto_del_pdf(
        generar_informe_pdf(diagnostico, {"innovacion": "Capacidad de innovación"})
    )

    assert "Capacidad de innovación" in texto
    assert "60.94" in texto and "60.9375" not in texto
    assert "56.25" in texto


def test_sin_nombres_el_informe_usa_el_codigo_de_la_dimension():
    assert "innovacion" in _texto_del_pdf(generar_informe_pdf(crear_diagnostico_evaluado()))


def test_una_observacion_larga_se_parte_en_lineas_y_no_se_sale_de_la_pagina():
    import io

    from pypdf import PdfReader

    diagnostico = crear_diagnostico_evaluado()
    diagnostico.resultado.dimensiones[0].observacion = (
        "La organización cuenta con asignación explícita de recursos y "
        "seguimiento de la junta directiva sobre el portafolio de innovación, "
        "lo que es un pilar fuerte del modelo. " * 4
    )

    pdf = generar_informe_pdf(diagnostico)

    pagina = PdfReader(io.BytesIO(pdf)).pages[0]
    ancho = float(pagina.mediabox.width)
    xs = []
    pagina.extract_text(visitor_text=lambda t, cm, tm, fd, fs: xs.append(tm[4]) if t.strip() else None)
    assert max(xs) < ancho - 36, "hay texto pegado o fuera del borde derecho"


def test_el_texto_con_marcado_no_rompe_el_informe():
    diagnostico = crear_diagnostico_evaluado()
    diagnostico.resultado.sintesis = "Ventas <30% & crecimiento </b> sostenido"

    texto = _texto_del_pdf(generar_informe_pdf(diagnostico))

    assert "Ventas <30% & crecimiento </b> sostenido" in texto


@pytest.mark.asyncio
async def test_los_nombres_de_dimension_salen_de_la_version_del_modelo_evaluada():
    from types import SimpleNamespace

    from src.aplicacion.casos_uso.generar_informe import nombres_de_dimensiones

    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = SimpleNamespace(
        dimensiones=[SimpleNamespace(codigo="innovacion", nombre="Capacidad de innovación")]
    )
    diagnostico = crear_diagnostico_evaluado()

    nombres = await nombres_de_dimensiones(repo_modelo, diagnostico)

    assert nombres == {"innovacion": "Capacidad de innovación"}
    repo_modelo.obtener_por_version.assert_awaited_once_with(diagnostico.modelo_version)


@pytest.mark.asyncio
async def test_si_la_version_del_modelo_ya_no_existe_no_hay_nombres():
    from src.aplicacion.casos_uso.generar_informe import nombres_de_dimensiones

    repo_modelo = AsyncMock()
    repo_modelo.obtener_por_version.return_value = None

    assert await nombres_de_dimensiones(repo_modelo, crear_diagnostico_evaluado()) == {}
