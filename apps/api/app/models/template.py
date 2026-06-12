"""Template model for customizable PRD templates"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

class Template(Base, SoftDeleteMixin, TimestampMixin):
    """PRD Template model"""
    __tablename__ = "templates"

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(String, default="other")  # medical, ecommerce, saas, other
    chapters = Column(JSON, default=list)       # list of chapter names
    icon = Column(String, default="📄")
    color = Column(String, default="bg-slate-500")
    is_builtin = Column(Boolean, default=False)  # builtin templates cannot be deleted
    created_by = Column(String, nullable=True)   # null for builtin templates