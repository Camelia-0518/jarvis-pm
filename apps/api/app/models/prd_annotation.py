"""PRD annotation / review comment model"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Enum
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class AnnotationStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AnnotationType(str, enum.Enum):
    COMMENT = "comment"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"


class PRDAnnotation(Base):
    """PRD review annotation / inline comment"""
    __tablename__ = "prd_annotations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prd_id = Column(String, ForeignKey("prds.id"), nullable=False)
    parent_id = Column(String, ForeignKey("prd_annotations.id"), nullable=True)  # reply to

    # Position: which chapter/section this annotation belongs to
    chapter_num = Column(String, nullable=True)
    chapter_title = Column(String, nullable=True)
    line_index = Column(Integer, nullable=True)  # approximate line position
    selected_text = Column(Text, nullable=True)  # the text being annotated

    # Content
    content = Column(Text, nullable=False)
    annotation_type = Column(Enum(AnnotationType), default=AnnotationType.COMMENT)
    status = Column(Enum(AnnotationStatus), default=AnnotationStatus.OPEN)

    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
