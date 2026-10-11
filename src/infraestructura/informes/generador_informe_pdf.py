import io
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from src.dominio.entidades.diagnostico import Diagnostico

MARGEN = 0.9 * inch


def _dos_decimales(valor) -> str:
    return str(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _texto(valor) -> str:
    """El texto del informe llega de personas y del agente: se escapa para que
    '<', '>' o '&' no se interpreten como marcado del PDF."""
    return escape(str(valor)) if valor else "—"


def generar_informe_pdf(
    diagnostico: Diagnostico, nombres_dimension: Optional[dict[str, str]] = None
) -> bytes:
    """RF-17 (HU-018): informe con los datos de la empresa, el nivel de
    madurez, el puntaje por dimensión, el perfil de cultura, el modelo de
    negocio en lienzo y las recomendaciones. Requiere que el diagnóstico ya
    tenga un resultado evaluado (el llamador valida esta precondición).
    `nombres_dimension` traduce el código de cada dimensión a su nombre; sin él
    se muestra el código."""
    resultado = diagnostico.resultado
    nombres_dimension = nombres_dimension or {}
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle(
        "Cuerpo", parent=estilos["Normal"], leading=14, alignment=TA_LEFT
    )
    celda = ParagraphStyle("Celda", parent=normal, fontSize=9, leading=12)
    celda_encabezado = ParagraphStyle(
        "CeldaEncabezado", parent=celda, fontName="Helvetica-Bold"
    )
    titulo = ParagraphStyle(
        "TituloInforme", parent=estilos["Title"], alignment=TA_LEFT, fontSize=20
    )
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGEN,
        rightMargin=MARGEN,
        topMargin=MARGEN,
        bottomMargin=MARGEN,
        title=f"Informe de diagnóstico — {diagnostico.empresa_nombre}",
    )
    ancho_util = letter[0] - 2 * MARGEN
    cuerpo: list = []

    cuerpo.append(
        Paragraph(
            f"Informe de diagnóstico — {escape(diagnostico.empresa_nombre)}", titulo
        )
    )
    cuerpo.append(
        Paragraph(
            f"Diagnóstico N.° {diagnostico.consecutivo} · Versión del modelo "
            f"{escape(str(diagnostico.modelo_version))} · Generado el "
            f"{resultado.generado_en.strftime('%Y-%m-%d %H:%M UTC')}",
            normal,
        )
    )
    cuerpo.append(Spacer(1, 16))

    cuerpo.append(Paragraph("Nivel de madurez", estilos["Heading2"]))
    cuerpo.append(
        Paragraph(
            f"Nivel {resultado.nivel} — índice global "
            f"{_dos_decimales(resultado.indice_global)}",
            normal,
        )
    )
    cuerpo.append(Paragraph(_texto(resultado.nivel_descripcion), normal))
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Puntaje por dimensión", estilos["Heading2"]))
    filas = [
        [
            Paragraph("Dimensión", celda_encabezado),
            Paragraph("Puntaje", celda_encabezado),
            Paragraph("Observación", celda_encabezado),
        ]
    ]
    for dimension in resultado.dimensiones:
        filas.append(
            [
                Paragraph(
                    _texto(nombres_dimension.get(dimension.codigo, dimension.codigo)),
                    celda,
                ),
                Paragraph(_dos_decimales(dimension.puntaje), celda),
                Paragraph(_texto(dimension.observacion), celda),
            ]
        )
    # La observación toma el ancho restante y se parte en varias líneas.
    tabla = Table(
        filas,
        colWidths=[1.6 * inch, 0.8 * inch, ancho_util - 2.4 * inch],
        hAlign="LEFT",
        repeatRows=1,
    )
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    cuerpo.append(tabla)
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Perfil de cultura de innovación", estilos["Heading2"]))
    cuerpo.append(
        Paragraph(f"Código: {escape(str(resultado.perfil_cultura.codigo))}", normal)
    )
    cuerpo.append(Paragraph(_texto(resultado.perfil_cultura.descripcion), normal))
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Modelo de negocio (lienzo)", estilos["Heading2"]))
    for bloque, texto in (resultado.lienzo_negocio or {}).items():
        cuerpo.append(
            Paragraph(
                f"<b>{escape(bloque.replace('_', ' '))}:</b> {_texto(texto)}", normal
            )
        )
        cuerpo.append(Spacer(1, 3))
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Síntesis", estilos["Heading2"]))
    cuerpo.append(Paragraph(_texto(resultado.sintesis), normal))
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Recomendaciones", estilos["Heading2"]))
    recomendaciones_visibles = [r for r in diagnostico.recomendaciones if r.visible]
    if not recomendaciones_visibles:
        cuerpo.append(Paragraph("Sin recomendaciones registradas.", normal))
    for recomendacion in recomendaciones_visibles:
        origen = (
            "Generada por el agente"
            if recomendacion.origen == "agente"
            else "Registrada por el consultor"
        )
        cuerpo.append(
            Paragraph(f"<b>{_texto(recomendacion.titulo)}</b> — {origen}", normal)
        )
        cuerpo.append(Paragraph(_texto(recomendacion.contenido), normal))
        cuerpo.append(Spacer(1, 6))

    documento.build(cuerpo)
    return buffer.getvalue()
