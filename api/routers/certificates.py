"""Certificate generation and verification endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import io

from ..database import get_db
from ..models.models import Certificate, Candidate, Result
from ..services.certificate_generator import (
    generate_certificate_pdf,
    generate_certificate_number,
    get_performance_label,
    TEST_LABELS,
)

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CertificateOut(BaseModel):
    id: str
    certificate_number: str
    candidate_name: str
    test_key: str
    test_label: str
    score_percentage: float
    performance_label: str
    issued_at: datetime
    pdf_url: str | None = None

    class Config:
        from_attributes = True


class VerifyResponse(BaseModel):
    valid: bool
    certificate_number: str
    candidate_name: str | None = None
    test_label: str | None = None
    score_percentage: float | None = None
    performance_label: str | None = None
    issued_at: datetime | None = None


# ─── Public: Verify a certificate ────────────────────────────────────────────

@router.get("/verify/{certificate_number}", response_model=VerifyResponse)
async def verify_certificate(
    certificate_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — verify a certificate by its number."""
    result = await db.execute(
        select(Certificate).where(Certificate.certificate_number == certificate_number)
    )
    cert = result.scalar_one_or_none()

    if not cert:
        return VerifyResponse(valid=False, certificate_number=certificate_number)

    return VerifyResponse(
        valid=True,
        certificate_number=cert.certificate_number,
        candidate_name=cert.candidate_name,
        test_label=cert.test_label,
        score_percentage=cert.score_percentage,
        performance_label=cert.performance_label,
        issued_at=cert.issued_at,
    )


# ─── Generate a certificate for a candidate + test ──────────────────────────

@router.post("/generate/{candidate_id}/{test_key}")
async def generate_certificate(
    candidate_id: str,
    test_key: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a certificate PDF if the candidate scored >= 60% on the given test.
    Returns the PDF as a downloadable file.
    """
    # Look up the candidate
    cand_result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = cand_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Look up the result
    res_result = await db.execute(
        select(Result).where(Result.candidate_id == candidate_id)
    )
    result_row = res_result.scalar_one_or_none()
    if not result_row:
        raise HTTPException(status_code=404, detail="No results found for this candidate")

    # Extract the score for the specific test
    scores = result_row.scores_by_test or {}
    test_score = scores.get(test_key)
    if not test_score:
        raise HTTPException(status_code=404, detail=f"No score found for test '{test_key}'")

    score_pct = float(test_score.get("pct", 0))
    if score_pct < 60:
        raise HTTPException(
            status_code=400,
            detail=f"Score {score_pct:.0f}% is below the 60% threshold required for certification"
        )

    # Check if certificate already exists
    existing = await db.execute(
        select(Certificate).where(
            Certificate.candidate_id == candidate_id,
            Certificate.test_key == test_key,
        )
    )
    existing_cert = existing.scalar_one_or_none()

    if existing_cert:
        # Re-generate and return the PDF
        pdf_bytes = generate_certificate_pdf(
            candidate_name=existing_cert.candidate_name,
            test_key=existing_cert.test_key,
            score_percentage=existing_cert.score_percentage,
            certificate_number=existing_cert.certificate_number,
            issued_at=existing_cert.issued_at,
        )
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="TalentCheck_{existing_cert.certificate_number}.pdf"'
            },
        )

    # Generate new certificate
    cert_number = generate_certificate_number()
    test_label = TEST_LABELS.get(test_key, test_key.replace("_", " ").title())
    performance_label = get_performance_label(score_pct)

    cert = Certificate(
        candidate_id=candidate_id,
        result_id=result_row.id,
        test_key=test_key,
        certificate_number=cert_number,
        candidate_name=candidate.full_name,
        test_label=test_label,
        score_percentage=score_pct,
        performance_label=performance_label,
    )
    db.add(cert)
    await db.flush()

    # Generate the PDF
    pdf_bytes = generate_certificate_pdf(
        candidate_name=candidate.full_name,
        test_key=test_key,
        score_percentage=score_pct,
        certificate_number=cert_number,
        issued_at=cert.issued_at,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="TalentCheck_{cert_number}.pdf"'
        },
    )


# ─── List all certificates for a candidate ───────────────────────────────────

@router.get("/{candidate_id}", response_model=list[CertificateOut])
async def list_certificates(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all certificates issued to a candidate."""
    result = await db.execute(
        select(Certificate).where(Certificate.candidate_id == candidate_id)
        .order_by(Certificate.issued_at.desc())
    )
    certs = result.scalars().all()
    return certs
