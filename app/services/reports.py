"""Relatório PDF de um diagnóstico salvo (ReportLab).

Recebe o dicionário de scanner.get_diagnostic(), ou seja, o que foi salvo na varredura.
"""

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.rules import format_value

SIMULATION_NOTICE = "SIMULAÇÃO DIDÁTICA: não representa leitura de um veículo real"
LEVEL_COLORS = {"ok": "#15803D", "info": "#0369A1", "warn": "#B45309", "crit": "#B91C1C"}
STATUS_TEXT = {"normal": "Normal", "warn": "Atenção", "crit": "Crítico", "invalid": "Sem leitura"}

_base = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle("title", parent=_base["Title"], fontSize=20, spaceAfter=2),
    "subtitle": ParagraphStyle("subtitle", parent=_base["Normal"], alignment=TA_CENTER, textColor=colors.HexColor("#4B5563")),
    "h2": ParagraphStyle("h2", parent=_base["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=4),
    "h3": ParagraphStyle("h3", parent=_base["Heading3"], fontSize=11, spaceBefore=6, spaceAfter=2),
    "body": ParagraphStyle("body", parent=_base["Normal"], fontSize=9.5, leading=13),
    "small": ParagraphStyle("small", parent=_base["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#4B5563")),
    "bullet": ParagraphStyle("bullet", parent=_base["Normal"], fontSize=9.5, leading=12.5, leftIndent=10, bulletIndent=2),
    "notice": ParagraphStyle("notice", parent=_base["Normal"], fontSize=11, leading=14, alignment=TA_CENTER,
                             textColor=colors.HexColor("#991B1B"), fontName="Helvetica-Bold"),
}
GRID = colors.HexColor("#D1D5DB")
HEADER_BG = colors.HexColor("#E5E7EB")


def _p(text, style="body") -> Paragraph:
    return Paragraph(escape(str(text)), STYLES[style])


def _bullets(items) -> list:
    return [Paragraph(escape(i), STYLES["bullet"], bulletText="•") for i in items]


def _when(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y %H:%M:%S")


def _table(rows, widths, header=True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.5, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), HEADER_BG))
    table.setStyle(TableStyle(style))
    return table


def _header_footer(diagnostic_id: int):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#4B5563"))
        width, height = A4
        canvas.drawString(doc.leftMargin, height - 12 * mm, f"AutoScan Pro · Relatório do diagnóstico nº {diagnostic_id}")
        canvas.drawString(doc.leftMargin, 10 * mm, SIMULATION_NOTICE)
        canvas.drawRightString(width - doc.rightMargin, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()
    return draw


def build_pdf(d: dict) -> bytes:
    v = d["vehicle"]
    content_width = A4[0] - 36 * mm
    story = [
        _p("AutoScan Pro", "title"),
        _p("Relatório de diagnóstico automotivo simulado", "subtitle"),
        Spacer(1, 6 * mm),
    ]

    notice = Table([[_p(SIMULATION_NOTICE, "notice")]], colWidths=[content_width])
    notice.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#DC2626")),
                                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
                                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [notice, Spacer(1, 5 * mm)]

    status = f'<font color="{LEVEL_COLORS.get(d["status"], "#000000")}"><b>{escape(d["status_label"])}</b></font>'
    ident = [
        [_p("Diagnóstico nº"), _p(d["diagnostic_id"])],
        [_p("Data e hora"), _p(_when(d["completed_at"]))],
        [_p("Veículo"), _p(f'{v["make"]} {v["model"]} {v["year"]}')],
        [_p("Motorização"), _p(v["engine"] or "Não informada")],
        [_p("Combustível"), _p(v["fuel_label"])],
        [_p("Quilometragem"), _p(format_value(v["mileage_km"], "km"))],
        [_p("Origem dos dados"), _p("ECU simulada do AutoScan Pro (sem conexão com veículo real)")],
        [_p("Situação"), Paragraph(status, STYLES["body"])],
    ]
    id_table = _table(ident, [40 * mm, content_width - 40 * mm], header=False)
    id_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), HEADER_BG)]))
    story += [id_table, _p("Resumo", "h2"), _p(d["summary"])]

    # Códigos de falha armazenados
    story.append(_p("Códigos de falha armazenados (DTC)", "h2"))
    if d["faults"]:
        rows = [[_p("Código"), _p("Descrição"), _p("Sistema")]]
        rows += [[_p(f["code"]), _p(f["description"]), _p(f["system"])] for f in d["faults"]]
        story.append(_table(rows, [22 * mm, content_width - 72 * mm, 50 * mm]))
    else:
        story.append(_p("Nenhum código de falha armazenado na ECU simulada."))
    story.append(_p(d["dtc_note"], "small"))

    # Condições observadas
    story.append(_p("Condições observadas", "h2"))
    story += _bullets([f'[{c["status_label"]}] {c["message"]}' for c in d["conditions"]]) or \
        [_p("Todos os parâmetros dentro dos limites didáticos.")]

    # Análise por regras
    story.append(_p("Análise por regras: evidências e recomendações", "h2"))
    if d["findings"]:
        story.append(_p("Hipóteses indicam o que investigar; não confirmam defeito.", "small"))
        for f in d["findings"]:
            block = [Paragraph(f'<font color="{LEVEL_COLORS[f["level"]]}">[{escape(f["level_label"])}]</font> '
                               f'{escape(f["title"])} <font size="8" color="#6B7280">(regra {escape(f["rule_id"])})</font>',
                               STYLES["h3"])]
            for title, items in (("Evidências observadas", f["evidence"]), ("Hipóteses possíveis", f["hypotheses"]),
                                 ("Verificações recomendadas", f["checks"])):
                block += [_p(title, "small"), *_bullets(items)]
            story.append(KeepTogether(block))
        story.append(Spacer(1, 2 * mm))
        story.append(_p(d["findings"][0]["disclaimer"], "small"))
    else:
        story.append(_p("Nenhuma regra disparada: não há indícios de anormalidade nesta leitura."))

    # Parâmetros lidos (título e tabela na mesma página)
    rows = [[_p("Parâmetro"), _p("Valor"), _p("Situação")]]
    for r in d["readings"]:
        value = "Sem leitura" if r["value"] is None else format_value(r["value"], r["unit"])
        rows.append([_p(r["display_name"]), _p(value), _p(STATUS_TEXT.get(r["status"], "-"))])
    story.append(KeepTogether([_p("Parâmetros lidos", "h2"), _table(rows, [content_width - 70 * mm, 40 * mm, 30 * mm]),
                               _p(d["thresholds_notice"], "small")]))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"AutoScan Pro - Diagnóstico {d['diagnostic_id']}",
                            author="AutoScan Pro (simulação didática)")
    on_page = _header_footer(d["diagnostic_id"])
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()
