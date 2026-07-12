from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

LEVEL_COLORS = {
    "none": colors.HexColor("#16a34a"),
    "low": colors.HexColor("#0d9488"),
    "moderate": colors.HexColor("#d97706"),
    "high": colors.HexColor("#dc2626"),
}


def generate_report(output_path: str, fusion_result: dict, task_id: str):
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("DeepSleuth — Forensic Analysis Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Task ID: {task_id}", styles["Normal"]))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    level = fusion_result["suspicion_level"].upper()
    level_color = LEVEL_COLORS.get(fusion_result["suspicion_level"], colors.grey)

    elements.append(Paragraph(
        f"Suspicion Level: <b><font color='{level_color}'>{level}</font></b>",
        styles["Heading2"],
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(fusion_result["summary"], styles["Normal"]))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Signal Breakdown", styles["Heading3"]))
    elements.append(Spacer(1, 8))

    table_data = [
        ["Signal", "Score", "Interpretation"],
        ["Spatial (XceptionNet)", f"{fusion_result['spatial_score']:.4f}",
         "Pixel-level manipulation artifacts"],
        ["Frequency (DCT)", f"{fusion_result['frequency_score']:.4f}",
         "Spectral inconsistencies"],
        ["Temporal (Blink + Pose)", f"{fusion_result['temporal_score']:.4f}",
         "Unnatural motion patterns"],
        ["Combined", f"{fusion_result['fused_score']:.4f}",
         ""],
    ]

    table = Table(table_data, colWidths=[160, 80, 180])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Methodology", styles["Heading3"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "This analysis applies three independent forensic signals to detect anomalies "
        "consistent with synthetic or manipulated video content. Scores range from 0.0 "
        "(no anomaly detected) to 1.0 (strong anomaly). No single signal is definitive; "
        "the combined score reflects agreement across all three streams.",
        styles["Normal"],
    ))

    doc.build(elements)
