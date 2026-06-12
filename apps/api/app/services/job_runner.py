"""Job Runner — 轻量 DB-polling worker

职责：
  1. enqueue_job(job_id) — 标记 Job 为 QUEUED，通知 worker
  2. 按 job_type 分发到对应 handler
  3. 通用状态流转：QUEUED → RUNNING → SUCCEEDED/FAILED
  4. 异常兜底：handler 抛异常时写 FAILED + failure_type=system + error_message

不负责：业务逻辑（handler 自己管）
"""

import asyncio
import logging
import time as _time
from datetime import datetime, timezone
from typing import Callable, Awaitable

from sqlalchemy import select, or_
from sqlalchemy.sql import func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.job import Job, JobType, JobStatus, FailureType

logger = logging.getLogger(__name__)

# ── Handler registry ──

HandlerFunc = Callable[[str, AsyncSession], Awaitable[None]]
_handlers: dict[JobType, HandlerFunc] = {}

# ── Worker state ──

_wake_event = asyncio.Event()
_worker_task: asyncio.Task | None = None
_running = False


def register_handler(job_type: JobType, handler: HandlerFunc) -> None:
    """注册 job_type 对应的执行 handler"""
    _handlers[job_type] = handler


async def enqueue_job(job_id: str, session: AsyncSession | None = None) -> None:
    """将 Job 标记为 QUEUED 并唤醒 worker。

    幂等：只有非 QUEUED/RUNNING 的任务才会改状态，但始终会唤醒 worker。
    session 参数允许调用方传入已有 session（避免 DB 连接不一致）。
    """
    _own_session = session is None
    if _own_session:
        session = AsyncSessionLocal()

    try:
        job = await session.get(Job, job_id)
        if not job:
            logger.warning("enqueue_job: job %s not found", job_id)
            return

        # 幂等保护：已在队列中或正在执行的不再改状态
        if job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
            job.status = JobStatus.QUEUED
            await session.commit()
            logger.info("Job %s enqueued (type=%s)", job_id, job.job_type.value if job.job_type else "?")
    finally:
        if _own_session:
            await session.close()

    # 始终唤醒 worker（保证立即执行语义）
    _wake_event.set()


async def _execute_job(job_id: str) -> None:
    """执行单个 Job 的完整生命周期"""
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            return

        # 乐观锁：只有 QUEUED 才能切 RUNNING
        if job.status != JobStatus.QUEUED:
            return

        handler = _handlers.get(job.job_type)
        if not handler:
            job.status = JobStatus.FAILED
            job.failure_type = FailureType.SYSTEM
            job.error_message = f"No handler registered for job_type={job.job_type.value}"
            await session.commit()
            logger.error("No handler for job %s (type=%s)", job_id, job.job_type.value if job.job_type else "?")
            return

        # QUEUED → RUNNING
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

    # 执行 handler（在自己的 session 中）
    _start = _time.monotonic()
    try:
        await handler(job_id, AsyncSessionLocal())
    except Exception as exc:
        # 失败回写
        async with AsyncSessionLocal() as session:
            job = await session.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.failure_type = FailureType.SYSTEM
                job.error_code = "EXECUTION_ERROR"
                job.error_message = str(exc)[:500]
                job.completed_at = datetime.now(timezone.utc)
                job.duration_ms = int((_time.monotonic() - _start) * 1000)
                await session.commit()
                logger.exception("Job %s failed", job_id)


async def _worker_loop(poll_interval: float = 2.0) -> None:
    """主循环：轮询 QUEUED 任务并执行"""
    global _running
    _running = True
    logger.info("Job worker started (poll interval=%ss)", poll_interval)

    while _running:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Job)
                    .where(
                        Job.status == JobStatus.QUEUED,
                        or_(
                            Job.next_retry_at.is_(None),
                            Job.next_retry_at <= sql_func.now(),
                        ),
                    )
                    .order_by(Job.created_at.asc())
                    .limit(5)
                )
                queued = result.scalars().all()

                for job in queued:
                    asyncio.create_task(_execute_job(job.id))

        except Exception:
            logger.exception("Worker poll error")

        # 等待下次轮询或被唤醒
        try:
            await asyncio.wait_for(_wake_event.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass
        _wake_event.clear()


async def start_worker(poll_interval: float = 2.0) -> None:
    """启动 worker（非阻塞）"""
    global _worker_task
    if _worker_task and not _worker_task.done():
        logger.warning("Worker already running")
        return
    _worker_task = asyncio.create_task(_worker_loop(poll_interval))
    logger.info("Job worker task created")


async def stop_worker() -> None:
    """停止 worker"""
    global _running
    _running = False
    _wake_event.set()
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Job worker stopped")
