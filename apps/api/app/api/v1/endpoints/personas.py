"""Persona endpoints for project user profiles"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.persona import Persona
from app.models.project import Project

router = APIRouter()


# ============== Request/Response Models ==============

class PersonaCreate(BaseModel):
    name: str
    role: str
    description: Optional[str] = None
    pain_points: Optional[str] = None
    goals: Optional[str] = None
    scenarios: Optional[str] = None
    demographics: Optional[str] = None


class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    pain_points: Optional[str] = None
    goals: Optional[str] = None
    scenarios: Optional[str] = None
    demographics: Optional[str] = None


class PersonaResponse(BaseModel):
    id: str
    project_id: str
    name: str
    role: str
    description: Optional[str]
    pain_points: Optional[str]
    goals: Optional[str]
    scenarios: Optional[str]
    demographics: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============== Endpoints ==============

@router.get("/projects/{project_id}/personas", response_model=dict)
async def list_personas(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all personas for a project"""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    result = await db.execute(
        select(Persona)
        .where(Persona.project_id == project_id)
        .order_by(desc(Persona.created_at))
    )
    personas = result.scalars().all()
    return ResponseBuilder.success([PersonaResponse.model_validate(p) for p in personas])


@router.post("/projects/{project_id}/personas", response_model=dict)
async def create_persona(
    project_id: str,
    data: PersonaCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new persona for a project"""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    if not proj_result.scalar_one_or_none():
        return ResponseBuilder.error(code="NOT_FOUND", message="Project not found")

    persona = Persona(
        project_id=project_id,
        created_by=user_id,
        name=data.name,
        role=data.role,
        description=data.description,
        pain_points=data.pain_points,
        goals=data.goals,
        scenarios=data.scenarios,
        demographics=data.demographics,
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return ResponseBuilder.success(PersonaResponse.model_validate(persona))


@router.get("/personas/{persona_id}", response_model=dict)
async def get_persona(
    persona_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a single persona"""
    result = await db.execute(
        select(Persona)
        .where(Persona.id == persona_id)
        .join(Project, Persona.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        return ResponseBuilder.error(code="NOT_FOUND", message="Persona not found")
    return ResponseBuilder.success(PersonaResponse.model_validate(persona))


@router.put("/personas/{persona_id}", response_model=dict)
async def update_persona(
    persona_id: str,
    data: PersonaUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a persona"""
    result = await db.execute(
        select(Persona)
        .where(Persona.id == persona_id)
        .join(Project, Persona.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        return ResponseBuilder.error(code="NOT_FOUND", message="Persona not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(persona, field, value)

    await db.commit()
    await db.refresh(persona)
    return ResponseBuilder.success(PersonaResponse.model_validate(persona))


@router.delete("/personas/{persona_id}", response_model=dict)
async def delete_persona(
    persona_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a persona"""
    result = await db.execute(
        select(Persona)
        .where(Persona.id == persona_id)
        .join(Project, Persona.project_id == Project.id)
        .where(Project.created_by == user_id)
    )
    persona = result.scalar_one_or_none()
    if not persona:
        return ResponseBuilder.error(code="NOT_FOUND", message="Persona not found")

    await db.delete(persona)
    await db.commit()
    return ResponseBuilder.success({"deleted": True})
