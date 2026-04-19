"""PRD endpoints with real AI generation"""

import json
import re
import uuid
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.services.ai_service import ai_service
from app.models.prd import PRD, PRDStatus
from app.models.project import Project

router = APIRouter()


def prd_json_to_markdown(data: dict, title: str) -> str:
    """Convert AI-generated PRD JSON to markdown"""
    md = [f"# {title}"]

    outline = data.get("outline", {}) if isinstance(data.get("outline"), dict) else {}
    content = data.get("content", {}) if isinstance(data.get("content"), dict) else {}
    suggestions = data.get("suggestions", []) if isinstance(data.get("suggestions"), list) else []

    # Background
    background = content.get("background", {}) if isinstance(content, dict) else {}
    if isinstance(background, str):
        md.append("\n## 一、背景与目标")
        md.append(f"\n{background}")
    elif isinstance(background, dict) and background:
        md.append("\n## 一、背景与目标")
        md.append(f"\n### 执行摘要\n{background.get('executive_summary', '')}")

        bp = background.get("business_problem", {}) if isinstance(background.get("business_problem"), dict) else {}
        if bp:
            md.append("\n### 当前痛点")
            for pain in bp.get("pain_points", []) if isinstance(bp.get("pain_points"), list) else []:
                md.append(f"- {pain}")
            md.append(f"\n**现状流程**: {bp.get('current_state', '')}")

        md.append(f"\n### 产品愿景\n{background.get('product_vision', '')}")

        obj = background.get("objectives", {}) if isinstance(background.get("objectives"), dict) else {}
        if obj:
            md.append("\n### 项目目标")
            md.append("**主要目标**:")
            for o in obj.get("primary", []) if isinstance(obj.get("primary"), list) else []:
                md.append(f"- {o}")
            if obj.get("secondary"):
                md.append("\n**次要目标**:")
                for o in obj.get("secondary", []) if isinstance(obj.get("secondary"), list) else []:
                    md.append(f"- {o}")

        sm = background.get("success_metrics", {}) if isinstance(background.get("success_metrics"), dict) else {}
        if sm:
            md.append("\n### 成功指标")
            for k, v in sm.items():
                md.append(f"- {k}: {v}")

        scope = background.get("scope", {}) if isinstance(background.get("scope"), dict) else {}
        if scope:
            md.append("\n### 项目范围")
            md.append("**包含范围**:")
            for s in scope.get("in_scope", []) if isinstance(scope.get("in_scope"), list) else []:
                md.append(f"- {s}")
            md.append("\n**不包含范围**:")
            for s in scope.get("out_of_scope", []) if isinstance(scope.get("out_of_scope"), list) else []:
                md.append(f"- {s}")

    # User Stories
    user_stories = content.get("user_stories", []) if isinstance(content, dict) and isinstance(content.get("user_stories"), list) else []
    if user_stories:
        md.append("\n## 二、用户故事")
        for us in user_stories:
            if isinstance(us, dict):
                md.append(f"\n### {us.get('id', 'US-XXX')}: {us.get('role', '')}")
                md.append(f"\n> {us.get('story', '')}")
                md.append(f"\n**优先级**: {us.get('priority', 'P1')}")
                ac = us.get("acceptance_criteria", []) if isinstance(us.get("acceptance_criteria"), list) else []
                if ac:
                    md.append("\n**验收标准**:")
                    for c in ac:
                        md.append(f"- {c}")

    # Suggestions
    if suggestions:
        md.append("\n## 系统建议（AI生成）")
        for i, s in enumerate(suggestions, 1):
            md.append(f"{i}. {s}")

    # Outline
    sections = outline.get("sections", []) if isinstance(outline.get("sections"), list) else []
    if sections:
        md.append("\n---")
        md.append("\n## PRD标准结构")
        for sec in sections:
            if isinstance(sec, dict):
                md.append(f"{sec.get('chapter', '')}. {sec.get('title', '')}")
                for kp in sec.get("key_points", []) if isinstance(sec.get("key_points"), list) else []:
                    md.append(f"  - {kp}")

    return "\n".join(md)


def extract_chapter_content(markdown: str, chapter_titles: List[str]) -> Dict[str, str]:
    """按章节标题拆分 markdown，提取各章节正文"""
    contents: Dict[str, str] = {}
    if not markdown or not chapter_titles:
        return contents

    # 策略1: 匹配 markdown 标题 (# ~ ####)
    escaped_titles = [re.escape(t) for t in chapter_titles]
    pattern = r'(?:^|\n)(?:#{1,4}\s*)(' + '|'.join(escaped_titles) + r')\s*(?:\n|\r\n)'

    parts = re.split(pattern, markdown)
    current_title = None
    for part in parts:
        if part in chapter_titles:
            current_title = part
        elif current_title is not None:
            contents[current_title] = part.strip()
            current_title = None

    # 策略2: 如果策略1未命中，尝试匹配加粗标题或下划线标题
    if not contents:
        bold_pattern = r'(?:^|\n)\*\*(' + '|'.join(escaped_titles) + r')\*\*\s*(?:\n|\r\n)'
        parts = re.split(bold_pattern, markdown)
        for part in parts:
            if part in chapter_titles:
                current_title = part
            elif current_title is not None:
                contents[current_title] = part.strip()
                current_title = None

    # 策略3: 如果仍未命中，按通用章节关键词（如“背景与目标”、“用户故事”）做模糊拆分
    if not contents:
        generic_sections = ["背景与目标", "用户故事", "功能需求", "非功能需求", "产品概述"]
        for title in generic_sections:
            if title in markdown:
                idx = markdown.index(title)
                next_idx = len(markdown)
                for other in generic_sections:
                    if other != title and other in markdown:
                        o_idx = markdown.index(other)
                        if o_idx > idx and o_idx < next_idx:
                            next_idx = o_idx
                contents[title] = markdown[idx + len(title):next_idx].strip("\n#* ")

    return contents


class PRDCreateRequest(BaseModel):
    """Create PRD request"""
    project_id: str
    title: str = Field(..., min_length=1, max_length=200)
    template: Optional[str] = "standard"


class PRDUpdateRequest(BaseModel):
    """Update PRD request"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[dict] = None
    status: Optional[str] = None
    markdown: Optional[str] = None


class PRDExportRequest(BaseModel):
    """Export PRD request"""
    format: str = Field("markdown", pattern="^(markdown|json|pdf)$")


class PRDGenerateRequest(BaseModel):
    """Generate PRD chapter request"""
    chapter: str
    prompt: str
    context: Optional[dict] = None


@router.get("", response_model=dict)
async def list_prds(
    project_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """List PRDs"""
    query = select(PRD).where(PRD.created_by == user_id)
    if project_id:
        query = query.where(PRD.project_id == project_id)
    query = query.order_by(desc(PRD.created_at))

    result = await db.execute(query)
    prds = result.scalars().all()

    items = []
    for prd in prds:
        items.append({
            "id": prd.id,
            "project_id": prd.project_id,
            "title": prd.title,
            "version": prd.version,
            "status": prd.status.value,
            "created_at": prd.created_at.isoformat() if prd.created_at else None,
            "updated_at": prd.updated_at.isoformat() if prd.updated_at else None,
        })

    return ResponseBuilder.success({
        "items": items,
        "total": len(items)
    })


@router.post("", response_model=dict)
async def create_prd(
    data: PRDCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new PRD with AI-generated content"""
    # Get project info for context
    result = await db.execute(
        select(Project).where(Project.id == data.project_id, Project.created_by == user_id)
    )
    project = result.scalar_one_or_none()

    description = project.description if project else ""
    industry = project.industry if project else data.template or "general"

    # Generate PRD content using AI
    ai_result = await ai_service.generate_prd(
        title=data.title,
        description=description or data.title,
        industry=industry,
        template=data.template or "default",
    )

    markdown = prd_json_to_markdown(ai_result, data.title)

    # Build chapters structure for frontend
    chapters = {}
    outline = ai_result.get("outline", {}) if isinstance(ai_result.get("outline"), dict) else {}
    section_titles = []
    for sec in outline.get("sections", []):
        if isinstance(sec, dict):
            section_titles.append(sec.get("title", ""))

    # 尝试从 markdown 中提取各章节正文
    chapter_contents = extract_chapter_content(markdown, section_titles)

    for sec in outline.get("sections", []):
        if not isinstance(sec, dict):
            continue
        chapter_num = str(sec.get("chapter", ""))
        title = sec.get("title", "")
        # 优先使用从 markdown 解析出的章节正文
        parsed_content = chapter_contents.get(title, "")
        if not parsed_content:
            # 退化为将 key_points 以列表形式拼接
            key_points = sec.get("key_points", []) if isinstance(sec.get("key_points"), list) else []
            parsed_content = "\n".join([f"- {kp}" for kp in key_points])

        chapters[chapter_num] = {
            "title": title,
            "content": parsed_content,
            "status": "draft"
        }

    content_struct = {
        "chapters": chapters,
        "template": data.template,
        "industry": industry,
    }

    new_prd = PRD(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        title=data.title,
        version="1.0",
        status=PRDStatus.DRAFT,
        content=content_struct,
        markdown=markdown,
        ai_generated=ai_result,
        created_by=user_id,
    )

    db.add(new_prd)
    await db.commit()
    await db.refresh(new_prd)

    return ResponseBuilder.success({
        "id": new_prd.id,
        "project_id": new_prd.project_id,
        "title": new_prd.title,
        "version": new_prd.version,
        "status": new_prd.status.value,
        "content": new_prd.content,
        "markdown": new_prd.markdown,
        "created_at": new_prd.created_at.isoformat() if new_prd.created_at else None,
        "updated_at": new_prd.updated_at.isoformat() if new_prd.updated_at else None,
    })


@router.get("/{prd_id}", response_model=dict)
async def get_prd(
    prd_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get PRD by ID"""
    result = await db.execute(
        select(PRD).where(PRD.id == prd_id, PRD.created_by == user_id)
    )
    prd = result.scalar_one_or_none()

    if not prd:
        return ResponseBuilder.error("PRD not found", code="NOT_FOUND")

    return ResponseBuilder.success({
        "id": prd.id,
        "project_id": prd.project_id,
        "title": prd.title,
        "version": prd.version,
        "status": prd.status.value,
        "content": prd.content,
        "markdown": prd.markdown,
        "created_at": prd.created_at.isoformat() if prd.created_at else None,
        "updated_at": prd.updated_at.isoformat() if prd.updated_at else None,
    })


@router.put("/{prd_id}", response_model=dict)
async def update_prd(
    prd_id: str,
    data: PRDUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Update PRD"""
    result = await db.execute(
        select(PRD).where(PRD.id == prd_id, PRD.created_by == user_id)
    )
    prd = result.scalar_one_or_none()

    if not prd:
        return ResponseBuilder.error("PRD not found", code="NOT_FOUND")

    if data.title is not None:
        prd.title = data.title
    if data.content is not None:
        prd.content = data.content
    if data.markdown is not None:
        prd.markdown = data.markdown
    if data.status is not None:
        try:
            prd.status = PRDStatus(data.status)
        except ValueError:
            return ResponseBuilder.error(f"Invalid status: {data.status}")

    await db.commit()
    await db.refresh(prd)

    return ResponseBuilder.success({
        "id": prd.id,
        "project_id": prd.project_id,
        "title": prd.title,
        "version": prd.version,
        "status": prd.status.value,
        "content": prd.content,
        "markdown": prd.markdown,
        "created_at": prd.created_at.isoformat() if prd.created_at else None,
        "updated_at": prd.updated_at.isoformat() if prd.updated_at else None,
    })


@router.delete("/{prd_id}", response_model=dict)
async def delete_prd(
    prd_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Delete PRD"""
    result = await db.execute(
        select(PRD).where(PRD.id == prd_id, PRD.created_by == user_id)
    )
    prd = result.scalar_one_or_none()

    if not prd:
        return ResponseBuilder.error("PRD not found", code="NOT_FOUND")

    await db.delete(prd)
    await db.commit()

    return ResponseBuilder.success({
        "id": prd_id,
        "deleted": True
    })


@router.post("/{prd_id}/generate", response_model=dict)
async def generate_prd_content(
    prd_id: str,
    data: PRDGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate PRD content using AI"""
    result = await db.execute(
        select(PRD).where(PRD.id == prd_id, PRD.created_by == user_id)
    )
    prd = result.scalar_one_or_none()

    if not prd:
        return ResponseBuilder.error("PRD not found", code="NOT_FOUND")

    industry = prd.content.get("industry", "general") if prd.content else "general"
    ai_result = await ai_service.generate_prd_chapter(
        chapter=data.chapter,
        prompt=data.prompt,
        context=prd.ai_generated if prd.ai_generated else {},
        industry=industry,
    )

    # Update PRD content
    content = prd.content or {"chapters": {}, "template": "standard", "industry": industry}
    content["chapters"] = content.get("chapters", {})
    content["chapters"][data.chapter] = {
        "title": ai_result.get("content", {}).get("sections", [{}])[0].get("title", f"Chapter {data.chapter}"),
        "content": ai_result.get("markdown", ""),
        "status": "generated"
    }

    # Append to markdown
    existing_md = prd.markdown or ""
    new_md = ai_result.get("markdown", "")
    prd.markdown = existing_md + "\n\n" + new_md if existing_md else new_md
    prd.content = content

    await db.commit()

    return ResponseBuilder.success({
        "chapter": chapter,
        "content": ai_result.get("content", {}),
        "markdown": ai_result.get("markdown", ""),
    })


@router.get("/{prd_id}/export", response_model=dict)
async def export_prd(
    prd_id: str,
    format: str = "markdown",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Export PRD"""
    result = await db.execute(
        select(PRD).where(PRD.id == prd_id, PRD.created_by == user_id)
    )
    prd = result.scalar_one_or_none()

    if not prd:
        return ResponseBuilder.error("PRD not found", code="NOT_FOUND")

    if format == "json":
        content = json.dumps(prd.ai_generated, ensure_ascii=False, indent=2)
    else:
        content = prd.markdown or "# PRD Content"

    return ResponseBuilder.success({
        "format": format,
        "content": content,
        "filename": f"prd_{prd_id}.{format}"
    })
