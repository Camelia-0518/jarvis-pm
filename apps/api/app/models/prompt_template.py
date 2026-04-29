"""Prompt Template model for version management"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, func
from sqlalchemy.orm import validates

from app.core.database import Base


class PromptTemplate(Base):
    """Prompt template with version control"""
    __tablename__ = "prompt_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    version = Column(String, nullable=False, default="1.0")
    is_active = Column(Boolean, default=False, index=True)
    tags = Column(JSON, default=list)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @validates('version')
    def validate_version(self, key, value):
        if not value or not isinstance(value, str):
            raise ValueError("Version must be a non-empty string")
        return value

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "version": self.version,
            "is_active": self.is_active,
            "tags": self.tags or [],
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
