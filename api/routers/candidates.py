from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from ..database import get_db
from ..models.models import Assessment, Candidate, CandidateStatus, Organization, User
from ..services.invitation import send_email_invite, send_sms_invite
from ..config import settings
from .auth import get_current_user

router = APIRouter()


class InviteRequest(BaseModel):
    assessment_id: str
    candidates: list[dict]   # [{full_name, email, phone?}]
    expires_in_days: int = 7


@router.post("/invite")
async def invite_candidates(
    body: InviteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assessment_result = await db.execute(
        select(Assessment).where(Assessment.id == body.assessment_id)
    )
    assessment = assessment_result.scalar_one_or_none()
    if not assessment or assessment.org_id != user.org_id:
        raise HTTPException(404, "Assessment not found")

    if assessment.status != "active":
        raise HTTPException(400, "Assessment must be active to invite candidates")

    org_result = await db.execute(
        select(Organization).where(Organization.id == user.org_id)
    )
    org = org_result.scalar_one()

    expires_at = datetime.utcnow() + timedelta(days=body.expires_in_days)
    created = []

    for c_data in body.candidates:
        candidate = Candidate(
            assessment_id=assessment.id,
            email=c_data["email"],
            phone=c_data.get("phone"),
            full_name=c_data["full_name"],
            expires_at=expires_at,
        )
        db.add(candidate)
        await db.flush()

        invite_url = f"{settings.FRONTEND_URL}/test/{candidate.invite_token}"

        background_tasks.add_task(
            send_email_invite,
            to_email=candidate.email,
            candidate_name=candidate.full_name,
            org_name=org.name,
            assessment_title=assessment.title,
            invite_url=invite_url,
            expires_in_days=body.expires_in_days,
        )

        if candidate.phone:
            background_tasks.add_task(
                send_sms_invite,
                phone=candidate.phone,
                candidate_name=candidate.full_name,
                org_name=org.name,
                invite_url=invite_url,
            )

        created.append({"id": candidate.id, "email": candidate.email, "invite_token": candidate.invite_token})

    return {"invited": len(created), "candidates": created}


@router.get("/by-assessment/{assessment_id}")
async def list_candidates(
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

    result = await db.execute(
        select(Candidate).where(Candidate.assessment_id == assessment_id)
        .order_by(Candidate.invited_at.desc())
    )
    candidates = result.scalars().all()
    return [
        {
            "id": c.id,
            "full_name": c.full_name,
            "email": c.email,
            "status": c.status,
            "invited_at": c.invited_at,
        }
        for c in candidates
    ]
