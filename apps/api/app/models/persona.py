"""User persona model for project context"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Persona(Base):
    """User persona model — structured user profile for PRD context"""
    __tablename__ = "personas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)           # 角色名称，如"门诊医生"
    role = Column(String, nullable=False)           # 角色类型，如"医生/护士/患者"
    description = Column(Text, nullable=True)       # 角色描述
    pain_points = Column(Text, nullable=True)       # 痛点
    goals = Column(Text, nullable=True)             # 目标
    scenarios = Column(Text, nullable=True)         # 使用场景
    demographics = Column(Text, nullable=True)      # 人口统计特征

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
