"""
PDF Report Generator using ReportLab.
Produces a per-candidate score report with org logo.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)


BRAND_DARK = colors.HexColor("#0A0E1A")
BRAND_AMBER = colors.HexColor("#F5A623")
BRAND_TEAL = colors.HexColor("#4ECDC4")
BRAND_LIGHT = colors.HexColor("#F8F9FA")


def build_report(
    candidate_name: str,
    candidate_email: str,
    org_name: str,
    assessment_title: str,
    scores_by_test: dict,
    total_score: float,
    percentile: float | None,
    rank: int | None,
    total_candidates: int | None,
    has_flags: bool,
    scored_at: datetime,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # Header
    header_data = [
        [
            Paragraph(f'<font size="18" color="#0A0E1A"><b>TalentCheck</b></font>', styles["Normal"]),
            Paragraph(f'<font size="10" color="#666666">{org_name}</font>', styles["Normal"]),
        ]
    ]
    header_table = Table(header_data, colWidths=[10*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND_AMBER),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    # Title
    story.append(Paragraph(
        f'<font size="14" color="#0A0E1A"><b>Assessment Report</b></font>',
        styles["Normal"]
    ))
    story.append(Paragraph(
        f'<font size="11" color="#555555">{assessment_title}</font>',
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.4*cm))

    # Candidate info
    info_data = [
        ["Candidate", candidate_name],
        ["Email", candidate_email],
        ["Date", scored_at.strftime("%d %B %Y, %H:%M")],
    ]
    info_table = Table(info_data, colWidths=[4*cm, 13*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#888888")),
        ("TEXTCOLOR", (1, 0), (1, -1), BRAND_DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.6*cm))

    # Overall score banner
    overall_data = [
        [
            Paragraph(f'<font size="28" color="#0A0E1A"><b>{total_score:.1f}%</b></font>', styles["Normal"]),
            Paragraph(
                f'<font size="11" color="#555555">Overall Score</font><br/>'
                + (f'<font size="10" color="#888888">Rank #{rank} of {total_candidates} candidates | {percentile:.0f}th percentile</font>' if rank else ''),
                styles["Normal"]
            ),
        ]
    ]
    overall_table = Table(overall_data, colWidths=[5*cm, 12*cm])
    overall_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("ROUNDEDCORNERS", [6]),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(overall_table)
    story.append(Spacer(1, 0.6*cm))

    # Scores by test
    story.append(Paragraph('<font size="12" color="#0A0E1A"><b>Score Breakdown</b></font>', styles["Normal"]))
    story.append(Spacer(1, 0.3*cm))

    score_rows = [["Test", "Score", "Label", "Questions"]]
    for test_key, data in scores_by_test.items():
        score_rows.append([
            test_key.replace("_", " ").title(),
            f"{data['percentage']:.1f}%",
            data['label'],
            f"{data['raw_score']} / {data['total_questions']}",
        ])

    score_table = Table(score_rows, colWidths=[6*cm, 3*cm, 4*cm, 4*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(score_table)

    if has_flags:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            '<font size="10" color="#CC3300">⚠ Note: Proctoring flags were recorded during this session. '
            'Review the session log before making a hiring decision.</font>',
            styles["Normal"]
        ))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DDDDDD")))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        '<font size="9" color="#AAAAAA">Generated by TalentCheck Ethiopia — talentcheck.et | '
        'Hire by Skill, Not CV</font>',
        styles["Normal"]
    ))

    doc.build(story)
    return buffer.getvalue()
