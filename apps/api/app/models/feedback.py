"""User feedback model"""

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Feedback(Base):
    """User feedback entry"""
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)  # bug, feature, quality, other
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    context = Column(String, nullable=True)  # page or feature reference
    created_at = Column(DateTime(timezone=True), server_default=func.now())
