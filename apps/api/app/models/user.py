"""User model"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, Boolean
from sqlalchemy.sql import func
import enum

from app.core.database import Base
from app.models.mixins import TimestampMixin

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"

class User(Base, TimestampMixin):
    """User model"""
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.MEMBER)
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, default=dict)
