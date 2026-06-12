"""Job query endpoints — 统一任务视图

GET  /jobs          — 列表，支持 project_id/prd_id/task_id/job_type/status 过滤
GET  /jobs/{id}     — 详情，包含完整生命周期信息
POST /jobs/{id}/retry — 手动重试失败任务

归属校验:
  - 有 project_id 的 Job：验证 project.created_by == user_id
  - 无 project_id 的 Job：验证 triggered_by == user_id
  - list 无 project_id 过滤时：只返回 triggered_by == user_id 的记录
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.permissions import require_project_owner
from app.core.exceptions import AppException
from app.models.job import Job, JobType, JobStatus
from app.models.audit_log import AuditLog

router = APIRouter()


async def _verify_job_access(job: Job, user_id: str, db: AsyncSession) -> None:
    """验证当前用户有权访问该 Job。

    有 project_id → 验证项目归属；无 project_id → 验证 triggered_by。
    """
    if job.project_id:
        await require_project_owner(db, job.project_id, user_id)
    elif job.triggered_by != user_id:
        raise AppException("Job not found", code="NOT_FOUND", status_code=404)


@router.get("/jobs", response_model=dict)
async def list_jobs(
    project_id: Optional[str] = None,
    prd_id: Optional[str] = None,
    task_id: Optional[str] = None,
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """查询任务列表 — 按项目/PRD/任务/类型/状态过滤。

    无 project_id 时自动限定为当前用户触发的任务。
    """
    query = select(Job).order_by(desc(Job.created_at))

    if project_id:
        await require_project_owner(db, project_id, user_id)
        query = query.where(Job.project_id == project_id)
    else:
        # 无项目范围 → 只返回当前用户触发的 Job
        query = query.where(Job.triggered_by == user_id)

    if prd_id:
        query = query.where(Job.prd_id == prd_id)
    if task_id:
        query = query.where(Job.task_id == task_id)
    if job_type:
        query = query.where(Job.job_type == JobType(job_type))
    if status:
        query = query.where(Job.status == JobStatus(status))

    # total count (mirrors the same ownership filter as the main query)
    count_query = select(Job)
    if project_id:
        count_query = count_query.where(Job.project_id == project_id)
    else:
        count_query = count_query.where(Job.triggered_by == user_id)
    if prd_id:
        count_query = count_query.where(Job.prd_id == prd_id)
    if task_id:
        count_query = count_query.where(Job.task_id == task_id)
    if job_type:
        count_query = count_query.where(Job.job_type == JobType(job_type))
    if status:
        count_query = count_query.where(Job.status == JobStatus(status))
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    page = (offset // limit) + 1 if offset else 1
    return ResponseBuilder.paginated(
        data=[_format_job(j) for j in jobs],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """查询单个任务详情（需归属校验）"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise AppException("Job not found", code="NOT_FOUND", status_code=404)

    await _verify_job_access(job, user_id, db)
    return ResponseBuilder.success(_format_job(job))


@router.post("/jobs/{job_id}/retry", response_model=dict)
async def retry_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """手动重试失败任务（需归属校验）。仅 system/timeout 类型失败可重试。"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise AppException("Job not found", code="NOT_FOUND", status_code=404)

    await _verify_job_access(job, user_id, db)

    if not job.is_retryable():
        reason = "已达最大重试次数" if job.attempt >= job.max_attempts else f"失败类型 {job.failure_type.value if job.failure_type else 'unknown'} 不可重试"
        raise AppException(f"任务不可重试: {reason}", code="NOT_RETRYABLE", status_code=400)

    # 计算退避 + 重置状态
    backoff = job.next_backoff()
    job.attempt += 1
    job.status = JobStatus.QUEUED
    job.failure_type = None
    job.error_message = None
    job.error_code = None
    job.duration_ms = None
    job.started_at = None
    job.completed_at = None
    job.retry_backoff_seconds = backoff
    from datetime import datetime, timedelta, timezone
    job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)

    await db.commit()
    await db.refresh(job)

    # 入队 — 由 worker 执行
    from app.services.job_runner import enqueue_job
    await enqueue_job(job.id, db)

    db.add(AuditLog(
        user_id=user_id, workspace_id=job.workspace_id, action="retry",
        resource_type="job", resource_id=job.id,
        summary=f"重试任务 {job.id} (第 {job.attempt} 次尝试, 退避 {backoff}s)",
    ))
    await db.commit()

    return ResponseBuilder.success({
        "id": job.id,
        "attempt": job.attempt,
        "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
        "backoff_seconds": backoff,
        "message": f"任务已重新入队（第 {job.attempt}/{job.max_attempts} 次尝试）",
    })


def _format_job(job: Job) -> dict:
    """格式化 Job 为 API 响应"""
    return {
        "id": job.id,
        "job_type": job.job_type.value if job.job_type else None,
        "status": job.status.value if job.status else None,
        "failure_type": job.failure_type.value if job.failure_type else None,
        "project_id": job.project_id,
        "prd_id": job.prd_id,
        "task_id": job.task_id,
        "triggered_by": job.triggered_by,
        "input_data": job.input_data,
        "output_data": job.output_data,
        "result_summary": job.result_summary,
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "duration_ms": job.duration_ms,
        "error_message": job.error_message,
        "error_code": job.error_code,
        "retryable": job.is_retryable(),
        "retry_backoff_seconds": job.retry_backoff_seconds,
        "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
