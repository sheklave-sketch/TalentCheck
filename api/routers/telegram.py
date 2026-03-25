"""
Telegram bot-facing API endpoints.
Authenticated via BOT_SECRET header (not OAuth2).
Only called from the bot process on localhost.
"""
import random
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from ..database import get_db
from ..models.models import (
    Candidate, CandidateStatus, Assessment, AssessmentStatus, TestSession,
    SessionStatus, Response, Result, User, TelegramLink, BotSession,
    Organization, PlanTier,
)
from ..services.scoring_engine import get_questions_for_client, load_test
from ..config import settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── Test catalog (prices in ETB) ────────────────────────────────────────────

TEST_CATALOG = {
    "cognitive": {
        "key": "cognitive",
        "label": "Cognitive Ability Test",
        "description": "Logical reasoning, numerical reasoning, verbal reasoning",
        "question_count": 40,
        "time_limit_minutes": 45,
        "price_etb": 150,
        "sample_question": "What comes next in the series: 2, 6, 18, 54, ?",
        "requirements": "No special requirements. Tests logical, numerical, and verbal reasoning ability.",
    },
    "english": {
        "key": "english",
        "label": "English Proficiency Test",
        "description": "Grammar, vocabulary, reading comprehension",
        "question_count": 40,
        "time_limit_minutes": 40,
        "price_etb": 150,
        "sample_question": "Choose the correct form: 'Neither the manager nor the employees ___ present.'",
        "requirements": "Tests English language proficiency for professional settings.",
    },
    "customer_service": {
        "key": "customer_service",
        "label": "Customer Service Test",
        "description": "Communication, problem-solving, empathy, conflict resolution",
        "question_count": 40,
        "time_limit_minutes": 35,
        "price_etb": 150,
        "sample_question": "A customer is angry about a delayed order. What is your first step?",
        "requirements": "Ideal for customer-facing roles. Tests soft skills and judgment.",
    },
    "computer_skills": {
        "key": "computer_skills",
        "label": "Computer Skills Test",
        "description": "MS Office, email, internet, basic IT literacy",
        "question_count": 40,
        "time_limit_minutes": 35,
        "price_etb": 150,
        "sample_question": "Which keyboard shortcut is used to copy selected text?",
        "requirements": "Tests basic computer literacy for office environments.",
    },
    "integrity": {
        "key": "integrity",
        "label": "Integrity & Ethics Test",
        "description": "Workplace ethics, honesty, decision-making in ethical dilemmas",
        "question_count": 40,
        "time_limit_minutes": 30,
        "price_etb": 100,
        "sample_question": "You find a colleague has been inflating expense reports. What do you do?",
        "requirements": "Situational judgment test. No right/wrong — measures ethical reasoning.",
    },
    "developer_basic": {
        "key": "developer_basic",
        "label": "Developer (Junior) Test",
        "description": "Programming fundamentals, algorithms, debugging, SQL basics",
        "question_count": 40,
        "time_limit_minutes": 50,
        "price_etb": 200,
        "sample_question": "What is the time complexity of binary search?",
        "requirements": "For junior developer positions. Covers Python, JS, SQL, and algorithms.",
    },
}


async def verify_bot_secret(x_bot_secret: str = Header()):
    if x_bot_secret != settings.BOT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid bot secret")


# ─── Register candidate ─────────────────────────────────────────────────────

class RegisterCandidateRequest(BaseModel):
    full_name: str
    email: str = ""
    phone: str = ""
    telegram_id: int
    telegram_username: str | None = None


@router.post("/register-candidate")
async def register_candidate(
    body: RegisterCandidateRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    # Check if telegram_id already linked
    existing = await db.execute(
        select(TelegramLink).where(TelegramLink.telegram_id == body.telegram_id)
    )
    link = existing.scalar_one_or_none()
    if link and link.candidate_id:
        return {"already_registered": True, "telegram_link_id": link.id}

    # Create a TelegramLink record for this candidate
    if not link:
        link = TelegramLink(
            telegram_id=body.telegram_id,
            telegram_username=body.telegram_username,
        )
        db.add(link)
        await db.flush()

    # Store candidate info in link metadata
    link.link_code = f"cand_{body.email}"
    link.telegram_username = body.telegram_username

    await db.flush()
    return {
        "registered": True,
        "telegram_link_id": link.id,
        "full_name": body.full_name,
        "email": body.email,
        "phone": body.phone,
    }


# ─── Register employer ──────────────────────────────────────────────────────

class RegisterEmployerRequest(BaseModel):
    org_name: str
    full_name: str
    email: str
    password: str
    telegram_id: int
    telegram_username: str | None = None


@router.post("/register-employer")
async def register_employer(
    body: RegisterEmployerRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        return {"error": True, "detail": "Email already registered. Use /link to connect your Telegram."}

    # Create organization
    org = Organization(name=body.org_name, plan=PlanTier.starter)
    db.add(org)
    await db.flush()

    # Create user
    user = User(
        org_id=org.id,
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
        full_name=body.full_name,
        role="admin",
        telegram_id=body.telegram_id,
    )
    db.add(user)
    await db.flush()

    # Create telegram link
    link = TelegramLink(
        telegram_id=body.telegram_id,
        telegram_username=body.telegram_username,
        user_id=user.id,
    )
    db.add(link)
    await db.flush()

    return {
        "registered": True,
        "user_id": user.id,
        "org_id": org.id,
        "org_name": org.name,
        "full_name": user.full_name,
    }


# ─── List tests with prices ─────────────────────────────────────────────────

@router.get("/tests")
async def list_tests(
    _: None = Depends(verify_bot_secret),
):
    return {"tests": list(TEST_CATALOG.values())}


# ─── Test details ────────────────────────────────────────────────────────────

@router.get("/tests/{test_key}")
async def test_details(
    test_key: str,
    _: None = Depends(verify_bot_secret),
):
    if test_key not in TEST_CATALOG:
        raise HTTPException(404, f"Unknown test: {test_key}")
    return TEST_CATALOG[test_key]


# ─── Candidate lookup ───────────────────────────────────────────────────────

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


# ─── Start session ──────────────────────────────────────────────────────────

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


# ─── Submit single answer ───────────────────────────────────────────────────

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

    # Anti-cheat: flag fast answers
    proctoring_flags = session.proctoring_flags or []
    if body.time_taken_seconds < 3:
        proctoring_flags.append({
            "type": "fast_answer",
            "detail": f"Question {body.question_id} answered in {body.time_taken_seconds}s",
            "ts": datetime.utcnow().isoformat(),
        })
        session.proctoring_flags = proctoring_flags

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


# ─── Update bot session progress ────────────────────────────────────────────

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


# ─── Submit session (finalize) ───────────────────────────────────────────────

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


# ─── Proctor event ───────────────────────────────────────────────────────────

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


# ─── Practice questions ──────────────────────────────────────────────────────

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


# ─── HR linking ──────────────────────────────────────────────────────────────

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

    link.telegram_id = body.telegram_id
    link.linked_at = datetime.utcnow()
    return {"linked": True}


# ─── Get HR users with Telegram for notifications ────────────────────────────

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


# ─── Candidate results ──────────────────────────────────────────────────────

@router.get("/candidate-results/{telegram_id}")
async def candidate_results(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    """Get all results for a candidate identified by telegram_id."""
    # Find all candidates associated with this telegram_id via bot sessions
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


# ─── Request demo ────────────────────────────────────────────────────────────

class RequestDemoRequest(BaseModel):
    org_name: str
    contact_name: str
    phone: str
    email: str
    notes: str = ""
    telegram_id: int | None = None


@router.post("/request-demo")
async def request_demo(
    body: RequestDemoRequest,
    _: None = Depends(verify_bot_secret),
):
    # In production, this would store in DB and notify admin
    # For now, we log it and return success
    print(
        f"[DEMO REQUEST] org={body.org_name}, contact={body.contact_name}, "
        f"phone={body.phone}, email={body.email}, notes={body.notes}, "
        f"telegram_id={body.telegram_id}"
    )
    return {"received": True, "message": "Demo request received. Our team will contact you within 24 hours."}


# ─── Invite candidates ──────────────────────────────────────────────────────

class InviteCandidateItem(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None


class InviteCandidatesRequest(BaseModel):
    assessment_id: str
    candidates: list[InviteCandidateItem]
    telegram_id: int


@router.post("/invite-candidates")
async def invite_candidates(
    body: InviteCandidatesRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    # Verify the telegram_id belongs to an employer
    link_result = await db.execute(
        select(TelegramLink).where(
            TelegramLink.telegram_id == body.telegram_id,
            TelegramLink.user_id.isnot(None),
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        return {"error": True, "detail": "Your Telegram is not linked to an employer account."}

    user_result = await db.execute(select(User).where(User.id == link.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": True, "detail": "User account not found."}

    # Verify assessment belongs to their org
    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == body.assessment_id)
    )
    assessment = assessment_result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        return {"error": True, "detail": "Assessment not found or unauthorized."}

    invited = []
    bot_username = "TalentCheckBot"  # Will be resolved dynamically by the bot

    for c in body.candidates:
        invite_token = str(uuid.uuid4())
        candidate = Candidate(
            assessment_id=body.assessment_id,
            full_name=c.full_name,
            email=c.email,
            phone=c.phone,
            invite_token=invite_token,
            invited_via="telegram",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.add(candidate)
        await db.flush()

        deep_link = f"https://t.me/{bot_username}?start={invite_token}"
        invited.append({
            "candidate_id": candidate.id,
            "full_name": c.full_name,
            "invite_token": invite_token,
            "deep_link": deep_link,
        })

    return {"invited": invited, "count": len(invited)}


# ─── Employer results ────────────────────────────────────────────────────────

@router.get("/employer-results/{telegram_id}/{assessment_id}")
async def employer_results(
    telegram_id: int,
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    # Verify employer
    link_result = await db.execute(
        select(TelegramLink).where(
            TelegramLink.telegram_id == telegram_id,
            TelegramLink.user_id.isnot(None),
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        return {"error": True, "detail": "Not linked to employer account."}

    user_result = await db.execute(select(User).where(User.id == link.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": True, "detail": "User not found."}

    # Verify assessment
    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    assessment = assessment_result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        return {"error": True, "detail": "Assessment not found or unauthorized."}

    # Get all results for this assessment, ordered by rank
    results_result = await db.execute(
        select(Result).where(Result.assessment_id == assessment_id)
        .order_by(Result.rank)
    )
    results = results_result.scalars().all()

    # Get all candidates for this assessment
    candidates_result = await db.execute(
        select(Candidate).where(Candidate.assessment_id == assessment_id)
    )
    all_candidates = candidates_result.scalars().all()
    cand_map = {c.id: c for c in all_candidates}

    output = []
    for r in results:
        cand = cand_map.get(r.candidate_id)
        if not cand:
            continue
        output.append({
            "rank": r.rank,
            "candidate_name": cand.full_name,
            "email": cand.email,
            "total_score": r.total_score,
            "percentile": r.percentile,
            "scores_by_test": r.scores_by_test,
            "has_flags": r.has_proctoring_flags,
            "status": cand.status.value if cand.status else "unknown",
        })

    total_invited = len(all_candidates)
    total_completed = len([c for c in all_candidates if c.status == CandidateStatus.completed])
    total_scored = len(results)

    return {
        "assessment_title": assessment.title,
        "total_invited": total_invited,
        "total_completed": total_completed,
        "total_scored": total_scored,
        "candidates": output,
    }


# ─── Employer assessments list ──────────────────────────────────────────────

@router.get("/employer-assessments/{telegram_id}")
async def employer_assessments(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    link_result = await db.execute(
        select(TelegramLink).where(
            TelegramLink.telegram_id == telegram_id,
            TelegramLink.user_id.isnot(None),
        )
    )
    link = link_result.scalar_one_or_none()
    if not link:
        return {"error": True, "detail": "Not linked to employer account."}

    user_result = await db.execute(select(User).where(User.id == link.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": True, "detail": "User not found."}

    assessments_result = await db.execute(
        select(Assessment).where(Assessment.org_id == user.org_id)
        .order_by(Assessment.created_at.desc())
    )
    assessments = assessments_result.scalars().all()

    output = []
    for a in assessments:
        # Count candidates
        cand_count_result = await db.execute(
            select(func.count(Candidate.id)).where(Candidate.assessment_id == a.id)
        )
        cand_count = cand_count_result.scalar() or 0

        output.append({
            "id": a.id,
            "title": a.title,
            "status": a.status.value,
            "candidate_count": cand_count,
            "created_at": a.created_at.isoformat(),
        })

    return {"assessments": output, "org_name": user.organization.name if hasattr(user, 'organization') else ""}


# ─── Check telegram link status ─────────────────────────────────────────────

@router.get("/check-link/{telegram_id}")
async def check_link(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    link_result = await db.execute(
        select(TelegramLink).where(TelegramLink.telegram_id == telegram_id)
    )
    link = link_result.scalar_one_or_none()

    if not link:
        return {"linked": False, "role": None}

    if link.user_id:
        user_result = await db.execute(select(User).where(User.id == link.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            org_result = await db.execute(select(Organization).where(Organization.id == user.org_id))
            org = org_result.scalar_one_or_none()
            return {
                "linked": True,
                "role": "employer",
                "full_name": user.full_name,
                "email": user.email,
                "org_id": user.org_id,
                "org_name": org.name if org else "",
            }

    if link.candidate_id:
        cand_result = await db.execute(select(Candidate).where(Candidate.id == link.candidate_id))
        cand = cand_result.scalar_one_or_none()
        return {
            "linked": True,
            "role": "candidate",
            "candidate_id": link.candidate_id,
            "full_name": cand.full_name if cand else "",
        }

    # Has a link record but not fully linked — candidate registered via bot
    return {
        "linked": True,
        "role": "candidate_registered",
        "link_id": link.id,
        "full_name": link.telegram_username or "",
    }


# ─── Generate Chapa payment link ─────────────────────────────────────────────

class InitiatePaymentRequest(BaseModel):
    telegram_id: int
    test_key: str
    email: str
    full_name: str
    phone: str


@router.post("/initiate-payment")
async def initiate_payment(
    body: InitiatePaymentRequest,
    _: None = Depends(verify_bot_secret),
):
    """Generate a Chapa payment link for a self-service candidate test."""
    if body.test_key not in TEST_CATALOG:
        raise HTTPException(404, f"Unknown test: {body.test_key}")

    test = TEST_CATALOG[body.test_key]
    amount = test["price_etb"]
    tx_ref = f"tc_{body.telegram_id}_{body.test_key}_{uuid.uuid4().hex[:8]}"

    # In production, this calls Chapa API
    # For now, return a mock payment link
    chapa_url = f"https://checkout.chapa.co/checkout/payment/{tx_ref}"

    return {
        "payment_url": chapa_url,
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": "ETB",
        "test_key": body.test_key,
        "test_label": test["label"],
    }


# ─── Verify Chapa payment ───────────────────────────────────────────────────

@router.get("/verify-payment/{tx_ref}")
async def verify_payment(
    tx_ref: str,
    _: None = Depends(verify_bot_secret),
):
    """Verify a Chapa payment by tx_ref."""
    # In production, this calls Chapa verify API
    # For now, return mock success
    return {
        "verified": True,
        "tx_ref": tx_ref,
        "status": "success",
    }


# ─── Generate certificate PDF ───────────────────────────────────────────────

@router.get("/certificate/{candidate_id}")
async def get_certificate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_bot_secret),
):
    """Generate a PDF certificate for a passed candidate."""
    from ..services.pdf_generator import build_report

    cand_result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = cand_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(404, "Candidate not found")

    res_result = await db.execute(select(Result).where(Result.candidate_id == candidate_id))
    result = res_result.scalar_one_or_none()
    if not result:
        raise HTTPException(404, "Results not yet scored")

    if result.total_score < 60.0:
        raise HTTPException(400, "Score below passing threshold (60%)")

    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == candidate.assessment_id)
    )
    assessment = assessment_result.scalar_one()

    org_result = await db.execute(
        select(Organization).where(Organization.id == assessment.org_id)
    )
    org = org_result.scalar_one()

    total_cands_result = await db.execute(
        select(func.count(Result.id)).where(Result.assessment_id == candidate.assessment_id)
    )
    total_candidates = total_cands_result.scalar() or 1

    pdf_bytes = build_report(
        candidate_name=candidate.full_name,
        candidate_email=candidate.email or "",
        org_name=org.name,
        assessment_title=assessment.title,
        scores_by_test=result.scores_by_test,
        total_score=result.total_score,
        percentile=result.percentile,
        rank=result.rank,
        total_candidates=total_candidates,
        has_flags=result.has_proctoring_flags,
        scored_at=result.scored_at,
    )

    import base64
    return {
        "pdf_base64": base64.b64encode(pdf_bytes).decode(),
        "filename": f"TalentCheck_Certificate_{candidate.full_name.replace(' ', '_')}.pdf",
        "candidate_name": candidate.full_name,
        "total_score": result.total_score,
    }
