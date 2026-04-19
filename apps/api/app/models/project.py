"""Project model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, ForeignKey
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(String, default="other")  # medical, ecommerce, saas, other
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
