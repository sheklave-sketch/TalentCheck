from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database import get_db
from ..models.models import Assessment, AssessmentStatus, User
from .auth import get_current_user

router = APIRouter()

AVAILABLE_TESTS = [
    {"key": "cognitive", "label": "Cognitive Ability", "description": "Logical, numerical, verbal reasoning"},
    {"key": "english", "label": "English Proficiency", "description": "Grammar, reading, business communication"},
    {"key": "customer_service", "label": "Customer Service", "description": "Scenario-based service simulations"},
    {"key": "computer_skills", "label": "Basic Computer Skills", "description": "Word, Excel, email fundamentals"},
    {"key": "integrity", "label": "Integrity & Work Ethics", "description": "Situational judgment test"},
    {"key": "developer_basic", "label": "Junior Developer (Basic)", "description": "MCQ technical questions"},
]


class TestConfigItem(BaseModel):
    test_key: str
    weight: int = 1          # relative weight for overall score
    time_limit_minutes: int = 20


class CreateAssessmentRequest(BaseModel):
    title: str
    description: str | None = None
    test_config: list[TestConfigItem]
    total_time_limit_minutes: int = 60
    expires_at: datetime | None = None


@router.get("/tests")
async def list_available_tests():
    return AVAILABLE_TESTS


@router.post("/")
async def create_assessment(
    body: CreateAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    valid_keys = {t["key"] for t in AVAILABLE_TESTS}
    for item in body.test_config:
        if item.test_key not in valid_keys:
            raise HTTPException(400, f"Unknown test key: {item.test_key}")

    assessment = Assessment(
        org_id=user.org_id,
        created_by=user.id,
        title=body.title,
        description=body.description,
        test_config=[item.model_dump() for item in body.test_config],
        total_time_limit_minutes=body.total_time_limit_minutes,
        expires_at=body.expires_at,
    )
    db.add(assessment)
    await db.flush()
    return {"id": assessment.id, "title": assessment.title, "status": assessment.status}


@router.get("/")
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.org_id == user.org_id)
        .order_by(Assessment.created_at.desc())
    )
    assessments = result.scalars().all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "tests": [t["test_key"] for t in a.test_config],
            "candidate_count": len(a.candidates) if a.candidates else 0,
            "created_at": a.created_at,
        }
        for a in assessments
    ]


@router.get("/{assessment_id}")
async def get_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        raise HTTPException(404, "Assessment not found")
    return assessment


@router.patch("/{assessment_id}/status")
async def update_status(
    assessment_id: str,
    status: AssessmentStatus,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        raise HTTPException(404, "Not found")
    assessment.status = status
    return {"status": assessment.status}
