"""Template model for customizable PRD templates"""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Template(Base):
    """PRD Template model"""
    __tablename__ = "templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(String, default="other")  # medical, ecommerce, saas, other
    chapters = Column(JSON, default=list)       # list of chapter names
    icon = Column(String, default="📄")
    color = Column(String, default="bg-slate-500")
    is_builtin = Column(Boolean, default=False)  # builtin templates cannot be deleted
    created_by = Column(String, nullable=True)   # null for builtin templates
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
