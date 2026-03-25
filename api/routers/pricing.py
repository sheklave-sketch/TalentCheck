"""Test pricing management endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from ..database import get_db
from ..models.models import TestPricing, User
from .auth import get_current_user

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PricingOut(BaseModel):
    id: str
    test_key: str
    price_etb: float
    is_active: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class PricingUpdate(BaseModel):
    price_etb: float | None = None
    is_active: bool | None = None


# ─── Public: List all test prices ─────────────────────────────────────────────

@router.get("/", response_model=list[PricingOut])
async def list_pricing(db: AsyncSession = Depends(get_db)):
    """Public endpoint — list all test prices."""
    result = await db.execute(
        select(TestPricing).order_by(TestPricing.test_key)
    )
    return result.scalars().all()


# ─── Admin: Update a test price ──────────────────────────────────────────────

@router.patch("/{test_key}", response_model=PricingOut)
async def update_pricing(
    test_key: str,
    body: PricingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin-only — update pricing for a test. Creates the record if it doesn't exist."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(
        select(TestPricing).where(TestPricing.test_key == test_key)
    )
    pricing = result.scalar_one_or_none()

    if not pricing:
        # Create new pricing record
        pricing = TestPricing(
            test_key=test_key,
            price_etb=body.price_etb if body.price_etb is not None else 0.0,
            is_active=body.is_active if body.is_active is not None else True,
        )
        db.add(pricing)
    else:
        if body.price_etb is not None:
            pricing.price_etb = body.price_etb
        if body.is_active is not None:
            pricing.is_active = body.is_active
        pricing.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(pricing)
    return pricing
