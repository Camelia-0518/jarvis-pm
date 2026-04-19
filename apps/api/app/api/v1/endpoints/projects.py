"""Project endpoints with standardized responses and pagination"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder, ErrorCode
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError
from app.core.rate_limit import rate_limit
from app.models.project import Project, ProjectStatus
from app.models.prd import PRD

router = APIRouter()


# ============== Request/Response Models ==============

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    industry: str = "other"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    industry: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    industry: str
    status: str
    prd_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    prds: List[dict]


# ============== Helper Functions ==============

async def get_project_with_prd_count(db: AsyncSession, project_id: str, user_id: str) -> Optional[dict]:
    """Get project with PRD count"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        return None

    # Get PRD count
    prd_result = await db.execute(
        select(func.count(PRD.id)).where(PRD.project_id == project.id)
    )
    prd_count = prd_result.scalar()

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "industry": project.industry,
        "status": project.status.value,
        "prd_count": prd_count,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


# ============== Endpoints ==============

@router.get("", response_model=dict)
async def list_projects(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    industry: Optional[str] = Query(None, description="Filter by industry")
):
    """List all projects for current user with pagination and filtering"""
    # Build base query
    query = select(Project).where(
        Project.created_by == user_id,
        Project.status != ProjectStatus.DELETED
    )

    # Apply filters
    if status:
        try:
            status_enum = ProjectStatus(status)
            query = query.where(Project.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    if industry:
        query = query.where(Project.industry == industry)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Apply pagination and ordering
    query = query.order_by(desc(Project.created_at))
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    projects = result.scalars().all()

    # Build response with PRD counts
    project_list = []
    for project in projects:
        prd_result = await db.execute(
            select(func.count(PRD.id)).where(PRD.project_id == project.id)
        )
        prd_count = prd_result.scalar()

        project_list.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "industry": project.industry,
            "status": project.status.value,
            "prd_count": prd_count,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        })

    return ResponseBuilder.paginated(
        data=project_list,
        page=page,
        limit=limit,
        total=total
    )


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
@rate_limit(requests=30, window=60)  # 30 creations per minute
async def create_project(
    project: ProjectCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    # Check for duplicate name
    existing = await db.execute(
        select(Project).where(
            Project.name == project.name,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    if existing.scalar_one_or_none():
        raise ResourceConflictError(
            message=f"Project with name '{project.name}' already exists"
        )

    new_project = Project(
        name=project.name,
        description=project.description,
        industry=project.industry,
        status=ProjectStatus.ACTIVE,
        created_by=user_id,
        settings={}
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return ResponseBuilder.created({
        "id": new_project.id,
        "name": new_project.name,
        "description": new_project.description,
        "industry": new_project.industry,
        "status": new_project.status.value,
        "prd_count": 0,
        "created_at": new_project.created_at,
        "updated_at": new_project.updated_at,
    })


@router.get("/{project_id}", response_model=dict)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get project details with PRDs"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Get project PRDs
    prd_result = await db.execute(
        select(PRD).where(PRD.project_id == project_id).order_by(desc(PRD.created_at))
    )
    prds = prd_result.scalars().all()

    return ResponseBuilder.success({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "industry": project.industry,
        "status": project.status.value,
        "prd_count": len(prds),
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "prds": [
            {
                "id": prd.id,
                "title": prd.title,
                "version": prd.version,
                "status": prd.status.value,
                "created_at": prd.created_at,
            }
            for prd in prds
        ]
    })


@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update project"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Check name uniqueness if updating name
    if project_update.name and project_update.name != project.name:
        existing = await db.execute(
            select(Project).where(
                Project.name == project_update.name,
                Project.created_by == user_id,
                Project.status != ProjectStatus.DELETED,
                Project.id != project_id
            )
        )
        if existing.scalar_one_or_none():
            raise ResourceConflictError(
                message=f"Project with name '{project_update.name}' already exists"
            )
        project.name = project_update.name

    # Update fields
    if project_update.description is not None:
        project.description = project_update.description
    if project_update.industry is not None:
        project.industry = project_update.industry
    if project_update.status is not None:
        try:
            project.status = ProjectStatus(project_update.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {project_update.status}"
            )

    await db.commit()
    await db.refresh(project)

    # Get updated PRD count
    prd_result = await db.execute(
        select(func.count(PRD.id)).where(PRD.project_id == project.id)
    )
    prd_count = prd_result.scalar()

    return ResponseBuilder.success({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "industry": project.industry,
        "status": project.status.value,
        "prd_count": prd_count,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    })


@router.delete("/{project_id}", response_model=dict)
async def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete project (soft delete)"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Soft delete
    project.status = ProjectStatus.DELETED
    await db.commit()

    return ResponseBuilder.no_content("Project deleted successfully")


@router.get("/{project_id}/stats", response_model=dict)
async def get_project_stats(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get project statistics"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Get PRD statistics
    prd_stats = await db.execute(
        select(
            PRD.status,
            func.count(PRD.id).label("count")
        ).where(
            PRD.project_id == project_id
        ).group_by(PRD.status)
    )
    status_counts = {status.value: count for status, count in prd_stats.all()}

    # Get total PRDs
    total_result = await db.execute(
        select(func.count(PRD.id)).where(PRD.project_id == project_id)
    )
    total_prds = total_result.scalar()

    return ResponseBuilder.success({
        "project_id": project_id,
        "total_prds": total_prds,
        "status_breakdown": status_counts,
        "project_status": project.status.value,
        "created_at": project.created_at,
        "updated_at": project.updated_at
    })
