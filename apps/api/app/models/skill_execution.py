"""Skill execution model for tracking AI skill runs"""

from sqlalchemy import Column, String, DateTime, JSON, Integer, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class SkillExecution(Base):
    """Skill execution tracking model

    Records each execution of an AI skill including inputs, outputs,
    performance metrics, and error information.
    """
    __tablename__ = "skill_executions"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Skill identification
    skill_id = Column(String, nullable=False, index=True)
    """Skill identifier (e.g., 'product-analyst', 'tech-architect')"""

    # Relationships (optional)
    workflow_id = Column(String, nullable=True, index=True)
    """Optional: Associated workflow if part of a workflow execution"""

    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    """Optional: Associated project context"""

    # Execution data
    inputs = Column(JSON, default=dict)
    """Input parameters passed to the skill"""

    output = Column(JSON, nullable=True)
    """Output result from the skill execution"""

    success = Column(Boolean, default=True)
    """Whether the execution completed successfully"""

    execution_time_ms = Column(Integer, default=0)
    """Execution time in milliseconds"""

    token_usage = Column(JSON, default=dict)
    """Token usage statistics: {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}"""

    error_message = Column(Text, nullable=True)
    """Error message if execution failed"""

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SkillExecution(id={self.id}, skill_id={self.skill_id}, success={self.success})>"

    def to_dict(self):
        """Convert to dictionary representation with JSON-safe values"""

        def _sanitize(value):
            """Recursively sanitize values for JSON serialization"""
            if value is None:
                return None
            if isinstance(value, (str, int, float, bool)):
                return value
            if isinstance(value, dict):
                return {k: _sanitize(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_sanitize(v) for v in value]
            # Fallback: convert to string
            return str(value)

        return {
            "id": self.id,
            "skill_id": self.skill_id,
            "workflow_id": self.workflow_id,
            "project_id": self.project_id,
            "inputs": _sanitize(self.inputs),
            "output": _sanitize(self.output),
            "success": bool(self.success),
            "execution_time_ms": int(self.execution_time_ms) if self.execution_time_ms else 0,
            "token_usage": _sanitize(self.token_usage),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
