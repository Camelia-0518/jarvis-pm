"""Requirement endpoints for project backlog and priority matrix"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.requirement import Requirement
from app.models.project import Project

router = APIRouter()


# ============== Request/Response Models ==============

class RequirementCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "backlog"
    priority: Optional[str] = "p1"
    rice_reach: Optional[int] = Field(default=0, ge=0, le=1000)
    rice_impact: Optional[float] = Field(default=0.0)
    rice_confidence: Optional[int] = Field(default=0, ge=0, le=100)
    rice_effort: Optional[float] = Field(default=0.0, ge=0)
    kano_category: Optional[str] = ""


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    rice_reach: Optional[int] = Field(default=None, ge=0, le=1000)
    rice_impact: Optional[float] = None
    rice_confidence: Optional[int] = Field(default=None, ge=0, le=100)
    rice_effort: Optional[float] = Field(default=None, ge=0)
    kano_category: Optional[str] = None


class RequirementResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    rice_reach: int
    rice_impact: float
    rice_confidence: int
    rice_effort: float
    rice_score: float
    kano_category: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _calc_rice_score(r: Requirement) -> float:
    if r.rice_effort <= 0:
        return 0.0
    return round(r.rice_reach * r.rice_impact * (r.rice_confidence / 100) / r.rice_effort, 2)


# ============== Endpoints ==============

@router.get("/projects/{project_id}/requirements", response_model=dict)
async def list_requirements(
    project_id: str,
    sort_by: Optional[str] = "created_at",
    order: Optional[str] = "desc",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all requirements for a project"""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    query = select(Requirement).where(Requirement.project_id == project_id)

    if sort_by == "rice_score":
        query = query.order_by(desc(Requirement.rice_score) if order == "desc" else asc(Requirement.rice_score))
    elif sort_by == "priority":
        query = query.order_by(desc(Requirement.priority) if order == "desc" else asc(Requirement.priority))
    else:
        query = query.order_by(desc(Requirement.created_at) if order == "desc" else asc(Requirement.created_at))

    result = await db.execute(query)
    reqs = result.scalars().all()
    return ResponseBuilder.success([RequirementResponse.model_validate(r) for r in reqs])


@router.post("/projects/{project_id}/requirements", response_model=dict)
async def create_requirement(
    project_id: str,
    data: RequirementCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new requirement for a project"""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    req = Requirement(
        project_id=project_id,
        created_by=user_id,
        title=data.title,
        description=data.description,
        status=data.status or "backlog",
        priority=data.priority or "p1",
        rice_reach=data.rice_reach or 0,
        rice_impact=data.rice_impact or 0.0,
        rice_confidence=data.rice_confidence or 0,
        rice_effort=data.rice_effort or 0.0,
        kano_category=data.kano_category or "",
    )
    req.rice_score = _calc_rice_score(req)
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return ResponseBuilder.success(RequirementResponse.model_validate(req))


@router.get("/requirements/{req_id}", response_model=dict)
async def get_requirement(
    req_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a single requirement"""
    result = await db.execute(
        select(Requirement)
        .where(Requirement.id == req_id)
        .join(Project, Requirement.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        return ResponseBuilder.error(code="NOT_FOUND", message="Requirement not found")
    return ResponseBuilder.success(RequirementResponse.model_validate(req))


@router.put("/requirements/{req_id}", response_model=dict)
async def update_requirement(
    req_id: str,
    data: RequirementUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a requirement"""
    result = await db.execute(
        select(Requirement)
        .where(Requirement.id == req_id)
        .join(Project, Requirement.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        return ResponseBuilder.error(code="NOT_FOUND", message="Requirement not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(req, field, value)

    req.rice_score = _calc_rice_score(req)
    await db.commit()
    await db.refresh(req)
    return ResponseBuilder.success(RequirementResponse.model_validate(req))


@router.delete("/requirements/{req_id}", response_model=dict)
async def delete_requirement(
    req_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a requirement"""
    result = await db.execute(
        select(Requirement)
        .where(Requirement.id == req_id)
        .join(Project, Requirement.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        return ResponseBuilder.error(code="NOT_FOUND", message="Requirement not found")

    await db.delete(req)
    await db.commit()
    return ResponseBuilder.success({"deleted": True})


@router.get("/projects/{project_id}/requirements/priority-matrix", response_model=dict)
async def get_priority_matrix(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get priority matrix summary (RICE + Kano)"""
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id)
    )
    reqs = result.scalars().all()

    # RICE sorted
    rice_sorted = sorted(reqs, key=lambda r: r.rice_score, reverse=True)

    # Kano grouped
    kano_groups: dict[str, list] = {"must_be": [], "one_dimensional": [], "attractive": [], "indifferent": [], "reverse": [], "": []}
    for r in reqs:
        cat = r.kano_category or ""
        if cat in kano_groups:
            kano_groups[cat].append(RequirementResponse.model_validate(r).model_dump())

    return ResponseBuilder.success({
        "total": len(reqs),
        "rice_top": [RequirementResponse.model_validate(r).model_dump() for r in rice_sorted[:10]],
        "kano_distribution": {k: len(v) for k, v in kano_groups.items()},
        "kano_groups": {k: v for k, v in kano_groups.items() if v},
    })
