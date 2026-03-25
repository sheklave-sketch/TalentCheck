"""
Candidate-facing web API endpoints.
Authenticated by telegram_id (passed from auto-login flow).
No BOT_SECRET needed — these are called from the web frontend.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.models import (
    Candidate, Assessment, Organization, Result, BotSession,
    TestSession, SessionStatus, Certificate, TelegramLink,
)

router = APIRouter()


@router.get("/profile/{telegram_id}")
async def candidate_profile(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get candidate profile from telegram_id."""
    link_result = await db.execute(
        select(TelegramLink).where(TelegramLink.telegram_id == telegram_id)
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "No account found")

    return {
        "telegram_id": telegram_id,
        "username": link.telegram_username or "",
        "linked": True,
    }


@router.get("/results/{telegram_id}")
async def candidate_results(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get all assessment results for a candidate."""
    bs_result = await db.execute(
        select(BotSession).where(BotSession.telegram_id == telegram_id)
    )
    bot_sessions = bs_result.scalars().all()

    if not bot_sessions:
        return {"results": []}

    candidate_ids = list(set(bs.candidate_id for bs in bot_sessions))
    results_list = []

    for cid in candidate_ids:
        res_result = await db.execute(
            select(Result).where(Result.candidate_id == cid)
        )
        res = res_result.scalar_one_or_none()
        if not res:
            continue

        cand_result = await db.execute(select(Candidate).where(Candidate.id == cid))
        candidate = cand_result.scalar_one()

        assessment_result = await db.execute(
            select(Assessment).where(Assessment.id == candidate.assessment_id)
        )
        assessment = assessment_result.scalar_one()

        org_result = await db.execute(
            select(Organization).where(Organization.id == assessment.org_id)
        )
        org = org_result.scalar_one()

        results_list.append({
            "candidate_id": cid,
            "candidate_name": candidate.full_name,
            "assessment_id": assessment.id,
            "assessment_title": assessment.title,
            "org_name": org.name,
            "total_score": res.total_score,
            "scores_by_test": res.scores_by_test,
            "percentile": res.percentile,
            "rank": res.rank,
            "has_flags": res.has_proctoring_flags,
            "scored_at": res.scored_at.isoformat() if res.scored_at else None,
            "passed": res.total_score >= 60.0,
        })

    return {"results": results_list}


@router.get("/certificates/{telegram_id}")
async def candidate_certificates(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get all certificates for a candidate."""
    bs_result = await db.execute(
        select(BotSession).where(BotSession.telegram_id == telegram_id)
    )
    bot_sessions = bs_result.scalars().all()
    if not bot_sessions:
        return {"certificates": []}

    candidate_ids = list(set(bs.candidate_id for bs in bot_sessions))

    certs_list = []
    for cid in candidate_ids:
        cert_result = await db.execute(
            select(Certificate).where(Certificate.candidate_id == cid)
        )
        certs = cert_result.scalars().all()
        for cert in certs:
            certs_list.append({
                "id": cert.id,
                "certificate_number": cert.certificate_number,
                "candidate_name": cert.candidate_name,
                "test_label": cert.test_label,
                "score_percentage": cert.score_percentage,
                "performance_label": cert.performance_label,
                "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
                "verify_url": f"https://talentcheck-tau.vercel.app/verify/{cert.certificate_number}",
            })

    return {"certificates": certs_list}


@router.get("/tests")
async def available_tests():
    """List available tests for candidates to browse."""
    from .telegram import TEST_CATALOG
    tests = []
    for key, t in TEST_CATALOG.items():
        tests.append({
            "key": t["key"],
            "label": t["label"],
            "description": t["description"],
            "question_count": t["question_count"],
            "time_limit_minutes": t["time_limit_minutes"],
            "price_etb": t["price_etb"],
        })
    return {"tests": tests}
