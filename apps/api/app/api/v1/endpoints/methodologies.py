"""Delivery methodology endpoints"""

from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.exceptions import ResourceNotFoundError
from app.models.delivery_methodology import DeliveryMethodology

router = APIRouter()


class MethodologyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    industry: str = "general"
    stages: Optional[List[dict]] = None
    best_practices: Optional[List[str]] = None
    pitfalls: Optional[List[str]] = None
    templates: Optional[List[dict]] = None


class MethodologyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    stages: Optional[List[dict]] = None
    best_practices: Optional[List[str]] = None
    pitfalls: Optional[List[str]] = None
    templates: Optional[List[dict]] = None


@router.get("", response_model=dict)
async def list_methodologies(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    industry: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List delivery methodologies"""
    query = select(DeliveryMethodology).where(DeliveryMethodology.deleted_at.is_(None))

    if industry:
        query = query.where(DeliveryMethodology.industry == industry)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    offset = (page - 1) * limit
    result = await db.execute(query.order_by(desc(DeliveryMethodology.created_at)).offset(offset).limit(limit))
    items = result.scalars().all()

    return ResponseBuilder.paginated(
        data=[{
            "id": m.id, "name": m.name, "description": m.description,
            "industry": m.industry, "stages": m.stages,
            "best_practices": m.best_practices, "pitfalls": m.pitfalls,
            "templates": m.templates, "created_at": m.created_at,
            "updated_at": m.updated_at,
        } for m in items],
        page=page, limit=limit, total=total
    )


@router.get("/{methodology_id}", response_model=dict)
async def get_methodology(
    methodology_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get methodology detail"""
    result = await db.execute(
        select(DeliveryMethodology).where(
            DeliveryMethodology.id == methodology_id,
            DeliveryMethodology.deleted_at.is_(None),
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise ResourceNotFoundError("Methodology", methodology_id)

    return ResponseBuilder.success({
        "id": m.id, "name": m.name, "description": m.description,
        "industry": m.industry, "stages": m.stages,
        "best_practices": m.best_practices, "pitfalls": m.pitfalls,
        "templates": m.templates, "created_at": m.created_at,
        "updated_at": m.updated_at,
    })


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_methodology(
    req: MethodologyCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create delivery methodology"""
    m = DeliveryMethodology(
        name=req.name, description=req.description or "",
        industry=req.industry, stages=req.stages or [],
        best_practices=req.best_practices or [],
        pitfalls=req.pitfalls or [],
        templates=req.templates or [],
        created_by=user_id,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return ResponseBuilder.created({
        "id": m.id, "name": m.name, "description": m.description,
        "industry": m.industry, "stages": m.stages,
        "best_practices": m.best_practices,
        "pitfalls": m.pitfalls, "templates": m.templates,
        "created_at": m.created_at,
    })


@router.put("/{methodology_id}", response_model=dict)
async def update_methodology(
    methodology_id: str,
    req: MethodologyUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update delivery methodology"""
    result = await db.execute(
        select(DeliveryMethodology).where(
            DeliveryMethodology.id == methodology_id,
            DeliveryMethodology.deleted_at.is_(None),
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise ResourceNotFoundError("Methodology", methodology_id)

    for field in ["name", "description", "industry", "stages", "best_practices", "pitfalls", "templates"]:
        val = getattr(req, field, None)
        if val is not None:
            setattr(m, field, val)

    await db.commit()
    await db.refresh(m)
    return ResponseBuilder.success({
        "id": m.id, "name": m.name, "updated_at": m.updated_at,
    })


@router.delete("/{methodology_id}", response_model=dict)
async def delete_methodology(
    methodology_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete methodology"""
    result = await db.execute(
        select(DeliveryMethodology).where(
            DeliveryMethodology.id == methodology_id,
            DeliveryMethodology.deleted_at.is_(None),
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        raise ResourceNotFoundError("Methodology", methodology_id)

    m.soft_delete()
    await db.commit()
    return ResponseBuilder.no_content("Methodology deleted")
