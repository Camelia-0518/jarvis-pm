"""共享 model 混入类 — 消除跨模型重复的 column 和方法。"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func
import uuid


class TimestampMixin:
    """提供 id, created_at, updated_at 列，消除 18+ 模型中的重复声明。"""

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SoftDeleteMixin:
    """软删除混入 — 添加 deleted_at 列、soft_delete() 和 is_deleted。"""

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        self.deleted_at = datetime.now(timezone.utc)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
