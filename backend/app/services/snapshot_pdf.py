"""Snapshot PDF para eventos de salvamento que ainda nao tem PDF diagramado."""
from __future__ import annotations

import json
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from xml.sax.saxutils import escape


def _public_text(value, depth=0):
    if depth > 12:
        return "[objeto muito profundo]"
    if isinstance(value, dict):
        return {str(k): _public_text(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_public_text(v, depth + 1) for v in value]
    if isinstance(value, str) and (value.startswith("data:image/") or len(value) > 3000):
        return "[conteudo binario/assinatura: conferir snapshot criptografico]"
    return value


def create_snapshot_pdf(title: str, content_json: str) -> bytes:
    """PDF de auditoria legivel; o JSON completo permanece em snapshot imutavel."""
    try:
        content = json.loads(content_json)
    except (ValueError, TypeError):
        content = {"conteudo": content_json}
    data = _public_text(content)
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    lines = []
    for line in pretty.splitlines():
        # Evitar colunas enormes ou URLs de mais de uma linha.
        while len(line) > 100:
            lines.append(line[:100])
            line = "    " + line[100:]
        lines.append(line)
    # PDF nao e a fonte do JSON; nenhuma informacao e truncada no snapshot.
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallMono", fontName="Courier", fontSize=7, leading=10, textColor=colors.black))
    story = [Paragraph(escape(title), styles['Heading2']), Spacer(1, 10), Paragraph(
        "Registro automatico de alteracao. Snapshot integral autenticado armazenado no sistema.", styles['Normal']), Spacer(1, 15)]
    for i in range(0, len(lines), 55):
        story.append(Preformatted("\n".join(lines[i:i+55]), styles["SmallMono"], maxLineLength=110))
    # PDFs produzidos a partir do mesmo snapshot precisam ter bytes estaveis para retentativas idempotentes.
    def stable_canvas(*args, **kwargs):
        kwargs.pop("invariant", None)
        return canvas.Canvas(*args, invariant=1, **kwargs)

    document.build(story, canvasmaker=stable_canvas)
    return buffer.getvalue()
