"""
PDF report generator for smart contract audit results.
Uses reportlab for PDF generation.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

SEV_ORDER = ["critical", "high", "medium", "low", "info"]
SEV_COLORS = {
    "critical": (0.80, 0.10, 0.10),
    "high":     (0.90, 0.40, 0.10),
    "medium":   (0.95, 0.75, 0.10),
    "low":      (0.20, 0.50, 0.80),
    "info":     (0.55, 0.55, 0.55),
}
VERDICT_COLORS = {
    "trusted":    (0.10, 0.65, 0.30),
    "warning":    (0.90, 0.65, 0.10),
    "suspicious": (0.80, 0.10, 0.10),
}


def _color(name: str, fallback=(0.3, 0.3, 0.3)):
    return SEV_COLORS.get(name, fallback)


def generate_pdf_report(
    contract_name: str,
    address: str,
    network: str,
    verdict: str,
    risk_score: int,
    analyst: str,
    summary: str,
    findings: list[dict[str, Any]],
    tools_used: str = "",
    date: str | None = None,
) -> bytes:
    """Return PDF report as bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Audit Report — {contract_name}",
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 9
    normal.leading = 13

    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=4, spaceBefore=10)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10, spaceAfter=2, spaceBefore=6)
    caption = ParagraphStyle("Cap", parent=normal, fontSize=8, textColor=colors.grey)
    mono = ParagraphStyle("Mono", parent=normal, fontName="Courier", fontSize=8, leading=11)

    date_str = date or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    vc = VERDICT_COLORS.get(verdict, (0.3, 0.3, 0.3))
    verdict_color = colors.Color(*vc)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Smart Contract Audit Report", h1))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2c3e50")))
    story.append(Spacer(1, 0.3*cm))

    meta = [
        ["Контракт",   contract_name,  "Сеть",      network],
        ["Адрес",      address,        "Аналитик",  analyst],
        ["Дата",       date_str,       "Инструменты", tools_used or "—"],
    ]
    meta_table = Table(meta, colWidths=[3*cm, 7.5*cm, 3*cm, 4.5*cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 0), (0, -1), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",   (2, 0), (2, -1), colors.HexColor("#2c3e50")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Verdict banner ────────────────────────────────────────────────────────
    verdict_label = {"trusted": "TRUSTED", "warning": "WARNING", "suspicious": "SUSPICIOUS"}.get(verdict, verdict.upper())
    banner = Table(
        [[
            Paragraph(f"<b>Вердикт: {verdict_label}</b>", ParagraphStyle(
                "V", fontName="Helvetica-Bold", fontSize=14,
                textColor=colors.white, alignment=TA_CENTER,
            )),
            Paragraph(f"<b>Risk Score: {risk_score}/100</b>", ParagraphStyle(
                "RS", fontName="Helvetica-Bold", fontSize=14,
                textColor=colors.white, alignment=TA_CENTER,
            )),
        ]],
        colWidths=[9*cm, 9*cm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), verdict_color),
        ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#2c3e50")),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.4*cm))

    # ── Summary ───────────────────────────────────────────────────────────────
    if summary:
        story.append(Paragraph("Резюме", h2))
        story.append(Paragraph(summary, normal))
        story.append(Spacer(1, 0.3*cm))

    # ── Severity breakdown ────────────────────────────────────────────────────
    story.append(Paragraph("Статистика находок", h2))
    counts = {}
    for f in findings:
        sev = f.get("severity_label") or f.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1

    sev_data = [["Severity", "Кол-во"]]
    for sev in SEV_ORDER:
        if counts.get(sev, 0):
            sev_data.append([sev.capitalize(), str(counts[sev])])
    sev_data.append(["Итого", str(len(findings))])

    sev_table = Table(sev_data, colWidths=[5*cm, 3*cm])
    sev_style = [
        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",  (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 9),
        ("GRID",      (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("ALIGN",     (1, 0), (1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]
    for row_i, sev in enumerate([s for s in SEV_ORDER if counts.get(s, 0)], 1):
        r, g, b = SEV_COLORS.get(sev, (0.5, 0.5, 0.5))
        sev_style.append(("TEXTCOLOR", (0, row_i), (0, row_i), colors.Color(r, g, b)))
        sev_style.append(("FONTNAME",  (0, row_i), (0, row_i), "Helvetica-Bold"))
    sev_table.setStyle(TableStyle(sev_style))
    story.append(sev_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Findings ──────────────────────────────────────────────────────────────
    if findings:
        story.append(Paragraph("Детальные находки", h2))

        for idx, f in enumerate(findings, 1):
            sev  = f.get("severity_label") or f.get("severity", "info")
            tool = f.get("tool", "—")
            rid  = f.get("rule_id", "—")
            title = f.get("title") or rid
            desc  = f.get("description", "")
            rec   = f.get("recommendation", "")
            fp    = f.get("file_path", "")
            ls    = f.get("line_start")
            le    = f.get("line_end")

            r, g, b = SEV_COLORS.get(sev, (0.5, 0.5, 0.5))
            sev_color = colors.Color(r, g, b)

            loc = ""
            if fp:
                loc = fp
                if ls:
                    loc += f":{ls}" + (f"–{le}" if le and le != ls else "")

            header_data = [[
                Paragraph(f"<b>#{idx} {title}</b>", ParagraphStyle(
                    "FH", fontName="Helvetica-Bold", fontSize=9,
                )),
                Paragraph(f"<b>{sev.upper()}</b>", ParagraphStyle(
                    "FS", fontName="Helvetica-Bold", fontSize=9,
                    textColor=sev_color, alignment=TA_CENTER,
                )),
                Paragraph(f"{tool} · {rid}", ParagraphStyle(
                    "FT", fontName="Helvetica", fontSize=8,
                    textColor=colors.grey,
                )),
            ]]
            header_table = Table(header_data, colWidths=[8*cm, 3*cm, 7*cm])
            header_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#f4f6f8")),
                ("TOPPADDING",  (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("LINEBELOW",   (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]))

            block = [header_table]
            if loc:
                block.append(Paragraph(f"<i>Файл: {loc}</i>", caption))
            if desc:
                block.append(Paragraph(desc, normal))
            if rec:
                block.append(Paragraph(f"<b>Рекомендация:</b> {rec}", normal))
            block.append(Spacer(1, 0.2*cm))

            story.append(KeepTogether(block))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        f"Отчёт сгенерирован автоматически · Smart Contract Audit Studio · {date_str}",
        ParagraphStyle("Footer", parent=caption, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buf.getvalue()
