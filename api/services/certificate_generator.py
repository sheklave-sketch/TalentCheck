"""
Professional PDF certificate generator for TalentCheck.
Produces branded certificates with QR verification codes.
"""

import io
import uuid
from datetime import datetime

import qrcode
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ─── Brand Colors ─────────────────────────────────────────────────────────────
NAVY = HexColor("#0A0E1A")
AMBER = HexColor("#F5A623")
AMBER_LIGHT = HexColor("#FFC857")
GOLD = HexColor("#D4A843")
DARK_GRAY = HexColor("#1A1F2E")
LIGHT_GRAY = HexColor("#E8E8E8")
WHITE = white

VERIFICATION_BASE_URL = "https://talentcheck-tau.vercel.app/verify"

# Test key → human-readable label mapping
TEST_LABELS = {
    "cognitive": "Cognitive Ability",
    "english": "English Proficiency",
    "customer_service": "Customer Service",
    "computer_skills": "Computer Skills",
    "integrity": "Integrity Assessment",
    "developer_basic": "Developer Assessment (Basic)",
}


def get_performance_label(score: float) -> str:
    """Return performance label based on score percentage."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Very Good"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    return "Needs Improvement"


def generate_certificate_number() -> str:
    """Generate unique certificate number: TC-YYYYMMDD-XXXXXX."""
    date_part = datetime.utcnow().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"TC-{date_part}-{random_part}"


def _make_qr_image(url: str) -> ImageReader:
    """Generate a QR code as an in-memory image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0E1A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_decorative_border(c: canvas.Canvas, w: float, h: float):
    """Draw a professional double-line border with corner accents."""
    # Outer border
    c.setStrokeColor(AMBER)
    c.setLineWidth(3)
    margin = 20
    c.rect(margin, margin, w - 2 * margin, h - 2 * margin)

    # Inner border
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    inner = 30
    c.rect(inner, inner, w - 2 * inner, h - 2 * inner)

    # Corner accents (small amber squares)
    accent_size = 8
    for x, y in [
        (margin - 2, margin - 2),
        (w - margin - accent_size + 2, margin - 2),
        (margin - 2, h - margin - accent_size + 2),
        (w - margin - accent_size + 2, h - margin - accent_size + 2),
    ]:
        c.setFillColor(AMBER)
        c.rect(x, y, accent_size, accent_size, fill=1, stroke=0)

    # Top decorative line
    c.setStrokeColor(AMBER)
    c.setLineWidth(2)
    line_y = h - 95
    line_margin = 80
    c.line(line_margin, line_y, w / 2 - 100, line_y)
    c.line(w / 2 + 100, line_y, w - line_margin, line_y)


def _draw_header(c: canvas.Canvas, w: float, h: float):
    """Draw the TalentCheck branding header."""
    # Logo text (since we don't have an image file, use styled text)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h - 70, "TALENTCHECK")

    c.setFillColor(LIGHT_GRAY)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 83, "E T H I O P I A")


def _draw_body(
    c: canvas.Canvas,
    w: float,
    h: float,
    candidate_name: str,
    test_label: str,
    score_pct: float,
    performance_label: str,
    issued_date: str,
    cert_number: str,
):
    """Draw the main certificate content."""
    center_x = w / 2

    # "Certificate of Achievement"
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(center_x, h - 130, "Certificate of Achievement")

    # Subtitle
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, h - 155, "This is to certify that")

    # Candidate name (large, prominent)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 36)
    name_y = h - 200
    c.drawCentredString(center_x, name_y, candidate_name)

    # Underline beneath name
    name_width = c.stringWidth(candidate_name, "Helvetica-Bold", 36)
    c.setStrokeColor(AMBER)
    c.setLineWidth(2)
    c.line(center_x - name_width / 2, name_y - 8, center_x + name_width / 2, name_y - 8)

    # "has successfully completed" text
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 12)
    c.drawCentredString(center_x, h - 230, "has successfully completed the assessment")

    # Test name and score
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(center_x, h - 265, f"{test_label} — {score_pct:.0f}%")

    # Performance badge
    badge_colors = {
        "Excellent": HexColor("#22C55E"),
        "Very Good": HexColor("#3B82F6"),
        "Good": HexColor("#F5A623"),
        "Fair": HexColor("#EF4444"),
        "Needs Improvement": HexColor("#6B7280"),
    }
    badge_color = badge_colors.get(performance_label, AMBER)

    badge_width = 140
    badge_height = 28
    badge_x = center_x - badge_width / 2
    badge_y = h - 305

    c.setFillColor(badge_color)
    c.roundRect(badge_x, badge_y, badge_width, badge_height, 14, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(center_x, badge_y + 8, performance_label)

    # Date and certificate number
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 10)
    c.drawCentredString(center_x - 150, h - 350, f"Date: {issued_date}")
    c.drawCentredString(center_x + 150, h - 350, f"Certificate No: {cert_number}")


def _draw_footer(c: canvas.Canvas, w: float, h: float, verification_url: str):
    """Draw footer with QR code and issuer info."""
    center_x = w / 2

    # QR code (bottom-right area)
    qr_img = _make_qr_image(verification_url)
    qr_size = 75
    qr_x = w - 120
    qr_y = 40
    c.drawImage(qr_img, qr_x, qr_y, qr_size, qr_size)

    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 7)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 10, "Scan to verify")

    # Issuer line
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 10)
    c.drawCentredString(center_x, 55, "Issued by TalentCheck Ethiopia")

    # Divider line above footer
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.5)
    c.line(80, 75, w - 80, 75)

    # Verification URL text
    c.setFillColor(HexColor("#6B7280"))
    c.setFont("Helvetica", 7)
    c.drawCentredString(center_x, 40, f"Verify at: {verification_url}")


def generate_certificate_pdf(
    candidate_name: str,
    test_key: str,
    score_percentage: float,
    certificate_number: str,
    issued_at: datetime | None = None,
) -> bytes:
    """
    Generate a professional PDF certificate and return as bytes.

    Args:
        candidate_name: Full name of the candidate
        test_key: Test identifier (e.g. 'cognitive')
        score_percentage: Score as percentage (0-100)
        certificate_number: Unique cert number (TC-YYYYMMDD-XXXXXX)
        issued_at: Date of issuance (defaults to now)

    Returns:
        PDF file contents as bytes
    """
    if issued_at is None:
        issued_at = datetime.utcnow()

    test_label = TEST_LABELS.get(test_key, test_key.replace("_", " ").title())
    performance_label = get_performance_label(score_percentage)
    verification_url = f"{VERIFICATION_BASE_URL}/{certificate_number}"
    issued_date = issued_at.strftime("%B %d, %Y")

    # Create PDF in landscape A4
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # White background
    c.setFillColor(WHITE)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Draw all sections
    _draw_decorative_border(c, w, h)
    _draw_header(c, w, h)
    _draw_body(c, w, h, candidate_name, test_label, score_percentage,
               performance_label, issued_date, certificate_number)
    _draw_footer(c, w, h, verification_url)

    c.save()
    buf.seek(0)
    return buf.read()
