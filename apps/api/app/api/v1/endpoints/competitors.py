"""Competitor endpoints for project competitor analysis"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.competitor import Competitor
from ._crud_helpers import verify_project_owner, get_owned_resource, list_project_resources, apply_update

router = APIRouter()


# ============== Request/Response Models ==============

class CompetitorCreate(BaseModel):
    name: str
    description: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    features: Optional[List[str]] = None
    pricing: Optional[str] = None
    market_position: Optional[str] = None
    source: Optional[str] = None


class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    features: Optional[List[str]] = None
    pricing: Optional[str] = None
    market_position: Optional[str] = None
    source: Optional[str] = None


class CompetitorResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: Optional[str]
    strengths: Optional[str]
    weaknesses: Optional[str]
    features: Optional[List[str]]
    pricing: Optional[str]
    market_position: Optional[str]
    source: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============== Endpoints ==============

@rate_limit(requests=100, window=60)
@router.get("/projects/{project_id}/competitors", response_model=dict)
async def list_competitors(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all competitors for a project"""
    items, schema = await list_project_resources(db, Competitor, project_id, user_id, CompetitorResponse)
    return ResponseBuilder.success([schema.model_validate(c) for c in items])


@rate_limit(requests=30, window=60)
@router.post("/projects/{project_id}/competitors", response_model=dict)
async def create_competitor(
    project_id: str,
    data: CompetitorCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new competitor for a project"""
    await verify_project_owner(db, project_id, user_id)
    competitor = Competitor(project_id=project_id, created_by=user_id, **data.model_dump())
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)
    return ResponseBuilder.success(CompetitorResponse.model_validate(competitor))


@rate_limit(requests=100, window=60)
@router.get("/competitors/{competitor_id}", response_model=dict)
async def get_competitor(
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a single competitor"""
    competitor = await get_owned_resource(db, Competitor, competitor_id, user_id)
    return ResponseBuilder.success(CompetitorResponse.model_validate(competitor))


@rate_limit(requests=30, window=60)
@router.put("/competitors/{competitor_id}", response_model=dict)
async def update_competitor(
    competitor_id: str,
    data: CompetitorUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a competitor"""
    competitor = await get_owned_resource(db, Competitor, competitor_id, user_id)
    await apply_update(db, competitor, data)
    return ResponseBuilder.success(CompetitorResponse.model_validate(competitor))


@rate_limit(requests=20, window=60)
@router.delete("/competitors/{competitor_id}", response_model=dict)
async def delete_competitor(
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a competitor"""
    competitor = await get_owned_resource(db, Competitor, competitor_id, user_id)
    competitor.soft_delete()
    await db.commit()
    return ResponseBuilder.success({"deleted": True})
