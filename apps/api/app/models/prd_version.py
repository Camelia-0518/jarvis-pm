"""PRD version history model"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class PRDVersion(Base):
    """PRD version snapshot"""
    __tablename__ = "prd_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    prd_id = Column(String, ForeignKey("prds.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    markdown = Column(Text, default="")
    content = Column(Text, default="")  # JSON snapshot
    change_summary = Column(String, nullable=True)  # auto or user description
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
