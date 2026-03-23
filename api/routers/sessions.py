"""
Session router — candidate-facing (no auth, token-based).
All answer processing is server-side. Correct answers are never sent to the client.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database import get_db
from ..models.models import (
    Candidate, CandidateStatus, TestSession, SessionStatus, Response, Assessment
)
from ..services.scoring_engine import get_questions_for_client

router = APIRouter()


async def get_candidate_by_token(token: str, db: AsyncSession) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.invite_token == token))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(404, "Invalid or expired invite link")
    if candidate.status == CandidateStatus.completed:
        raise HTTPException(400, "This assessment has already been submitted")
    if candidate.expires_at and candidate.expires_at < datetime.utcnow():
        candidate.status = CandidateStatus.expired
        raise HTTPException(400, "This invite link has expired")
    return candidate


@router.get("/start/{token}")
async def start_session(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Returns assessment config + questions (no correct answers)."""
    candidate = await get_candidate_by_token(token, db)

    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == candidate.assessment_id)
    )
    assessment = assessment_result.scalar_one()

    # Check for existing session
    session_result = await db.execute(
        select(TestSession).where(TestSession.candidate_id == candidate.id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        deadline = datetime.utcnow() + timedelta(minutes=assessment.total_time_limit_minutes)
        session = TestSession(
            candidate_id=candidate.id,
            assessment_id=assessment.id,
            status=SessionStatus.in_progress,
            started_at=datetime.utcnow(),
            server_deadline=deadline,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(session)
        candidate.status = CandidateStatus.started
        await db.flush()

    # Build questions payload (no answers)
    tests = []
    for test_cfg in assessment.test_config:
        questions = get_questions_for_client(test_cfg["test_key"])
        tests.append({
            "test_key": test_cfg["test_key"],
            "time_limit_minutes": test_cfg["time_limit_minutes"],
            "questions": questions,
        })

    seconds_remaining = max(0, int((session.server_deadline - datetime.utcnow()).total_seconds()))

    return {
        "session_id": session.id,
        "candidate_name": candidate.full_name,
        "assessment_title": assessment.title,
        "total_time_limit_minutes": assessment.total_time_limit_minutes,
        "seconds_remaining": seconds_remaining,
        "tests": tests,
    }


class ProctorEvent(BaseModel):
    type: str        # tab_switch, visibility_change
    detail: str = ""


@router.post("/session/{session_id}/proctor-event")
async def log_proctor_event(
    session_id: str,
    event: ProctorEvent,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TestSession).where(TestSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    if event.type == "tab_switch":
        session.tab_switch_count += 1

    flags = session.proctoring_flags or []
    flags.append({"type": event.type, "detail": event.detail, "ts": datetime.utcnow().isoformat()})
    session.proctoring_flags = flags
    return {"logged": True}


class SubmitRequest(BaseModel):
    session_id: str
    responses: list[dict]   # [{test_key, question_id, answer, time_taken_seconds}]


@router.post("/submit")
async def submit_session(body: SubmitRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TestSession).where(TestSession.id == body.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    if session.status == SessionStatus.submitted:
        raise HTTPException(400, "Already submitted")

    # Enforce server-side deadline
    if session.server_deadline and datetime.utcnow() > session.server_deadline:
        # Accept but flag it
        flags = session.proctoring_flags or []
        flags.append({"type": "late_submission", "ts": datetime.utcnow().isoformat()})
        session.proctoring_flags = flags

    # Persist responses
    for r in body.responses:
        response = Response(
            session_id=session.id,
            test_key=r["test_key"],
            question_id=r["question_id"],
            answer=r.get("answer"),
            time_taken_seconds=r.get("time_taken_seconds"),
        )
        db.add(response)

    session.status = SessionStatus.submitted
    session.submitted_at = datetime.utcnow()

    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == session.candidate_id)
    )
    candidate = candidate_result.scalar_one()
    candidate.status = CandidateStatus.completed

    await db.flush()
    return {"submitted": True, "message": "Your assessment has been submitted successfully."}
