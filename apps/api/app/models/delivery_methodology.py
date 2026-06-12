"""Delivery Methodology model — standardized delivery paths"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

class DeliveryMethodology(Base, SoftDeleteMixin, TimestampMixin):
    """Standardized delivery methodology template (Stage-Gate, etc.)"""
    __tablename__ = "delivery_methodologies"

    name = Column(String, nullable=False)
    description = Column(Text, default="")
    industry = Column(String, default="general")  # medical, saas, general

    # Stage-Gate stages
    stages = Column(JSON, default=list)

    # Best practices & lessons learned
    best_practices = Column(JSON, default=list)
    pitfalls = Column(JSON, default=list)
    templates = Column(JSON, default=list)

    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
