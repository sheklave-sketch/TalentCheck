from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response as HTTPResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from io import BytesIO

import pandas as pd

from ..database import get_db
from ..models.models import (
    Assessment, Candidate, TestSession, SessionStatus, Response, Result, User
)
from ..services.scoring_engine import score_session, compute_weighted_total, compute_percentile_ranks
from ..services.pdf_generator import build_report
from .auth import get_current_user

router = APIRouter()


@router.post("/score/{assessment_id}")
async def score_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Score all submitted-but-unscored sessions for an assessment."""
    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    assessment = assessment_result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        raise HTTPException(404, "Not found")

    candidates_result = await db.execute(
        select(Candidate).where(Candidate.assessment_id == assessment_id)
    )
    candidates = candidates_result.scalars().all()

    scored_count = 0
    all_totals = []
    all_candidate_ids = []

    for candidate in candidates:
        session_result = await db.execute(
            select(TestSession).where(
                TestSession.candidate_id == candidate.id,
                TestSession.status == SessionStatus.submitted,
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            continue

        # Load all responses for this session
        responses_result = await db.execute(
            select(Response).where(Response.session_id == session.id)
        )
        responses = responses_result.scalars().all()

        # Group by test
        by_test: dict[str, list] = {}
        for r in responses:
            by_test.setdefault(r.test_key, []).append(
                {"question_id": r.question_id, "answer": r.answer}
            )

        # Score each test and mark correct/incorrect in DB
        scores_by_test = {}
        for test_cfg in assessment.test_config:
            test_key = test_cfg["test_key"]
            test_responses = by_test.get(test_key, [])
            result_data = score_session(test_key, test_responses)
            scores_by_test[test_key] = result_data

            # Update is_correct on each response
            from ..services.scoring_engine import load_test
            test_data = load_test(test_key)
            answer_key = {q["id"]: q["correct_answer"] for q in test_data["questions"]}
            for r in responses:
                if r.test_key == test_key:
                    r.is_correct = answer_key.get(r.question_id) == r.answer

        total = compute_weighted_total(scores_by_test, assessment.test_config)

        # Check existing result
        existing_result = await db.execute(
            select(Result).where(Result.candidate_id == candidate.id)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.scores_by_test = scores_by_test
            existing.total_score = total
            existing.has_proctoring_flags = bool(session.proctoring_flags)
        else:
            res = Result(
                candidate_id=candidate.id,
                assessment_id=assessment_id,
                scores_by_test=scores_by_test,
                total_score=total,
                has_proctoring_flags=bool(session.proctoring_flags),
            )
            db.add(res)

        session.status = SessionStatus.scored
        all_totals.append(total)
        all_candidate_ids.append(candidate.id)
        scored_count += 1

    # Compute percentile ranks and assign
    percentiles = compute_percentile_ranks(all_totals)
    sorted_indices = sorted(range(len(all_totals)), key=lambda i: all_totals[i], reverse=True)

    for rank_pos, idx in enumerate(sorted_indices, 1):
        cid = all_candidate_ids[idx]
        res_result = await db.execute(select(Result).where(Result.candidate_id == cid))
        res = res_result.scalar_one_or_none()
        if res:
            res.percentile = percentiles[idx]
            res.rank = rank_pos

    await db.flush()
    return {"scored": scored_count}


@router.get("/assessment/{assessment_id}")
async def get_results(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    assessment = assessment_result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        raise HTTPException(404, "Not found")

    results_result = await db.execute(
        select(Result).where(Result.assessment_id == assessment_id)
        .order_by(Result.rank)
    )
    results = results_result.scalars().all()

    output = []
    for r in results:
        cand_result = await db.execute(select(Candidate).where(Candidate.id == r.candidate_id))
        candidate = cand_result.scalar_one()
        output.append({
            "rank": r.rank,
            "candidate_id": r.candidate_id,
            "full_name": candidate.full_name,
            "email": candidate.email,
            "total_score": r.total_score,
            "percentile": r.percentile,
            "scores_by_test": r.scores_by_test,
            "has_flags": r.has_proctoring_flags,
            "pdf_url": r.pdf_url,
        })
    return output


@router.get("/export/{assessment_id}")
async def export_results_excel(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = await get_results(assessment_id, db, user)
    rows = []
    for r in results:
        row = {
            "Rank": r["rank"],
            "Name": r["full_name"],
            "Email": r["email"],
            "Total Score (%)": r["total_score"],
            "Percentile": r["percentile"],
            "Proctoring Flags": "Yes" if r["has_flags"] else "No",
        }
        for test_key, data in (r.get("scores_by_test") or {}).items():
            row[f"{test_key.replace('_', ' ').title()} (%)"] = data.get("percentage")
        rows.append(row)

    df = pd.DataFrame(rows)
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)

    return HTTPResponse(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=results_{assessment_id[:8]}.xlsx"},
    )


@router.get("/pdf/{candidate_id}")
async def get_candidate_pdf(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cand_result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = cand_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(404, "Candidate not found")

    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == candidate.assessment_id)
    )
    assessment = assessment_result.scalar_one()
    if assessment.org_id != user.org_id:
        raise HTTPException(403, "Forbidden")

    res_result = await db.execute(select(Result).where(Result.candidate_id == candidate_id))
    result = res_result.scalar_one_or_none()
    if not result:
        raise HTTPException(404, "Results not yet scored")

    total_cands_result = await db.execute(
        select(Result).where(Result.assessment_id == candidate.assessment_id)
    )
    total_candidates = len(total_cands_result.scalars().all())

    pdf_bytes = build_report(
        candidate_name=candidate.full_name,
        candidate_email=candidate.email,
        org_name=assessment.organization.name if hasattr(assessment, 'organization') else "",
        assessment_title=assessment.title,
        scores_by_test=result.scores_by_test,
        total_score=result.total_score,
        percentile=result.percentile,
        rank=result.rank,
        total_candidates=total_candidates,
        has_flags=result.has_proctoring_flags,
        scored_at=result.scored_at,
    )

    return HTTPResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{candidate_id[:8]}.pdf"},
    )
