"""Authentication endpoints with security enhancements"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user_id,
    decode_token,
)
from app.core.responses import ResponseBuilder, ErrorCode
from app.core.exceptions import (
    AuthenticationError,
    ValidationError,
    ResourceConflictError
)
from app.core.rate_limit import rate_limit, get_rate_limiter
from app.core.logging_config import audit
from app.models.user import User, UserRole

router = APIRouter()
security = HTTPBearer()


class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=2, max_length=50)

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    name: str
    role: str
    is_active: bool


@router.post("/register", response_model=dict)
@rate_limit(requests=5, window=300)  # 5 registrations per 5 minutes
async def register(
    request: Request,
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ResourceConflictError(message="Email already registered")

    # Create new user
    user = User(
        email=data.email,
        name=data.name,
        hashed_password=get_password_hash(data.password),
        role=UserRole.MEMBER,
        is_active=True
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Audit log
    audit.log_security(
        event="user_registered",
        severity="info",
        details={"email": data.email}
    )

    # Create token
    token = create_access_token(data={"sub": user.id})

    return ResponseBuilder.success({
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value
        }
    })


@router.post("/login", response_model=dict)
@rate_limit(requests=10, window=60)  # 10 logins per minute
async def login(
    request: Request,
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login user"""
    # Find user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        audit.log_security(
            event="login_failed",
            severity="warning",
            details={"email": data.email, "reason": "invalid_credentials"}
        )
        raise AuthenticationError(message="Invalid email or password")

    if not user.is_active:
        raise AuthenticationError(message="Account is disabled")

    # Update last login
    user.last_login = datetime.now()
    await db.commit()

    # Audit log
    audit.log_security(
        event="login_success",
        severity="info",
        details={"user_id": user.id, "email": user.email}
    )

    # Create token
    token = create_access_token(data={"sub": user.id})

    return ResponseBuilder.success({
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value
        }
    })


@router.get("/me", response_model=dict)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        # Single-user mode: return a default user when not found
        return ResponseBuilder.success({
            "id": user_id,
            "email": "admin@jarvis.pm",
            "name": "Admin",
            "role": "admin",
            "is_active": True,
            "created_at": None
        })

    return ResponseBuilder.success({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None
    })


@router.put("/me/password", response_model=dict)
@rate_limit(requests=3, window=300)  # 3 password changes per 5 minutes
async def change_password(
    request: Request,
    old_password: str = Body(..., min_length=1),
    new_password: str = Body(..., min_length=8, max_length=128),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError(message="User not found")

    # Verify old password
    if not verify_password(old_password, user.hashed_password):
        audit.log_security(
            event="password_change_failed",
            severity="medium",
            details={"user_id": user_id, "reason": "invalid_old_password"}
        )
        raise AuthenticationError(message="Current password is incorrect")

    # Update password
    user.hashed_password = get_password_hash(new_password)
    await db.commit()

    # Audit log
    audit.log_security(
        event="password_changed",
        severity="info",
        details={"user_id": user_id}
    )

    return ResponseBuilder.success(message="Password changed successfully")


@router.post("/refresh", response_model=dict)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise AuthenticationError(message="Invalid token")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError(message="Invalid token")

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationError(message="User not found or inactive")

    # Create new token
    new_token = create_access_token(data={"sub": user_id})

    return ResponseBuilder.success({
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": 60 * 60 * 24 * 7  # 7 days
    })


from datetime import datetime
