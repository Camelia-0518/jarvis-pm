"""用户反馈 API 端点"""

from typing import Optional, Literal
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.models.feedback import Feedback

router = APIRouter()


class FeedbackCreate(BaseModel):
    category: Literal["bug", "feature", "quality", "other"] = Field(..., description="反馈类型")
    content: str = Field(..., min_length=1, max_length=2000, description="反馈内容")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分 1-5")
    context: Optional[str] = Field(None, max_length=100, description="相关页面或功能")


class FeedbackResponse(BaseModel):
    id: str
    category: str
    content: str
    rating: Optional[int]
    context: Optional[str]
    created_at: datetime


@rate_limit(requests=30, window=60)
@router.post("", response_model=dict)
async def create_feedback(
    request: FeedbackCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """提交用户反馈"""
    feedback = Feedback(
        user_id=user_id,
        category=request.category,
        content=request.content,
        rating=request.rating,
        context=request.context,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return ResponseBuilder.success({
        "id": feedback.id,
        "message": "反馈已提交，感谢你的建议！"
    })


@rate_limit(requests=100, window=60)
@router.get("", response_model=dict)
async def list_feedback(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取反馈列表（管理员用，当前仅返回自己的）"""
    query = select(Feedback).where(Feedback.user_id == user_id, Feedback.deleted_at.is_(None)).order_by(desc(Feedback.created_at))

    if category:
        query = query.where(Feedback.category == category)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return ResponseBuilder.paginated(
        data=[{
            "id": i.id,
            "category": i.category,
            "content": i.content,
            "rating": i.rating,
            "context": i.context,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        } for i in items],
        page=offset // limit + 1 if limit > 0 else 1,
        limit=limit,
        total=total,
    )