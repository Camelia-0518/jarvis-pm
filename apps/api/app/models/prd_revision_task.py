"""PRD revision task model — 批注驱动的修改任务"""

import enum

from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class PRDRevisionTask(Base, SoftDeleteMixin, TimestampMixin):
    """PRD 修改任务：从批注产生，驱动 PRD 迭代"""
    __tablename__ = "prd_revision_tasks"

    prd_id = Column(String, ForeignKey("prds.id"), nullable=False, index=True)
    annotation_id = Column(String, ForeignKey("prd_annotations.id"), nullable=True, index=True)

    # 任务内容（从批注自动提取）
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)  # 批注原文 + 补充说明

    # 状态流转：todo → in_progress → done / cancelled
    # 转由 app.models.state_machine.RevisionTaskStateMachine 统一管控
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)

    # 负责人
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    # 完成信息
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_note = Column(Text, nullable=True)  # 修改说明

    # 再评审结果（任务完成后触发）
    re_review_status = Column(String(20), nullable=True)  # pass, partial, fail, pending
    re_review_result = Column(Text, nullable=True)  # 再评审结果摘要

