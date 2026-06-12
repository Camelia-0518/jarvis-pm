"""Project endpoints with standardized responses and pagination"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError
from app.core.rate_limit import rate_limit
from app.core.permissions import require_project_owner
from app.models.project import Project, ProjectStatus
from app.models.audit_log import AuditLog
from app.models.state_machine import project_sm
from app.models.prd import PRD
from app.models.delivery_plan import DeliveryPlan
from app.models.prd_annotation import PRDAnnotation

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
        select(func.count(PRD.id)).where(PRD.project_id == project.id, PRD.deleted_at.is_(None))
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

@rate_limit(requests=100, window=60)
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

    # Get all PRD counts in a single query to avoid N+1
    project_ids = [p.id for p in projects]
    prd_counts_result = await db.execute(
        select(PRD.project_id, func.count(PRD.id))
        .where(PRD.project_id.in_(project_ids), PRD.deleted_at.is_(None))
        .group_by(PRD.project_id)
    )
    prd_counts = {pid: count for pid, count in prd_counts_result.all()}

    # Build response with PRD counts
    project_list = []
    for project in projects:
        project_list.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "industry": project.industry,
            "status": project.status.value,
            "prd_count": prd_counts.get(project.id, 0),
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        })

    return ResponseBuilder.paginated(
        data=project_list,
        page=page,
        limit=limit,
        total=total
    )


@rate_limit(requests=30, window=60)  # 30 creations per minute
@router.post("", status_code=status.HTTP_201_CREATED)
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

    # Audit log
    db.add(AuditLog(
        user_id=user_id,
        workspace_id=getattr(new_project, "workspace_id", None),
        action="create",
        resource_type="project",
        resource_id=new_project.id,
        summary=f"创建了项目 {new_project.name}",
    ))
    await db.commit()

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


@router.get("/projects-health-check", response_model=dict)
async def get_projects_health(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get health status for all projects with risk scoring and AI bottleneck detection"""
    result = await db.execute(
        select(Project).where(
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        ).order_by(desc(Project.created_at))
    )
    projects = result.scalars().all()

    health_items = []
    for p in projects:
        prd_result = await db.execute(
            select(PRD.status, func.count(PRD.id))
            .where(PRD.project_id == p.id, PRD.deleted_at.is_(None))
            .group_by(PRD.status)
        )
        prd_statuses = {s.value: c for s, c in prd_result.all()}
        total_prds = sum(prd_statuses.values())
        published_prds = prd_statuses.get("published", 0) + prd_statuses.get("approved", 0)

        delivery_result = await db.execute(
            select(DeliveryPlan).where(
                DeliveryPlan.project_id == p.id,
                DeliveryPlan.deleted_at.is_(None)
            ).order_by(desc(DeliveryPlan.created_at)).limit(1)
        )
        delivery = delivery_result.scalar_one_or_none()

        prd_score = min(published_prds * 30, 60) if total_prds > 0 else 10
        delivery_score = 0
        if delivery:
            status_map = {"completed": 40, "in_progress": 25, "draft": 15, "at_risk": 5, "cancelled": 0}
            delivery_score = status_map.get(
                delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status), 15
            )

        recency_score = 10
        days_since_update = None
        if p.updated_at:
            pt = p.updated_at.replace(tzinfo=None) if p.updated_at.tzinfo else p.updated_at
            delta = datetime.now().replace(tzinfo=None) - pt
            if delta:
                days_since_update = delta.days
                if days_since_update < 7:
                    recency_score = 20
                elif days_since_update < 30:
                    recency_score = 10
                else:
                    recency_score = 5

        health_score = prd_score + delivery_score + recency_score

        if health_score >= 70:
            risk_level = "on_track"
        elif health_score >= 40:
            risk_level = "at_risk"
        else:
            risk_level = "critical"

        bottlenecks = []
        if total_prds == 0:
            bottlenecks.append({"type": "no_prd", "message": "尚未创建 PRD 文档，建议立即启动需求分析", "severity": "high"})
        if published_prds == 0 and total_prds > 0:
            bottlenecks.append({"type": "all_draft", "message": "所有 PRD 仍为草稿状态，建议推进评审流程", "severity": "medium"})
        if not delivery:
            bottlenecks.append({"type": "no_delivery", "message": "尚未创建交付计划，建议从 PRD 生成交付方案", "severity": "high"})
        elif delivery and (delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status)) == "at_risk":
            bottlenecks.append({"type": "delivery_at_risk", "message": "交付计划存在风险，请检查风险矩阵并制定应对措施", "severity": "critical"})
        if days_since_update and days_since_update > 30:
            bottlenecks.append({"type": "stale", "message": f"项目 {days_since_update} 天未更新，可能存在停滞风险", "severity": "medium"})

        health_items.append({
            "project_id": p.id,
            "project_name": p.name,
            "industry": p.industry,
            "health_score": health_score,
            "risk_level": risk_level,
            "metrics": {
                "total_prds": total_prds,
                "published_prds": published_prds,
                "draft_prds": prd_statuses.get("draft", 0),
                "has_delivery_plan": delivery is not None,
                "delivery_status": (
                    delivery.status.value if delivery and hasattr(delivery.status, 'value')
                    else (str(delivery.status) if delivery else None)
                ),
                "days_since_update": days_since_update,
            },
            "bottlenecks": bottlenecks,
        })

    total = len(health_items)
    on_track = sum(1 for h in health_items if h["risk_level"] == "on_track")
    at_risk = sum(1 for h in health_items if h["risk_level"] == "at_risk")
    critical = sum(1 for h in health_items if h["risk_level"] == "critical")
    avg_score = round(sum(h["health_score"] for h in health_items) / total, 1) if total > 0 else 0

    return ResponseBuilder.success({
        "summary": {
            "total_projects": total,
            "on_track": on_track,
            "at_risk": at_risk,
            "critical": critical,
            "average_health_score": avg_score,
        },
        "projects": health_items,
    })


@rate_limit(requests=30, window=60)
@router.get("/{project_id}/health", response_model=dict)
async def get_project_health(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed health status for a single project with actionable insights"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
            Project.status != ProjectStatus.DELETED
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # PRD metrics
    prd_result = await db.execute(
        select(PRD.status, func.count(PRD.id))
        .where(PRD.project_id == project_id, PRD.deleted_at.is_(None))
        .group_by(PRD.status)
    )
    prd_statuses = {s.value: c for s, c in prd_result.all()}
    total_prds = sum(prd_statuses.values())

    # Latest delivery plan
    delivery_result = await db.execute(
        select(DeliveryPlan).where(
            DeliveryPlan.project_id == project_id,
            DeliveryPlan.deleted_at.is_(None)
        ).order_by(desc(DeliveryPlan.created_at)).limit(1)
    )
    delivery = delivery_result.scalar_one_or_none()

    # Annotation metrics
    ann_result = await db.execute(
        select(PRDAnnotation.annotation_type, PRDAnnotation.status, func.count(PRDAnnotation.id))
        .where(PRDAnnotation.prd_id.in_(
            select(PRD.id).where(PRD.project_id == project_id, PRD.deleted_at.is_(None))
        ))
        .group_by(PRDAnnotation.annotation_type, PRDAnnotation.status)
    )
    ann_data = ann_result.all()
    open_issues = sum(c for t, s, c in ann_data if s == "open")
    total_annotations = sum(c for _, _, c in ann_data)
    resolved_rate = round((total_annotations - open_issues) / total_annotations * 100, 1) if total_annotations > 0 else 100

    # Schedule metrics
    milestone_count = 0
    completed_milestones = 0
    if delivery and delivery.milestones:
        milestones = delivery.milestones if isinstance(delivery.milestones, list) else delivery.milestones.get("phases", [])
        if isinstance(milestones, list):
            milestone_count = len(milestones)
            completed_milestones = sum(1 for m in (milestones or []) if isinstance(m, dict) and m.get("status") == "completed")

    # Risk metrics
    active_risks_count = 0
    high_risk_count = 0
    if delivery and delivery.risks:
        risks = delivery.risks if isinstance(delivery.risks, list) else []
        active_risks_count = len(risks)
        high_risk_count = sum(1 for r in risks if isinstance(r, dict) and r.get("level") in ("high", "critical"))

    # Health score calculation (0-100)
    prd_score = min(total_prds * 10, 30) if total_prds > 0 else 0
    pub_bonus = min((prd_statuses.get("published", 0) + prd_statuses.get("approved", 0)) * 10, 15)
    delivery_score = 0
    if delivery:
        d_status = delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status)
        delivery_score = {"completed": 20, "in_progress": 15, "draft": 10, "at_risk": 3, "cancelled": 0}.get(d_status, 10)
    milestone_score = (5 + min(int(completed_milestones / milestone_count * 10), 10)) if milestone_count > 0 else 0
    quality_score = min(int(resolved_rate / 100 * 10), 10)
    risk_penalty = min(high_risk_count * 5 + active_risks_count * 2, 20)

    days_since_update = None
    if project.updated_at:
        dt = datetime.now().replace(tzinfo=None)
        pt = project.updated_at.replace(tzinfo=None) if project.updated_at.tzinfo else project.updated_at
        days_since_update = (dt - pt).days if pt else None
    recency_score = 15 if days_since_update is None else (15 if days_since_update < 7 else (10 if days_since_update < 30 else 5))

    health_score = min(prd_score + pub_bonus + delivery_score + milestone_score + quality_score + recency_score - risk_penalty, 100)
    health_score = max(health_score, 0)

    if health_score >= 70:
        risk_level = "on_track"
    elif health_score >= 40:
        risk_level = "at_risk"
    else:
        risk_level = "critical"

    # Bottleneck identification
    bottlenecks = []
    if total_prds == 0:
        bottlenecks.append({"type": "no_prd", "message": "尚未创建 PRD，建议使用「完整交付方案」或「快速PRD」启动", "severity": "high", "action": "trigger_full_delivery"})
    if not delivery:
        bottlenecks.append({"type": "no_plan", "message": "尚未创建交付计划，建议从 PRD 生成交付方案", "severity": "high", "action": "trigger_full_delivery"})
    if milestone_count > 0 and completed_milestones / milestone_count < 0.3:
        bottlenecks.append({"type": "slow_progress", "message": f"里程碑进度滞后（{completed_milestones}/{milestone_count}），建议检查阻塞因素", "severity": "critical" if milestone_count > 0 else "medium"})
    if open_issues > 5:
        bottlenecks.append({"type": "issues_backlog", "message": f"有 {open_issues} 个待解决问题积压，建议评审排期", "severity": "high"})
    if high_risk_count > 2:
        bottlenecks.append({"type": "high_risk", "message": f"存在 {high_risk_count} 个高/严重风险，建议立即制定应对措施", "severity": "critical"})
    if days_since_update and days_since_update > 30:
        bottlenecks.append({"type": "stale", "message": f"项目 {days_since_update} 天未更新，可能存在停滞风险", "severity": "medium"})

    return ResponseBuilder.success({
        "project_id": project.id,
        "project_name": project.name,
        "health_score": health_score,
        "risk_level": risk_level,
        "score_breakdown": {
            "prd_score": prd_score,
            "publish_bonus": pub_bonus,
            "delivery_score": delivery_score,
            "milestone_score": milestone_score,
            "quality_score": quality_score,
            "recency_score": recency_score,
            "risk_penalty": -risk_penalty,
        },
        "metrics": {
            "total_prds": total_prds,
            "published_prds": prd_statuses.get("published", 0) + prd_statuses.get("approved", 0),
            "draft_prds": prd_statuses.get("draft", 0),
            "milestones_total": milestone_count,
            "milestones_completed": completed_milestones,
            "milestone_progress_pct": round(completed_milestones / milestone_count * 100, 1) if milestone_count > 0 else 0,
            "open_issues": open_issues,
            "total_annotations": total_annotations,
            "issue_resolution_rate": resolved_rate,
            "active_risks": active_risks_count,
            "high_risks": high_risk_count,
            "days_since_update": days_since_update,
        },
        "bottlenecks": bottlenecks,
    })


@rate_limit(requests=100, window=60)
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
        select(PRD).where(PRD.project_id == project_id, PRD.deleted_at.is_(None)).order_by(desc(PRD.created_at))
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


@rate_limit(requests=30, window=60)
@router.put("/{project_id}", response_model=dict)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update project (including restoring deleted projects via status change)"""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.created_by == user_id,
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
        project_sm.transition(project, project_update.status)

    await db.commit()
    await db.refresh(project)

    # Get updated PRD count
    prd_result = await db.execute(
        select(func.count(PRD.id)).where(PRD.project_id == project.id, PRD.deleted_at.is_(None))
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


@rate_limit(requests=20, window=60)
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
    project_sm.transition(project, "deleted")
    await db.commit()

    return ResponseBuilder.no_content("Project deleted successfully")


@rate_limit(requests=100, window=60)
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
            PRD.project_id == project_id,
            PRD.deleted_at.is_(None),
        ).group_by(PRD.status)
    )
    status_counts = {status.value: count for status, count in prd_stats.all()}

    # Get total PRDs
    total_result = await db.execute(
        select(func.count(PRD.id)).where(PRD.project_id == project_id, PRD.deleted_at.is_(None))
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