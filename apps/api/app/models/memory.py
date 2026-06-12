#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长期记忆模型

存储用户偏好、项目风格、反馈等长期记忆
"""

from sqlalchemy import Column, String, DateTime, Integer, Float, JSON
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.mixins import TimestampMixin
import uuid


class MemoryEntry(Base, TimestampMixin):
    """记忆条目"""
    __tablename__ = "memory_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)  # preference / style / feedback / context
    content = Column(JSON, nullable=False, default=dict)
    tags = Column(JSON, nullable=False, default=list)  # ["medical", "prd_style", "formal"]
    project_id = Column(String(36), nullable=True, index=True)
    importance = Column(Float, nullable=False, default=5.0)  # 0-10
    access_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())