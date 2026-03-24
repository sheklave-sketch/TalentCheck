import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, BigInteger, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from ..database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class PlanTier(str, enum.Enum):
    starter = "starter"
    growth = "growth"
    enterprise = "enterprise"


class AssessmentStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"
    archived = "archived"


class CandidateStatus(str, enum.Enum):
    invited = "invited"
    started = "started"
    completed = "completed"
    expired = "expired"


class SessionStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    submitted = "submitted"
    scored = "scored"
    flagged = "flagged"


# ─── Models ───────────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "tc_organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    plan: Mapped[PlanTier] = mapped_column(SAEnum(PlanTier, name="tc_plantier"), default=PlanTier.starter)
    monthly_candidate_limit: Mapped[int] = mapped_column(Integer, default=10)
    candidates_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "tc_users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("tc_organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin, member
    telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="users")


class Assessment(Base):
    __tablename__ = "tc_assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("tc_organizations.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("tc_users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AssessmentStatus] = mapped_column(SAEnum(AssessmentStatus, name="tc_assessmentstatus"), default=AssessmentStatus.draft)

    # Config: list of {test_key, weight, time_limit_minutes}
    test_config: Mapped[list] = mapped_column(JSON, default=list)
    total_time_limit_minutes: Mapped[int] = mapped_column(Integer, default=60)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="assessments")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="assessment")


class Candidate(Base):
    __tablename__ = "tc_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("tc_assessments.id"), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(100))
    invited_via: Mapped[str] = mapped_column(String(20), default="email")  # email, telegram, sms
    invite_token: Mapped[str] = mapped_column(String(100), unique=True, default=gen_uuid)
    status: Mapped[CandidateStatus] = mapped_column(SAEnum(CandidateStatus, name="tc_candidatestatus"), default=CandidateStatus.invited)
    invited_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    assessment: Mapped["Assessment"] = relationship(back_populates="candidates")
    session: Mapped["TestSession | None"] = relationship(back_populates="candidate", uselist=False)
    result: Mapped["Result | None"] = relationship(back_populates="candidate", uselist=False)


class TestSession(Base):
    __tablename__ = "tc_test_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("tc_candidates.id"), unique=True, nullable=False)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("tc_assessments.id"), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus, name="tc_sessionstatus"), default=SessionStatus.pending)

    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    server_deadline: Mapped[datetime | None] = mapped_column(DateTime)  # authoritative end time

    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    tab_switch_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_urls: Mapped[list] = mapped_column(JSON, default=list)
    proctoring_flags: Mapped[list] = mapped_column(JSON, default=list)  # [{type, timestamp, detail}]

    candidate: Mapped["Candidate"] = relationship(back_populates="session")
    responses: Mapped[list["Response"]] = relationship(back_populates="session")


class Response(Base):
    __tablename__ = "tc_responses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("tc_test_sessions.id"), nullable=False)
    test_key: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. "cognitive"
    question_id: Mapped[str] = mapped_column(String(100), nullable=False)
    answer: Mapped[str | None] = mapped_column(String(500))  # selected option key
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["TestSession"] = relationship(back_populates="responses")


class Result(Base):
    __tablename__ = "tc_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("tc_candidates.id"), unique=True, nullable=False)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("tc_assessments.id"), nullable=False)

    scores_by_test: Mapped[dict] = mapped_column(JSON, default=dict)   # {test_key: {raw, pct, label}}
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    percentile: Mapped[float | None] = mapped_column(Float)            # vs other candidates in same assessment
    rank: Mapped[int | None] = mapped_column(Integer)

    has_proctoring_flags: Mapped[bool] = mapped_column(Boolean, default=False)
    pdf_url: Mapped[str | None] = mapped_column(String(500))
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="result")


class TelegramLink(Base):
    __tablename__ = "tc_telegram_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(100))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("tc_users.id"))
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("tc_candidates.id"))
    link_code: Mapped[str | None] = mapped_column(String(20))
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BotSession(Base):
    __tablename__ = "tc_bot_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("tc_candidates.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("tc_test_sessions.id"), nullable=False)
    current_test_index: Mapped[int] = mapped_column(Integer, default=0)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    answers: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    state: Mapped[str] = mapped_column(String(20), default="active")  # active, submitted, expired
