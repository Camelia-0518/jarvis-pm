"""Project model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, ForeignKey
from sqlalchemy.sql import func
import enum

from app.core.database import Base
from app.models.mixins import TimestampMixin

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class Project(Base, TimestampMixin):
    """Project model"""
    __tablename__ = "projects"

    name = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=True, index=True)
    description = Column(Text, nullable=True)
    industry = Column(String, default="other")  # medical, ecommerce, saas, other
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    settings = Column(JSON, default=dict)
