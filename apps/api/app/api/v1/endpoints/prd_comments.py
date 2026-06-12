"""PRD chapter comments API"""

import re
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.core.permissions import require_resource_owner
from app.models.prd_comment import PRDComment
from app.models.prd import PRD
from app.core.exceptions import AppException

router = APIRouter()


class CommentCreateRequest(BaseModel):
    chapter_id: str = Field(..., description="Chapter ID, e.g. '1', '2'")
    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: Optional[str] = None


class CommentUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


def _extract_mentions(content: str) -> str:
    """Extract @user_id mentions from content"""
    mentions = re.findall(r"@([a-zA-Z0-9_-]+)", content)
    return ",".join(mentions) if mentions else ""


@rate_limit(requests=30, window=60)
@router.post("/", response_model=dict)
async def create_comment(
    prd_id: str,
    data: CommentCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a comment on a PRD chapter"""
    # Verify PRD exists and belongs to user
    await require_resource_owner(db, PRD, prd_id, user_id)

    comment = PRDComment(
        prd_id=prd_id,
        chapter_id=data.chapter_id,
        parent_id=data.parent_id,
        content=data.content,
        mentions=_extract_mentions(data.content),
        created_by=user_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return ResponseBuilder.success(comment.to_dict())


@rate_limit(requests=100, window=60)
@router.get("/", response_model=dict)
async def list_comments(
    prd_id: str,
    chapter_id: Optional[str] = Query(None, description="Filter by chapter"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List comments for a PRD (optionally filtered by chapter)"""
    # Verify PRD ownership
    await require_resource_owner(db, PRD, prd_id, user_id)

    query = select(PRDComment).where(PRDComment.prd_id == prd_id, PRDComment.deleted_at.is_(None))
    if chapter_id:
        query = query.where(PRDComment.chapter_id == chapter_id)
    query = query.order_by(desc(PRDComment.created_at))

    result = await db.execute(query)
    comments = result.scalars().all()

    # Build reply tree
    root_comments = [c for c in comments if c.parent_id is None]
    reply_map = {}
    for c in comments:
        if c.parent_id:
            reply_map.setdefault(c.parent_id, []).append(c.to_dict())

    items = []
    for c in root_comments:
        item = c.to_dict()
        item["replies"] = reply_map.get(c.id, [])
        items.append(item)

    return ResponseBuilder.success({
        "items": items,
        "total": len(comments),
    })


@rate_limit(requests=30, window=60)
@router.put("/{comment_id}", response_model=dict)
async def update_comment(
    prd_id: str,
    comment_id: str,
    data: CommentUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a comment (only by creator)"""
    comment = await require_resource_owner(db, PRDComment, comment_id, user_id)
    if comment.prd_id != prd_id:
        raise AppException("Comment not found", code="NOT_FOUND", status_code=404)

    comment.content = data.content
    comment.mentions = _extract_mentions(data.content)
    await db.commit()
    await db.refresh(comment)

    return ResponseBuilder.success(comment.to_dict())


@rate_limit(requests=20, window=60)
@router.delete("/{comment_id}", response_model=dict)
async def delete_comment(
    prd_id: str,
    comment_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a comment (only by creator)"""
    comment = await require_resource_owner(db, PRDComment, comment_id, user_id)
    if comment.prd_id != prd_id:
        raise AppException("Comment not found", code="NOT_FOUND", status_code=404)

    comment.soft_delete()
    await db.commit()

    return ResponseBuilder.success({"message": "Comment deleted"})