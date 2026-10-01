import io

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from src.dominio.entidades.diagnostico import Diagnostico


def generar_informe_pdf(diagnostico: Diagnostico) -> bytes:
    """RF-17 (HU-018): informe con los datos de la empresa, el nivel de
    madurez, el puntaje por dimensión, el perfil de cultura, el modelo de
    negocio en lienzo y las recomendaciones. Requiere que el diagnóstico ya
    tenga un resultado evaluado (el llamador valida esta precondición)."""
    resultado = diagnostico.resultado
    estilos = getSampleStyleSheet()
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=letter)
    cuerpo: list = []

    cuerpo.append(
        Paragraph(
            f"Informe de diagnóstico — {diagnostico.empresa_nombre}", estilos["Title"]
        )
    )
    cuerpo.append(
        Paragraph(
            f"Diagnóstico N.° {diagnostico.consecutivo} · Versión del modelo "
            f"{diagnostico.modelo_version} · Generado el "
            f"{resultado.generado_en.strftime('%Y-%m-%d %H:%M UTC')}",
            estilos["Normal"],
        )
    )
    cuerpo.append(Spacer(1, 16))

    cuerpo.append(Paragraph("Nivel de madurez", estilos["Heading2"]))
    cuerpo.append(
        Paragraph(
            f"Nivel {resultado.nivel} — índice global {resultado.indice_global}",
            estilos["Normal"],
        )
    )
    cuerpo.append(Paragraph(resultado.nivel_descripcion, estilos["Normal"]))
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Puntaje por dimensión", estilos["Heading2"]))
    filas = [["Dimensión", "Puntaje", "Observación"]]
    for dimension in resultado.dimensiones:
        filas.append(
            [dimension.codigo, str(dimension.puntaje), dimension.observacion or "—"]
        )
    tabla = Table(filas, hAlign="LEFT")
    tabla.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, "#999999"),
                ("BACKGROUND", (0, 0), (-1, 0), "#eeeeee"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    cuerpo.append(tabla)
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Perfil de cultura de innovación", estilos["Heading2"]))
    cuerpo.append(
        Paragraph(f"Código: {resultado.perfil_cultura.codigo}", estilos["Normal"])
    )
    cuerpo.append(
        Paragraph(resultado.perfil_cultura.descripcion or "—", estilos["Normal"])
    )
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Modelo de negocio (lienzo)", estilos["Heading2"]))
    for bloque, texto in (resultado.lienzo_negocio or {}).items():
        cuerpo.append(
            Paragraph(f"<b>{bloque.replace('_', ' ')}:</b> {texto}", estilos["Normal"])
        )
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Síntesis", estilos["Heading2"]))
    cuerpo.append(Paragraph(resultado.sintesis or "—", estilos["Normal"]))
    cuerpo.append(Spacer(1, 12))

    cuerpo.append(Paragraph("Recomendaciones", estilos["Heading2"]))
    recomendaciones_visibles = [r for r in diagnostico.recomendaciones if r.visible]
    if not recomendaciones_visibles:
        cuerpo.append(Paragraph("Sin recomendaciones registradas.", estilos["Normal"]))
    for recomendacion in recomendaciones_visibles:
        origen = (
            "Generada por el agente"
            if recomendacion.origen == "agente"
            else "Registrada por el consultor"
        )
        cuerpo.append(
            Paragraph(f"<b>{recomendacion.titulo}</b> — {origen}", estilos["Normal"])
        )
        cuerpo.append(Paragraph(recomendacion.contenido, estilos["Normal"]))
        cuerpo.append(Spacer(1, 6))

    documento.build(cuerpo)
    return buffer.getvalue()
