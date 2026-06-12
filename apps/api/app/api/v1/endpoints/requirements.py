"""Requirement endpoints for project backlog and priority matrix"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.requirement import Requirement
from ._crud_helpers import verify_project_owner, get_owned_resource, list_project_resources, apply_update

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

@rate_limit(requests=100, window=60)
@router.get("/projects/{project_id}/requirements", response_model=dict)
async def list_requirements(
    project_id: str,
    sort_by: Optional[str] = "created_at",
    order: Optional[str] = "desc",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all requirements for a project"""
    items, schema = await list_project_resources(
        db, Requirement, project_id, user_id, RequirementResponse,
        sort_by=sort_by, sort_order=order,
    )
    return ResponseBuilder.success([schema.model_validate(r) for r in items])


@rate_limit(requests=30, window=60)
@router.post("/projects/{project_id}/requirements", response_model=dict)
async def create_requirement(
    project_id: str,
    data: RequirementCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new requirement for a project"""
    await verify_project_owner(db, project_id, user_id)
    req = Requirement(project_id=project_id, created_by=user_id, **data.model_dump())
    req.rice_score = _calc_rice_score(req)
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return ResponseBuilder.success(RequirementResponse.model_validate(req))


@rate_limit(requests=100, window=60)
@router.get("/requirements/{req_id}", response_model=dict)
async def get_requirement(
    req_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a single requirement"""
    req = await get_owned_resource(db, Requirement, req_id, user_id)
    return ResponseBuilder.success(RequirementResponse.model_validate(req))


@rate_limit(requests=30, window=60)
@router.put("/requirements/{req_id}", response_model=dict)
async def update_requirement(
    req_id: str,
    data: RequirementUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a requirement"""
    req = await get_owned_resource(db, Requirement, req_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(req, field, value)
    req.rice_score = _calc_rice_score(req)
    await db.commit()
    await db.refresh(req)
    return ResponseBuilder.success(RequirementResponse.model_validate(req))


@rate_limit(requests=20, window=60)
@router.delete("/requirements/{req_id}", response_model=dict)
async def delete_requirement(
    req_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a requirement"""
    req = await get_owned_resource(db, Requirement, req_id, user_id)
    req.soft_delete()
    await db.commit()
    return ResponseBuilder.success({"deleted": True})


@rate_limit(requests=100, window=60)
@router.get("/projects/{project_id}/requirements/priority-matrix", response_model=dict)
async def get_priority_matrix(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get priority matrix summary (RICE + Kano)"""
    await verify_project_owner(db, project_id, user_id)

    result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id, Requirement.deleted_at.is_(None))
    )
    reqs = result.scalars().all()

    # RICE sorted
    rice_sorted = sorted(reqs, key=lambda r: r.rice_score, reverse=True)

    # Kano grouped
    kano_groups: Dict[str, List[Dict[str, Any]]] = {"must_be": [], "one_dimensional": [], "attractive": [], "indifferent": [], "reverse": [], "": []}
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
