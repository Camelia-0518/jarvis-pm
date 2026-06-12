"""Lessons Learned model — project experience knowledge base"""

import uuid

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Lesson(Base, SoftDeleteMixin, TimestampMixin):
    """A single lesson learned from a completed project"""
    __tablename__ = "lessons"

    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    delivery_plan_id = Column(String, ForeignKey("delivery_plans.id"), nullable=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)  # what_went_well | what_went_wrong | improvement | reusable_template
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)  # ["沟通", "需求管理", "测试", "上线"]
    industry = Column(String, default="medical")
    source_type = Column(String, default="ai_generated")  # ai_generated | manual | project_retro

    # Reuse metadata
    is_reusable = Column(JSON, default=dict)  # {"applicable_to": ["HIS", "EMR"], "confidence": 0.8}
    related_lessons = Column(JSON, default=list)  # [lesson_id_1, lesson_id_2]

    # Auto-extracted action item
    action_item = Column(Text, default="")
    severity = Column(String, default="medium")  # critical | high | medium | low

