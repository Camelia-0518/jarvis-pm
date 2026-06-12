"""AuditLog — 关键操作审计追踪"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AuditLog(Base, TimestampMixin):
    """审计日志 — 记录关键操作（创建/更新/删除/重试/登录）"""

    __tablename__ = "audit_logs"

    # ── 谁 ──
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)

    # ── 做了什么 ──
    action = Column(String(50), nullable=False, index=True)  # create/update/delete/retry/login/complete
    resource_type = Column(String(50), nullable=False)        # project/prd/annotation/job/task
    resource_id = Column(String, nullable=True, index=True)

    # ── 详情 ──
    summary = Column(Text, nullable=True)                     # 人可读摘要
    details = Column(JSON, default=dict)                      # 结构化变更（新旧值）
    ip_address = Column(String(45), nullable=True)
