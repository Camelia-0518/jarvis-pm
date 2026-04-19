"""Battle (Campaign) model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, ForeignKey, Integer
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class BattleStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Battle(Base):
    """Battle campaign model for PRD sprint mode"""
    __tablename__ = "battles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    prd_id = Column(String, ForeignKey("prds.id"), nullable=True)
    status = Column(Enum(BattleStatus), default=BattleStatus.ACTIVE)
    current_day = Column(Integer, default=1)
    total_days = Column(Integer, default=5)
    days = Column(JSON, default=list)  # [{"day": "Day 1", "task": "...", "status": "...", "tool": "...", "notes": ""}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
