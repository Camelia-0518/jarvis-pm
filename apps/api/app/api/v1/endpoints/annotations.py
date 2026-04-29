"""PRD 评审批注 API 端点"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType

router = APIRouter()


class AnnotationCreate(BaseModel):
    chapter_num: Optional[str] = Field(None, max_length=10)
    chapter_title: Optional[str] = Field(None, max_length=200)
    line_index: Optional[int] = None
    selected_text: Optional[str] = Field(None, max_length=1000)
    content: str = Field(..., min_length=1, max_length=2000)
    annotation_type: Literal["comment", "question", "suggestion", "issue"] = "comment"
    parent_id: Optional[str] = None


class AnnotationUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=2000)
    status: Optional[Literal["open", "resolved", "dismissed"]] = None


@router.post("", response_model=dict)
async def create_annotation(
    prd_id: str,
    request: AnnotationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """创建评审批注"""
    annotation = PRDAnnotation(
        prd_id=prd_id,
        parent_id=request.parent_id,
        chapter_num=request.chapter_num,
        chapter_title=request.chapter_title,
        line_index=request.line_index,
        selected_text=request.selected_text,
        content=request.content,
        annotation_type=AnnotationType(request.annotation_type),
        created_by=user_id,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)

    return ResponseBuilder.success({
        "id": annotation.id,
        "message": "批注已添加"
    })


@router.get("", response_model=dict)
async def list_annotations(
    prd_id: str,
    status: Optional[str] = None,
    chapter_num: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取 PRD 的评审批注列表"""
    query = select(PRDAnnotation).where(PRDAnnotation.prd_id == prd_id).order_by(desc(PRDAnnotation.created_at))

    if status:
        query = query.where(PRDAnnotation.status == AnnotationStatus(status))
    if chapter_num:
        query = query.where(PRDAnnotation.chapter_num == chapter_num)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return ResponseBuilder.paginated(
        data=[{
            "id": a.id,
            "prd_id": a.prd_id,
            "parent_id": a.parent_id,
            "chapter_num": a.chapter_num,
            "chapter_title": a.chapter_title,
            "line_index": a.line_index,
            "selected_text": a.selected_text,
            "content": a.content,
            "annotation_type": a.annotation_type.value if a.annotation_type else None,
            "status": a.status.value if a.status else None,
            "created_by": a.created_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "resolved_by": a.resolved_by,
        } for a in items],
        page=offset // limit + 1 if limit > 0 else 1,
        limit=limit,
        total=total,
    )


@router.put("/{annotation_id}", response_model=dict)
async def update_annotation(
    prd_id: str,
    annotation_id: str,
    request: AnnotationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新批注（内容或状态）"""
    result = await db.execute(
        select(PRDAnnotation).where(
            PRDAnnotation.id == annotation_id,
            PRDAnnotation.prd_id == prd_id
        )
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        return ResponseBuilder.error(code="NOT_FOUND", message="批注不存在")

    if request.content is not None:
        annotation.content = request.content
    if request.status is not None:
        annotation.status = AnnotationStatus(request.status)
        if request.status == "resolved":
            from sqlalchemy.sql import func as sql_func
            annotation.resolved_at = sql_func.now()
            annotation.resolved_by = user_id

    await db.commit()
    await db.refresh(annotation)

    return ResponseBuilder.success({"id": annotation.id, "message": "批注已更新"})


@router.delete("/{annotation_id}", response_model=dict)
async def delete_annotation(
    prd_id: str,
    annotation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """删除批注"""
    result = await db.execute(
        select(PRDAnnotation).where(
            PRDAnnotation.id == annotation_id,
            PRDAnnotation.prd_id == prd_id,
            PRDAnnotation.created_by == user_id
        )
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        return ResponseBuilder.error(code="NOT_FOUND", message="批注不存在或无权删除")

    await db.delete(annotation)
    await db.commit()

    return ResponseBuilder.success({"message": "批注已删除"})


@router.get("/stats", response_model=dict)
async def get_annotation_stats(
    prd_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取 PRD 批注统计"""
    from sqlalchemy import func as sql_func

    result = await db.execute(
        select(
            PRDAnnotation.status,
            sql_func.count().label("count")
        )
        .where(PRDAnnotation.prd_id == prd_id)
        .group_by(PRDAnnotation.status)
    )

    stats = {row.status.value: row.count for row in result.all()}
    return ResponseBuilder.success({
        "open": stats.get("open", 0),
        "resolved": stats.get("resolved", 0),
        "dismissed": stats.get("dismissed", 0),
        "total": sum(stats.values()),
    })
