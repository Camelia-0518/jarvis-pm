"""PRD chapter comment model with @mention support"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class PRDComment(Base, SoftDeleteMixin, TimestampMixin):
    """Comment on a specific PRD chapter"""
    __tablename__ = "prd_comments"

    prd_id = Column(String, ForeignKey("prds.id"), nullable=False, index=True)
    chapter_id = Column(String, nullable=False, index=True)  # e.g., "1", "2"
    parent_id = Column(String, ForeignKey("prd_comments.id"), nullable=True, index=True)

    content = Column(Text, nullable=False)
    mentions = Column(Text, default="")  # comma-separated user IDs for @mentions

    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prd_id": self.prd_id,
            "chapter_id": self.chapter_id,
            "parent_id": self.parent_id,
            "content": self.content,
            "mentions": self.mentions.split(",") if self.mentions else [],
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }