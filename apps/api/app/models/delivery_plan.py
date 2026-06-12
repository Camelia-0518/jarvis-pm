"""Delivery Plan model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Text
from datetime import datetime, timezone
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

class DeliveryStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DeliveryPlan(Base, SoftDeleteMixin, TimestampMixin):
    """Project delivery plan model"""
    __tablename__ = "delivery_plans"

    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    prd_id = Column(String, ForeignKey("prds.id"), nullable=True)
    title = Column(String, nullable=False)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.DRAFT)
    industry = Column(String, default="medical")

    # Core delivery data (JSON)
    wbs = Column(JSON, default=dict)
    milestones = Column(JSON, default=dict)
    resources = Column(JSON, default=dict)
    gantt = Column(JSON, default=dict)

    # Risk analysis
    risks = Column(JSON, default=dict)
    risk_matrix = Column(JSON, default=dict)
    risk_response_plan = Column(JSON, default=dict)

    # Stakeholder management
    stakeholders = Column(JSON, default=dict)
    raci = Column(JSON, default=dict)
    communication_plan = Column(JSON, default=dict)
    status_template = Column(JSON, default=dict)

    # Full markdown output
    plan_markdown = Column(Text, default="")
    risk_markdown = Column(Text, default="")
    stakeholder_markdown = Column(Text, default="")

    # Metadata
    ai_generated = Column(JSON, default=dict)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
