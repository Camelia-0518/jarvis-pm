"""Requirement model for project feature backlog"""

from sqlalchemy import Column, String, Text, ForeignKey, Integer, Float, DateTime
from sqlalchemy.sql import func

import uuid

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

class Requirement(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "requirements"

    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"))

    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="backlog")  # backlog, todo, in_progress, done
    priority = Column(String, default="p1")  # p0, p1, p2

    # RICE scoring
    rice_reach = Column(Integer, default=0)  # 影响用户数/范围 1-100
    rice_impact = Column(Float, default=0.0)  # 影响程度 0.25, 0.5, 1, 2, 3
    rice_confidence = Column(Integer, default=0)  # 信心度 0-100
    rice_effort = Column(Float, default=0.0)  # 工作量（人月）
    rice_score = Column(Float, default=0.0)  # Reach * Impact * Confidence / Effort

    # Kano model
    kano_category = Column(String, default="")  # must_be, one_dimensional, attractive, indifferent, reverse



