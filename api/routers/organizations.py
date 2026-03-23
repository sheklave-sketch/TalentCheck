from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database import get_db
from ..models.models import Organization, User
from .auth import get_current_user

router = APIRouter()


class UpdateOrgRequest(BaseModel):
    name: str | None = None
    logo_url: str | None = None


@router.get("/me")
async def get_my_org(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    return {
        "id": org.id,
        "name": org.name,
        "logo_url": org.logo_url,
        "plan": org.plan,
        "monthly_candidate_limit": org.monthly_candidate_limit,
        "candidates_used_this_month": org.candidates_used_this_month,
    }


@router.patch("/me")
async def update_my_org(
    body: UpdateOrgRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    if body.name:
        org.name = body.name
    if body.logo_url is not None:
        org.logo_url = body.logo_url
    return {"updated": True}
