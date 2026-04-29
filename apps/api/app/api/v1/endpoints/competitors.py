"""Competitor endpoints for project competitor analysis"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.competitor import Competitor
from app.models.project import Project

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

@router.get("/projects/{project_id}/competitors", response_model=dict)
async def list_competitors(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all competitors for a project"""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    result = await db.execute(
        select(Competitor)
        .where(Competitor.project_id == project_id)
        .order_by(desc(Competitor.created_at))
    )
    competitors = result.scalars().all()
    return ResponseBuilder.success([CompetitorResponse.model_validate(c) for c in competitors])


@router.post("/projects/{project_id}/competitors", response_model=dict)
async def create_competitor(
    project_id: str,
    data: CompetitorCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new competitor for a project"""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    competitor = Competitor(
        project_id=project_id,
        created_by=user_id,
        name=data.name,
        description=data.description,
        strengths=data.strengths,
        weaknesses=data.weaknesses,
        features=data.features or [],
        pricing=data.pricing,
        market_position=data.market_position,
        source=data.source,
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)
    return ResponseBuilder.success(CompetitorResponse.model_validate(competitor))


@router.get("/competitors/{competitor_id}", response_model=dict)
async def get_competitor(
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a single competitor"""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.id == competitor_id)
        .join(Project, Competitor.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        return ResponseBuilder.error(code="NOT_FOUND", message="Competitor not found")
    return ResponseBuilder.success(CompetitorResponse.model_validate(competitor))


@router.put("/competitors/{competitor_id}", response_model=dict)
async def update_competitor(
    competitor_id: str,
    data: CompetitorUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a competitor"""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.id == competitor_id)
        .join(Project, Competitor.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        return ResponseBuilder.error(code="NOT_FOUND", message="Competitor not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(competitor, field, value)

    await db.commit()
    await db.refresh(competitor)
    return ResponseBuilder.success(CompetitorResponse.model_validate(competitor))


@router.delete("/competitors/{competitor_id}", response_model=dict)
async def delete_competitor(
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a competitor"""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.id == competitor_id)
        .join(Project, Competitor.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        return ResponseBuilder.error(code="NOT_FOUND", message="Competitor not found")

    await db.delete(competitor)
    await db.commit()
    return ResponseBuilder.success({"deleted": True})
