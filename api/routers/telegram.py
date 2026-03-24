"""
Telegram bot-facing API endpoints.
Authenticated via BOT_SECRET header (not OAuth2).
Only called from the bot process on localhost.
"""
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database import get_db
from ..models.models import (
    Candidate, CandidateStatus, Assessment, TestSession, SessionStatus,
    Response, User, TelegramLink, BotSession, Organization,
)
from ..services.scoring_engine import get_questions_for_client, load_test
from ..config import settings

router = APIRouter()


async def verify_bot_secret(x_bot_secret: str = Header()):
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid bot secret")


# ─── Candidate lookup ─────────────────────────────────────────────────────────

@router.get("/candidate-by-token/{invite_token}")
async def candidate_by_token(
    invite_token: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(select(Candidate).where(Candidate.invite_token == invite_token))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(404, "Invalid invite token")

    if candidate.status == CandidateStatus.completed:
        raise HTTPException(400, "Assessment already completed")
    if candidate.expires_at and candidate.expires_at < datetime.utcnow():
        raise HTTPException(400, "Invite has expired")

    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == candidate.assessment_id)
    )
    assessment = assessment_result.scalar_one()

    org_result = await db.execute(
        select(Organization).where(Organization.id == assessment.org_id)
    )
    org = org_result.scalar_one()

    # Count total questions
    total_questions = 0
    for tc in assessment.test_config:
        test_data = load_test(tc["test_key"])
        total_questions += len(test_data["questions"])

    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "org_name": org.name,
        "total_time_limit_minutes": assessment.total_time_limit_minutes,
        "test_config": assessment.test_config,
        "total_questions": total_questions,
        "status": candidate.status,
    }


# ─── Start session ────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    invite_token: str
    telegram_id: int


@router.post("/start-session")
async def start_session(
    body: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(select(Candidate).where(Candidate.invite_token == body.invite_token))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(404, "Invalid invite token")

    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == candidate.assessment_id)
    )
    assessment = assessment_result.scalar_one()

    # Check for existing session
    session_result = await db.execute(
        select(TestSession).where(TestSession.candidate_id == candidate.id)
    )
    session = session_result.scalar_one_or_none()

    if session and session.status == SessionStatus.submitted:
        raise HTTPException(400, "Already submitted")

    if not session:
        deadline = datetime.utcnow() + timedelta(minutes=assessment.total_time_limit_minutes)
        session = TestSession(
            candidate_id=candidate.id,
            assessment_id=assessment.id,
            status=SessionStatus.in_progress,
            started_at=datetime.utcnow(),
            server_deadline=deadline,
            ip_address="telegram",
            user_agent="talentcheck-bot/1.0",
        )
        db.add(session)
        candidate.status = CandidateStatus.started
        await db.flush()

    # Create or recover bot session
    bot_session_result = await db.execute(
        select(BotSession).where(
            BotSession.candidate_id == candidate.id,
            BotSession.state == "active",
        )
    )
    bot_session = bot_session_result.scalar_one_or_none()

    if not bot_session:
        bot_session = BotSession(
            telegram_id=body.telegram_id,
            candidate_id=candidate.id,
            session_id=session.id,
        )
        db.add(bot_session)
        await db.flush()

    # Build questions for all tests (without answers)
    tests = []
    for tc in assessment.test_config:
        questions = get_questions_for_client(tc["test_key"])
        tests.append({
            "test_key": tc["test_key"],
            "time_limit_minutes": tc["time_limit_minutes"],
            "questions": questions,
        })

    seconds_remaining = max(0, int((session.server_deadline - datetime.utcnow()).total_seconds()))

    return {
        "session_id": session.id,
        "bot_session_id": bot_session.id,
        "seconds_remaining": seconds_remaining,
        "current_test_index": bot_session.current_test_index,
        "current_question_index": bot_session.current_question_index,
        "tests": tests,
    }


# ─── Submit single answer ────────────────────────────────────────────────────

class SubmitAnswerRequest(BaseModel):
    session_id: str
    bot_session_id: str
    test_key: str
    question_id: str
    answer: str
    time_taken_seconds: int = 0


@router.post("/submit-answer")
async def submit_answer(
    body: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    session_result = await db.execute(
        select(TestSession).where(TestSession.id == body.session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    if session.status == SessionStatus.submitted:
        raise HTTPException(400, "Session already submitted")

    # Check deadline
    if session.server_deadline and datetime.utcnow() > session.server_deadline:
        raise HTTPException(400, "Time expired")

    # Save response
    response = Response(
        session_id=session.id,
        test_key=body.test_key,
        question_id=body.question_id,
        answer=body.answer,
        time_taken_seconds=body.time_taken_seconds,
    )
    db.add(response)

    # Update bot session progress
    bot_session_result = await db.execute(
        select(BotSession).where(BotSession.id == body.bot_session_id)
    )
    bot_session = bot_session_result.scalar_one_or_none()
    if bot_session:
        answers = bot_session.answers or []
        answers.append({
            "test_key": body.test_key,
            "question_id": body.question_id,
            "answer": body.answer,
            "time_taken_seconds": body.time_taken_seconds,
        })
        bot_session.answers = answers

    seconds_remaining = max(0, int((session.server_deadline - datetime.utcnow()).total_seconds()))
    await db.flush()

    return {"recorded": True, "seconds_remaining": seconds_remaining}


# ─── Update bot session progress ─────────────────────────────────────────────

class UpdateProgressRequest(BaseModel):
    bot_session_id: str
    current_test_index: int
    current_question_index: int


@router.post("/update-progress")
async def update_progress(
    body: UpdateProgressRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(
        select(BotSession).where(BotSession.id == body.bot_session_id)
    )
    bot_session = result.scalar_one_or_none()
    if not bot_session:
        raise HTTPException(404, "Bot session not found")

    bot_session.current_test_index = body.current_test_index
    bot_session.current_question_index = body.current_question_index
    return {"updated": True}


# ─── Submit session (finalize) ────────────────────────────────────────────────

class SubmitSessionRequest(BaseModel):
    session_id: str
    bot_session_id: str | None = None


@router.post("/submit-session")
async def submit_session(
    body: SubmitSessionRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(
        select(TestSession).where(TestSession.id == body.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    if session.status == SessionStatus.submitted:
        return {"submitted": True, "already": True}

    session.status = SessionStatus.submitted
    session.submitted_at = datetime.utcnow()

    candidate_result = await db.execute(
        select(Candidate).where(Candidate.id == session.candidate_id)
    )
    candidate = candidate_result.scalar_one()
    candidate.status = CandidateStatus.completed

    # Mark bot session
    if body.bot_session_id:
        bs_result = await db.execute(
            select(BotSession).where(BotSession.id == body.bot_session_id)
        )
        bs = bs_result.scalar_one_or_none()
        if bs:
            bs.state = "submitted"

    await db.flush()
    return {"submitted": True}


# ─── Proctor event ────────────────────────────────────────────────────────────

class ProctorEventRequest(BaseModel):
    session_id: str
    type: str
    detail: str = ""


@router.post("/proctor-event")
async def proctor_event(
    body: ProctorEventRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(
        select(TestSession).where(TestSession.id == body.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    flags = session.proctoring_flags or []
    flags.append({"type": body.type, "detail": body.detail, "ts": datetime.utcnow().isoformat()})
    session.proctoring_flags = flags
    return {"logged": True}


# ─── Practice questions ───────────────────────────────────────────────────────

@router.get("/practice-questions/{test_key}")
async def practice_questions(
    test_key: str,
    count: int = 5,
    _: None = Depends(verify_bot_secret),
):
    try:
        test_data = load_test(test_key)
    except ValueError:
        raise HTTPException(404, f"Unknown test: {test_key}")

    questions = test_data["questions"]
    sample = random.sample(questions, min(count, len(questions)))
    return {
        "test_key": test_key,
        "label": test_data["label"],
        "questions": sample,  # includes correct_answer for practice
    }


# ─── HR linking ───────────────────────────────────────────────────────────────

class LinkHRRequest(BaseModel):
    telegram_id: int
    link_code: str


@router.post("/link-hr")
async def link_hr(
    body: LinkHRRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(
        select(TelegramLink).where(
            TelegramLink.link_code == body.link_code,
            TelegramLink.user_id.is_(None),
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(404, "Invalid or expired link code")

    # The link_code was generated by the web dashboard and has the user_id pending
    # For now, we store the telegram_id association
    link.telegram_id = body.telegram_id
    link.linked_at = datetime.utcnow()
    return {"linked": True}


# ─── Get HR users with Telegram for notifications ─────────────────────────────

@router.get("/hr-telegram-ids/{org_id}")
async def hr_telegram_ids(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    result = await db.execute(
        select(User).where(
            User.org_id == org_id,
            User.telegram_id.isnot(None),
        )
    )
    users = result.scalars().all()
    return [{"user_id": u.id, "telegram_id": u.telegram_id, "full_name": u.full_name} for u in users]
