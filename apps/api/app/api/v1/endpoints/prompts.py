"""Prompt template endpoints for version management"""

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError
from app.services.prompt_service import PromptService

router = APIRouter()


class PromptCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    version: str = Field(default="1.0", min_length=1, max_length=20)
    description: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[List[str]] = Field(default=None)


class PromptUpdateRequest(BaseModel):
    description: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[List[str]] = Field(default=None)


class PromptResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    content: str
    version: str
    is_active: bool
    tags: List[str]
    created_by: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ============== Endpoints ==============

@router.get("", response_model=dict)
async def list_prompts(
    name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List prompt templates with filtering"""
    prompts, total = await PromptService.list_prompts(
        db, name=name, tag=tag, is_active=is_active, page=page, limit=limit
    )
    return ResponseBuilder.paginated(
        data=[p.to_dict() for p in prompts],
        page=page,
        limit=limit,
        total=total,
    )


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new prompt version"""
    prompt = await PromptService.create_prompt(
        db=db,
        name=data.name,
        content=data.content,
        version=data.version,
        description=data.description,
        tags=data.tags,
        user_id=user_id,
    )
    return ResponseBuilder.created(prompt.to_dict())


@router.get("/{prompt_id}", response_model=dict)
async def get_prompt(
    prompt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a single prompt by ID"""
    prompt = await PromptService.get_prompt_by_id(db, prompt_id)
    if not prompt:
        raise ResourceNotFoundError("PromptTemplate", prompt_id)
    return ResponseBuilder.success(prompt.to_dict())


@router.put("/{prompt_id}", response_model=dict)
async def update_prompt(
    prompt_id: str,
    data: PromptUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update mutable fields of a prompt"""
    prompt = await PromptService.update_prompt(
        db, prompt_id, description=data.description, tags=data.tags
    )
    return ResponseBuilder.success(prompt.to_dict())


@router.delete("/{prompt_id}", response_model=dict)
async def delete_prompt(
    prompt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prompt version"""
    await PromptService.delete_prompt(db, prompt_id)
    return ResponseBuilder.no_content("Prompt deleted successfully")


@router.post("/{prompt_id}/activate", response_model=dict)
async def activate_prompt(
    prompt_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Activate a prompt version (deactivates others with same name)"""
    prompt = await PromptService.activate_prompt(db, prompt_id)
    return ResponseBuilder.success(prompt.to_dict())


@router.get("/by-name/{name}/versions", response_model=dict)
async def list_prompt_versions(
    name: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all versions for a given prompt name"""
    versions = await PromptService.list_versions(db, name)
    return ResponseBuilder.success([v.to_dict() for v in versions])
