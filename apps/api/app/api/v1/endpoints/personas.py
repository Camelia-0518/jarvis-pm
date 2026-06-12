"""Persona endpoints for project user profiles"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.persona import Persona
from app.core.exceptions import AppException
from ._crud_helpers import verify_project_owner, get_owned_resource, list_project_resources, apply_update

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

@rate_limit(requests=100, window=60)
@router.get("/projects/{project_id}/personas", response_model=dict)
async def list_personas(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List all personas for a project"""
    items, schema = await list_project_resources(db, Persona, project_id, user_id, PersonaResponse)
    return ResponseBuilder.success([schema.model_validate(p) for p in items])


@rate_limit(requests=30, window=60)
@router.post("/projects/{project_id}/personas", response_model=dict)
async def create_persona(
    project_id: str,
    data: PersonaCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new persona for a project"""
    await verify_project_owner(db, project_id, user_id)

    persona = Persona(project_id=project_id, created_by=user_id, **data.model_dump())
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return ResponseBuilder.success(PersonaResponse.model_validate(persona))


@rate_limit(requests=100, window=60)
@router.get("/personas/{persona_id}", response_model=dict)
async def get_persona(
    persona_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get a single persona"""
    persona = await get_owned_resource(db, Persona, persona_id, user_id)
    return ResponseBuilder.success(PersonaResponse.model_validate(persona))


@rate_limit(requests=30, window=60)
@router.put("/personas/{persona_id}", response_model=dict)
async def update_persona(
    persona_id: str,
    data: PersonaUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update a persona"""
    persona = await get_owned_resource(db, Persona, persona_id, user_id)
    await apply_update(db, persona, data)
    return ResponseBuilder.success(PersonaResponse.model_validate(persona))


@rate_limit(requests=20, window=60)
@router.delete("/personas/{persona_id}", response_model=dict)
async def delete_persona(
    persona_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete a persona"""
    persona = await get_owned_resource(db, Persona, persona_id, user_id)
    persona.soft_delete()
    await db.commit()
    return ResponseBuilder.success({"deleted": True})
