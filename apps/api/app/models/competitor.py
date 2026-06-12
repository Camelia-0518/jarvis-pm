"""Competitor model for project context"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
import uuid

from app.core.database import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Competitor(Base, SoftDeleteMixin, TimestampMixin):
    """Competitor model — structured competitor profile for PRD context"""
    __tablename__ = "competitors"

    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)           # 竞品名称
    description = Column(Text, nullable=True)       # 竞品描述
    strengths = Column(Text, nullable=True)         # 优势
    weaknesses = Column(Text, nullable=True)        # 劣势
    features = Column(JSON, default=list)           # 功能对比列表
    pricing = Column(Text, nullable=True)           # 定价信息
    market_position = Column(Text, nullable=True)   # 市场定位
    source = Column(Text, nullable=True)            # 信息来源

