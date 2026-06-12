"""PRD version history model"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.models.mixins import TimestampMixin


class PRDVersion(Base, TimestampMixin):
    """PRD version snapshot"""
    __tablename__ = "prd_versions"

    prd_id = Column(String, ForeignKey("prds.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    markdown = Column(Text, default="")
    content = Column(Text, default="")  # JSON snapshot
    change_summary = Column(String, nullable=True)  # auto or user description
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
