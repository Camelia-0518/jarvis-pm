"""PRD annotation / review comment model"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Enum
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class AnnotationStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AnnotationType(str, enum.Enum):
    COMMENT = "comment"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"


class PRDAnnotation(Base, SoftDeleteMixin, TimestampMixin):
    """PRD review annotation / inline comment"""
    __tablename__ = "prd_annotations"

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

    # 关联修改任务（闭环改造）
    revision_task_id = Column(String, ForeignKey("prd_revision_tasks.id"), nullable=True, index=True)

    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
