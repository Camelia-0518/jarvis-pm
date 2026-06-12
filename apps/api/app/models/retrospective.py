"""Retrospective model — project post-mortem and lessons learned"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Float
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Retrospective(Base, SoftDeleteMixin, TimestampMixin):
    """Project retrospective / post-mortem analysis"""
    __tablename__ = "retrospectives"

    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)

    # 3-column retro structure
    what_went_well = Column(Text, default="")
    what_went_wrong = Column(Text, default="")
    surprises = Column(Text, default="")

    # Structured decisions log
    key_decisions = Column(JSON, default=list)

    # Delivery metrics
    planned_days = Column(Float, nullable=True)
    actual_days = Column(Float, nullable=True)
    planned_budget = Column(Float, nullable=True)
    actual_budget = Column(Float, nullable=True)

    # Extracted lessons
    lessons = Column(JSON, default=list)

    # AI-generated analysis
    ai_analysis = Column(Text, default="")
    ai_suggestions = Column(JSON, default=list)

    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
