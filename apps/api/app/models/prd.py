"""PRD document model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Text
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class PRDStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"


class PRD(Base):
    """PRD document model"""
    __tablename__ = "prds"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    version = Column(String, default="1.0")
    status = Column(Enum(PRDStatus), default=PRDStatus.DRAFT)
    content = Column(JSON, default=dict)  # Structured content with chapters
    markdown = Column(Text, default="")  # Raw markdown
    ai_generated = Column(JSON, default=dict)  # AI generation metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
