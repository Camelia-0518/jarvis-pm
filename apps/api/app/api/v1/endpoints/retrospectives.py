"""Retrospective API endpoints

CRUD for project retrospectives + AI-assisted analysis.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.core.exceptions import AppException
from app.models.retrospective import Retrospective
from ._crud_helpers import verify_project_owner, get_owned_resource

router = APIRouter()


class RetrospectiveCreate(BaseModel):
    project_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    what_went_well: str = ""
    what_went_wrong: str = ""
    surprises: str = ""
    key_decisions: List[Dict[str, Any]] = Field(default_factory=list)
    planned_days: Optional[float] = None
    actual_days: Optional[float] = None
    planned_budget: Optional[float] = None
    actual_budget: Optional[float] = None


class RetrospectiveUpdate(BaseModel):
    title: Optional[str] = None
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    surprises: Optional[str] = None
    key_decisions: Optional[List[Dict[str, Any]]] = None
    planned_days: Optional[float] = None
    actual_days: Optional[float] = None
    planned_budget: Optional[float] = None
    actual_budget: Optional[float] = None


class AIRetrospectiveRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    title: str = Field(default="项目复盘")
    what_went_well: str = ""
    what_went_wrong: str = ""
    surprises: str = ""
    prd_content: str = ""
    delivery_data: Dict[str, Any] = Field(default_factory=dict)


@rate_limit(requests=30, window=60)
@router.get("", response_model=dict)
async def list_retrospectives(
    project_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List retrospectives, optionally filtered by project"""
    query = select(Retrospective).where(Retrospective.deleted_at.is_(None))
    if project_id:
        await verify_project_owner(db, project_id, user_id)
        query = query.where(Retrospective.project_id == project_id)
    query = query.order_by(Retrospective.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    result = await db.execute(query.offset(offset).limit(limit))
    items = result.scalars().all()

    return ResponseBuilder.paginated(
        data=[{
            "id": r.id,
            "project_id": r.project_id,
            "title": r.title,
            "planned_days": r.planned_days,
            "actual_days": r.actual_days,
            "lessons": r.lessons,
            "ai_analysis": r.ai_analysis,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in items],
        page=offset // limit + 1,
        limit=limit,
        total=total,
    )


@rate_limit(requests=30, window=60)
@router.get("/{retro_id}", response_model=dict)
async def get_retrospective(
    retro_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get retrospective detail"""
    retro = await get_owned_resource(db, Retrospective, retro_id, user_id)

    return ResponseBuilder.success({
        "id": retro.id,
        "project_id": retro.project_id,
        "title": retro.title,
        "what_went_well": retro.what_went_well,
        "what_went_wrong": retro.what_went_wrong,
        "surprises": retro.surprises,
        "key_decisions": retro.key_decisions,
        "planned_days": retro.planned_days,
        "actual_days": retro.actual_days,
        "planned_budget": retro.planned_budget,
        "actual_budget": retro.actual_budget,
        "lessons": retro.lessons,
        "ai_analysis": retro.ai_analysis,
        "ai_suggestions": retro.ai_suggestions,
        "created_at": retro.created_at.isoformat() if retro.created_at else None,
    })


@rate_limit(requests=20, window=60)
@router.post("", response_model=dict)
async def create_retrospective(
    request: RetrospectiveCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new retrospective record"""
    await verify_project_owner(db, request.project_id, user_id)

    retro = Retrospective(created_by=user_id, **request.model_dump())
    db.add(retro)
    await db.commit()
    await db.refresh(retro)

    return ResponseBuilder.success({"id": retro.id, "title": retro.title}, message="复盘记录已创建")


@rate_limit(requests=20, window=60)
@router.put("/{retro_id}", response_model=dict)
async def update_retrospective(
    retro_id: str,
    request: RetrospectiveUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update retrospective"""
    retro = await get_owned_resource(db, Retrospective, retro_id, user_id)

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(retro, field, value)

    await db.commit()
    return ResponseBuilder.success(None, message="复盘记录已更新")


@rate_limit(requests=10, window=60)
@router.post("/{retro_id}/ai-analyze", response_model=dict)
async def ai_analyze_retrospective(
    retro_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Run AI analysis on a retrospective"""
    retro = await get_owned_resource(db, Retrospective, retro_id, user_id)

    from app.agents.agents.retrospective_agent import RetrospectiveAgent
    agent = RetrospectiveAgent()

    result = await agent.execute({
        "project_name": retro.title,
        "what_went_well": retro.what_went_well,
        "what_went_wrong": retro.what_went_wrong,
        "surprises": retro.surprises,
        "prd_content": "",
        "delivery_data": {},
    })

    if result.success:
        retro.lessons = result.data.get("lessons", [])
        retro.ai_analysis = result.data.get("summary", "")
        retro.ai_suggestions = result.data.get("action_items", [])
        await db.commit()

    return ResponseBuilder.success(result.data)


@rate_limit(requests=10, window=60)
@router.delete("/{retro_id}", response_model=dict)
async def delete_retrospective(
    retro_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Soft-delete retrospective"""
    retro = await get_owned_resource(db, Retrospective, retro_id, user_id)
    retro.soft_delete()
    await db.commit()
    return ResponseBuilder.success(None, message="复盘记录已删除")
