"""异步任务 Job 模型

替代 request 内裸 background_tasks，提供统一的任务生命周期:
  queued → running → succeeded / failed
  支持重试、失败原因记录、历史查询、耗时追踪。
"""

import enum

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey, Enum

from app.core.database import Base
from app.models.mixins import TimestampMixin


class JobType(str, enum.Enum):
    COMPLIANCE_CHECK = "compliance_check"
    RE_REVIEW = "re_review"
    PRD_GENERATION = "prd_generation"
    PROTOTYPE_GENERATION = "prototype_generation"
    EXPORT = "export"
    GENERAL = "general"


class FailureType(str, enum.Enum):
    BUSINESS = "business"     # 业务失败：合规不通过、内容不合法等
    SYSTEM = "system"         # 系统失败：LLM 超时、网络异常、DB 错误
    TIMEOUT = "timeout"       # 执行超时
    CANCELLED = "cancelled"   # 手动取消


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


# 可重试的失败类型
RETRYABLE_FAILURES = {FailureType.SYSTEM, FailureType.TIMEOUT}

# 退避策略（秒）
RETRY_BACKOFF = [1, 5, 30]


class Job(Base, TimestampMixin):
    """异步任务记录 — 支持重试、失败分类、超时检测"""

    __tablename__ = "jobs"

    # ── 标识 ──
    job_type = Column(Enum(JobType), nullable=False, default=JobType.GENERAL)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    failure_type = Column(Enum(FailureType), nullable=True)  # 失败分类

    # ── 关联 ──
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    prd_id = Column(String, ForeignKey("prds.id"), nullable=True, index=True)
    task_id = Column(String, ForeignKey("prd_revision_tasks.id"), nullable=True, index=True)
    triggered_by = Column(String, ForeignKey("users.id"), nullable=False)

    # ── 输入/输出 ──
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    result_summary = Column(Text, nullable=True)

    # ── 执行信息 ──
    attempt = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)  # 机器可读错误码

    # ── 重试控制 ──
    retry_backoff_seconds = Column(Integer, nullable=True)  # 当前退避等待秒数
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # ── 时间戳 ──
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def is_retryable(self) -> bool:
        """是否可重试"""
        return (
            self.status == JobStatus.FAILED
            and self.failure_type in RETRYABLE_FAILURES
            and self.attempt < self.max_attempts
        )

    def next_backoff(self) -> int:
        """计算下一次退避秒数"""
        idx = min(self.attempt - 1, len(RETRY_BACKOFF) - 1)
        return RETRY_BACKOFF[idx]
