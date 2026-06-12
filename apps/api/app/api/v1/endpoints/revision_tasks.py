"""PRD revision task endpoints — 批注驱动的修改任务闭环"""

import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.sql import func as sql_func

from app.core.database import get_db, AsyncSessionLocal
from app.core.rate_limit import rate_limit
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.core.exceptions import AppException
from app.models.prd_revision_task import PRDRevisionTask, TaskStatus
from app.models.prd_annotation import PRDAnnotation, AnnotationStatus
from app.models.prd import PRD
from app.models.state_machine import task_sm
from app.core.permissions import require_resource_owner

logger = logging.getLogger(__name__)

router = APIRouter()


# ============== Request/Response Models ==============

class RevisionTaskCreate(BaseModel):
    annotation_id: str = Field(..., description="关联的批注ID")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    assigned_to: Optional[str] = None


class RevisionTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done|cancelled)$")
    assigned_to: Optional[str] = None


class RevisionTaskComplete(BaseModel):
    completion_note: str = Field(..., min_length=1, max_length=2000, description="修改说明")
    trigger_re_review: bool = Field(False, description="是否触发再评审")


# ============== Endpoints ==============

@rate_limit(requests=30, window=60)
@router.post("", response_model=dict, status_code=201)
async def create_task(
    prd_id: str,
    request: RevisionTaskCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """从批注创建修改任务"""
    # 验证批注存在
    ann_result = await db.execute(
        select(PRDAnnotation).where(
            PRDAnnotation.id == request.annotation_id,
            PRDAnnotation.prd_id == prd_id,
            PRDAnnotation.deleted_at.is_(None),
        )
    )
    annotation = ann_result.scalar_one_or_none()
    if not annotation:
        raise AppException("批注不存在", code="NOT_FOUND", status_code=404)

    # 创建任务
    task = PRDRevisionTask(
        prd_id=prd_id,
        annotation_id=request.annotation_id,
        title=request.title,
        description=request.description or annotation.content,
        assigned_to=request.assigned_to or user_id,
        created_by=user_id,
        status=TaskStatus.TODO,
    )
    db.add(task)

    # 更新批注关联
    annotation.revision_task_id = task.id

    await db.commit()
    await db.refresh(task)

    return ResponseBuilder.created({
        "id": task.id,
        "prd_id": task.prd_id,
        "annotation_id": task.annotation_id,
        "title": task.title,
        "status": task.status,
        "message": "修改任务已创建"
    })


@rate_limit(requests=100, window=60)
@router.get("", response_model=dict)
async def list_tasks(
    prd_id: str,
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取 PRD 的修改任务列表"""
    await require_resource_owner(db, PRD, prd_id, user_id)
    query = select(PRDRevisionTask).where(
        PRDRevisionTask.prd_id == prd_id,
        PRDRevisionTask.deleted_at.is_(None),
    ).order_by(desc(PRDRevisionTask.created_at))

    if status:
        query = query.where(PRDRevisionTask.status == status)

    result = await db.execute(query)
    items = result.scalars().all()

    return ResponseBuilder.success([{
        "id": t.id,
        "prd_id": t.prd_id,
        "annotation_id": t.annotation_id,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "assigned_to": t.assigned_to,
        "created_by": t.created_by,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "completion_note": t.completion_note,
        "re_review_status": t.re_review_status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    } for t in items])


@rate_limit(requests=30, window=60)
@router.put("/{task_id}", response_model=dict)
async def update_task(
    prd_id: str,
    task_id: str,
    request: RevisionTaskUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新修改任务（状态、负责人、内容）"""
    await require_resource_owner(db, PRD, prd_id, user_id)
    result = await db.execute(
        select(PRDRevisionTask).where(
            PRDRevisionTask.id == task_id,
            PRDRevisionTask.prd_id == prd_id,
            PRDRevisionTask.deleted_at.is_(None),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise AppException("任务不存在", code="NOT_FOUND", status_code=404)

    if request.title is not None:
        task.title = request.title
    if request.description is not None:
        task.description = request.description
    if request.status is not None:
        task_sm.transition(task, request.status)
    if request.assigned_to is not None:
        task.assigned_to = request.assigned_to

    await db.commit()
    await db.refresh(task)

    return ResponseBuilder.success({
        "id": task.id,
        "status": task.status,
        "message": "任务已更新"
    })


@rate_limit(requests=30, window=60)
@router.post("/{task_id}/complete", response_model=dict)
async def complete_task(
    prd_id: str,
    task_id: str,
    request: RevisionTaskComplete,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """完成任务 + 可选触发再评审"""
    await require_resource_owner(db, PRD, prd_id, user_id)
    result = await db.execute(
        select(PRDRevisionTask).where(
            PRDRevisionTask.id == task_id,
            PRDRevisionTask.prd_id == prd_id,
            PRDRevisionTask.deleted_at.is_(None),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise AppException("任务不存在", code="NOT_FOUND", status_code=404)

    # 更新任务状态
    task_sm.transition(task, "done")
    task.completed_at = sql_func.now()
    task.completion_note = request.completion_note

    # 同时解决关联的批注
    if task.annotation_id:
        ann_result = await db.execute(
            select(PRDAnnotation).where(PRDAnnotation.id == task.annotation_id, PRDAnnotation.deleted_at.is_(None))
        )
        annotation = ann_result.scalar_one_or_none()
        if annotation:
            annotation.status = AnnotationStatus.RESOLVED
            annotation.resolved_at = sql_func.now()
            annotation.resolved_by = user_id

    await db.commit()
    await db.refresh(task)

    # Trigger re-review: run compliance check as background task
    if request.trigger_re_review:
        task.re_review_status = "pending"
        await db.commit()
        # Create Job and enqueue for async re-review execution
        from app.models.job import Job, JobType, JobStatus
        from app.services.job_runner import enqueue_job
        prd = await db.get(PRD, prd_id)
        re_review_job = Job(
            job_type=JobType.RE_REVIEW,
            status=JobStatus.QUEUED,
            project_id=prd.project_id if prd else None,
            prd_id=prd_id,
            task_id=task.id,
            triggered_by=user_id,
            input_data={"prd_title": prd.title if prd else ""},
        )
        db.add(re_review_job)
        await db.commit()
        await db.refresh(re_review_job)
        await enqueue_job(re_review_job.id, db)

    return ResponseBuilder.success({
        "id": task.id,
        "status": task.status,
        "re_review_status": task.re_review_status,
        "message": "任务已完成" + ("，再评审已排队" if request.trigger_re_review else "")
    })


async def _run_re_review_handler(job_id: str, session: AsyncSession) -> None:
    """Job handler: 执行再评审。由 job_runner 调用，session 已提供。"""
    import time as _time
    _start = _time.monotonic()

    job = await session.get(Job, job_id)
    if not job or not job.task_id:
        return

    task = await session.get(PRDRevisionTask, job.task_id)
    if not task:
        job.status = JobStatus.FAILED
        job.failure_type = FailureType.SYSTEM
        job.error_message = "Revision task not found"
        await session.commit()
        return

    prd_id = job.prd_id or task.prd_id
    prd = await session.get(PRD, prd_id) if prd_id else None
    if not prd:
        task.re_review_status = "fail"
        job.status = JobStatus.FAILED
        job.failure_type = FailureType.SYSTEM
        job.error_message = "PRD not found"
        await session.commit()
        return

    # QUEUED → RUNNING
    job.status = JobStatus.RUNNING
    job.started_at = sql_func.now()
    await session.commit()

    try:
        from app.agents.agents.compliance_checker import ComplianceChecker
        checker = ComplianceChecker()
        result = await checker.execute({
            "product_name": prd.title,
            "industry": prd.content.get("industry", "medical") if isinstance(prd.content, dict) else "medical",
            "features": [(prd.markdown or "")[:5000]],
        })

        task.re_review_status = "pass" if result.success else "fail"
        task.re_review_result = (result.output[:500] if result.output else "再评审通过") if result.success else (result.error or "再评审未通过")

        from app.models.review_record import ReviewRecord, ReviewType, ReviewStatus
        review_record = ReviewRecord(
            project_id=prd.project_id,
            prd_id=prd.id,
            revision_task_id=job.task_id,
            review_type=ReviewType.RE_REVIEW,
            status=ReviewStatus.COMPLETED if result.success else ReviewStatus.FAILED,
            industry=prd.content.get("industry", "medical") if isinstance(prd.content, dict) else "medical",
            score=result.compliance_score if hasattr(result, 'compliance_score') else None,
            result_summary=task.re_review_result,
            trigger_source="task_complete",
            submitted_by=task.created_by,
            submitted_at=sql_func.now(),
        )
        session.add(review_record)

        job.status = JobStatus.SUCCEEDED if result.success else JobStatus.FAILED
        job.result_summary = task.re_review_result
        if not result.success:
            job.failure_type = FailureType.BUSINESS
            job.error_code = "RE_REVIEW_FAILED"
        job.completed_at = sql_func.now()
        job.duration_ms = int((_time.monotonic() - _start) * 1000)
        await session.commit()
        logger.info("Re-review done for task %s: %s (job=%s)", job.task_id, task.re_review_status, job_id)
    except Exception as exc:
        logger.exception("Re-review failed for task %s (job=%s)", job.task_id, job_id)
        job.status = JobStatus.FAILED
        job.failure_type = FailureType.SYSTEM
        job.error_code = "EXECUTION_ERROR"
        job.error_message = str(exc)[:500]
        job.completed_at = sql_func.now()
        job.duration_ms = int((_time.monotonic() - _start) * 1000)
        task.re_review_status = "fail"
        await session.commit()


@rate_limit(requests=20, window=60)
@router.delete("/{task_id}", response_model=dict)
async def delete_task(
    prd_id: str,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """删除修改任务"""
    task = await require_resource_owner(db, PRDRevisionTask, task_id, user_id)
    # 额外验证 prd_id 匹配
    if task.prd_id != prd_id:
        raise AppException("任务不存在或无权删除", code="NOT_FOUND", status_code=404)

    # 解除批注关联
    if task.annotation_id:
        ann_result = await db.execute(
            select(PRDAnnotation).where(PRDAnnotation.id == task.annotation_id, PRDAnnotation.deleted_at.is_(None))
        )
        annotation = ann_result.scalar_one_or_none()
        if annotation:
            annotation.revision_task_id = None

    task.soft_delete()
    await db.commit()

    return ResponseBuilder.success({"message": "任务已删除"})


@rate_limit(requests=100, window=60)
@router.get("/stats", response_model=dict)
async def get_task_stats(
    prd_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取 PRD 修改任务统计"""
    result = await db.execute(
        select(
            PRDRevisionTask.status,
            func.count().label("count")
        )
        .where(PRDRevisionTask.prd_id == prd_id, PRDRevisionTask.deleted_at.is_(None))
        .group_by(PRDRevisionTask.status)
    )

    stats = {row.status: row.count for row in result.all()}
    return ResponseBuilder.success({
        "todo": stats.get("todo", 0),
        "in_progress": stats.get("in_progress", 0),
        "done": stats.get("done", 0),
        "cancelled": stats.get("cancelled", 0),
        "total": sum(stats.values()),
    })
