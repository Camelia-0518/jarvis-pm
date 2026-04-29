"""Template endpoints for CRUD operations"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder, ErrorCode
from app.core.exceptions import ResourceNotFoundError, ResourceConflictError
from app.models.template import Template

router = APIRouter()


# ============== Request/Response Models ==============

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    industry: str = "other"
    chapters: List[str] = Field(default_factory=list)
    icon: str = "📄"
    color: str = "bg-slate-500"


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    industry: Optional[str] = None
    chapters: Optional[List[str]] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    industry: str
    chapters: List[str]
    icon: str
    color: str
    is_builtin: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============== Builtin Templates Seed Data ==============

BUILTIN_TEMPLATES = [
    {
        "id": "tpl-default",
        "name": "默认模板",
        "description": "标准 8 章 PRD 结构，适用于大多数产品场景",
        "industry": "other",
        "chapters": ["产品概述", "背景与目标", "用户故事", "功能需求", "非功能需求", "数据模型", "UI/UX 设计", "发布计划"],
        "icon": "📄",
        "color": "bg-slate-500",
    },
    {
        "id": "tpl-medical",
        "name": "医疗行业模板",
        "description": "针对医疗信息化产品，内置合规检查与多院区适配",
        "industry": "medical",
        "chapters": ["产品概述", "政策与合规", "用户角色", "核心流程", "功能需求", "数据安全", "系统集成", "上线计划"],
        "icon": "🏥",
        "color": "bg-emerald-500",
    },
    {
        "id": "tpl-saas",
        "name": "SaaS 产品模板",
        "description": "面向 B2B SaaS，强调订阅模式、权限管理与集成能力",
        "industry": "saas",
        "chapters": ["产品概述", "价值主张", "用户画像", "核心功能", "定价策略", "技术架构", "集成方案", "GTM 计划"],
        "icon": "☁️",
        "color": "bg-sky-500",
    },
    {
        "id": "tpl-ecommerce",
        "name": "电商产品模板",
        "description": "专注交易链路、商品管理与营销转化",
        "industry": "ecommerce",
        "chapters": ["产品概述", "商业模式", "用户旅程", "交易链路", "营销工具", "库存管理", "支付与风控", "运营计划"],
        "icon": "🛒",
        "color": "bg-orange-500",
    },
]


async def seed_builtin_templates(db: AsyncSession):
    """Seed builtin templates if they don't exist"""
    for tmpl in BUILTIN_TEMPLATES:
        result = await db.execute(select(Template).where(Template.id == tmpl["id"]))
        existing = result.scalar_one_or_none()
        if not existing:
            builtin = Template(
                id=tmpl["id"],
                name=tmpl["name"],
                description=tmpl["description"],
                industry=tmpl["industry"],
                chapters=tmpl["chapters"],
                icon=tmpl["icon"],
                color=tmpl["color"],
                is_builtin=True,
                created_by=None,
            )
            db.add(builtin)
    await db.commit()


# ============== Endpoints ==============

@router.get("", response_model=dict)
async def list_templates(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
):
    """List all templates (builtin + user-created) with pagination"""
    query = select(Template)

    if industry:
        query = query.where(Template.industry == industry)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Apply pagination and ordering
    query = query.order_by(desc(Template.is_builtin), desc(Template.created_at))
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    templates = result.scalars().all()

    template_list = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "industry": t.industry,
            "chapters": t.chapters or [],
            "icon": t.icon,
            "color": t.color,
            "is_builtin": t.is_builtin,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }
        for t in templates
    ]

    return ResponseBuilder.paginated(data=template_list, page=page, limit=limit, total=total)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new custom template"""
    # Check for duplicate name (case-insensitive) for this user
    existing = await db.execute(
        select(Template).where(
            func.lower(Template.name) == func.lower(template.name),
            Template.created_by == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ResourceConflictError(
            message=f"Template with name '{template.name}' already exists"
        )

    new_template = Template(
        name=template.name,
        description=template.description,
        industry=template.industry,
        chapters=template.chapters,
        icon=template.icon,
        color=template.color,
        is_builtin=False,
        created_by=user_id,
    )

    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    return ResponseBuilder.created(
        {
            "id": new_template.id,
            "name": new_template.name,
            "description": new_template.description,
            "industry": new_template.industry,
            "chapters": new_template.chapters or [],
            "icon": new_template.icon,
            "color": new_template.color,
            "is_builtin": new_template.is_builtin,
            "created_at": new_template.created_at,
            "updated_at": new_template.updated_at,
        }
    )


@router.get("/{template_id}", response_model=dict)
async def get_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get template details"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    tmpl = result.scalar_one_or_none()

    if not tmpl:
        raise ResourceNotFoundError("Template", template_id)

    # Non-builtin templates can only be accessed by their creator
    if not tmpl.is_builtin and tmpl.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this template",
        )

    return ResponseBuilder.success(
        {
            "id": tmpl.id,
            "name": tmpl.name,
            "description": tmpl.description,
            "industry": tmpl.industry,
            "chapters": tmpl.chapters or [],
            "icon": tmpl.icon,
            "color": tmpl.color,
            "is_builtin": tmpl.is_builtin,
            "created_at": tmpl.created_at,
            "updated_at": tmpl.updated_at,
        }
    )


@router.put("/{template_id}", response_model=dict)
async def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a template (builtin templates cannot be modified)"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    tmpl = result.scalar_one_or_none()

    if not tmpl:
        raise ResourceNotFoundError("Template", template_id)

    if tmpl.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Builtin templates cannot be modified",
        )

    if tmpl.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this template",
        )

    # Check name uniqueness if updating name
    if template_update.name and template_update.name != tmpl.name:
        existing = await db.execute(
            select(Template).where(
                func.lower(Template.name) == func.lower(template_update.name),
                Template.created_by == user_id,
                Template.id != template_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ResourceConflictError(
                message=f"Template with name '{template_update.name}' already exists"
            )
        tmpl.name = template_update.name

    if template_update.description is not None:
        tmpl.description = template_update.description
    if template_update.industry is not None:
        tmpl.industry = template_update.industry
    if template_update.chapters is not None:
        tmpl.chapters = template_update.chapters
    if template_update.icon is not None:
        tmpl.icon = template_update.icon
    if template_update.color is not None:
        tmpl.color = template_update.color

    await db.commit()
    await db.refresh(tmpl)

    return ResponseBuilder.success(
        {
            "id": tmpl.id,
            "name": tmpl.name,
            "description": tmpl.description,
            "industry": tmpl.industry,
            "chapters": tmpl.chapters or [],
            "icon": tmpl.icon,
            "color": tmpl.color,
            "is_builtin": tmpl.is_builtin,
            "created_at": tmpl.created_at,
            "updated_at": tmpl.updated_at,
        }
    )


@router.delete("/{template_id}", response_model=dict)
async def delete_template(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a template (builtin templates cannot be deleted)"""
    result = await db.execute(select(Template).where(Template.id == template_id))
    tmpl = result.scalar_one_or_none()

    if not tmpl:
        raise ResourceNotFoundError("Template", template_id)

    if tmpl.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Builtin templates cannot be deleted",
        )

    if tmpl.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this template",
        )

    await db.delete(tmpl)
    await db.commit()

    return ResponseBuilder.no_content("Template deleted successfully")
