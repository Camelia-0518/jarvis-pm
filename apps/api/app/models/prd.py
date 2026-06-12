"""PRD document model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Text
from datetime import datetime, timezone
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

class PRDStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    IMPLEMENTED = "implemented"

class PRD(Base, SoftDeleteMixin, TimestampMixin):
    """PRD document model"""
    __tablename__ = "prds"

    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    version = Column(String, default="1.0")
    status = Column(Enum(PRDStatus), default=PRDStatus.DRAFT)
    content = Column(JSON, default=dict)  # Structured content with chapters
    markdown = Column(Text, default="")  # Raw markdown
    ai_generated = Column(JSON, default=dict)  # AI generation metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
