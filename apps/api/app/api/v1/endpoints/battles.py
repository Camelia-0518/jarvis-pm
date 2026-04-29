"""Battle (Campaign) endpoints"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.models.battle import Battle, BattleStatus
from app.models.project import Project
from app.models.prd import PRD, PRDStatus
from app.services.ai_service import ai_service
from app.api.v1.endpoints.prds import prd_json_to_markdown
import uuid

router = APIRouter()


class BattleDay(BaseModel):
    day: str
    task: str
    status: str = Field(default="pending", pattern="^(pending|in-progress|completed)$")
    tool: str
    notes: Optional[str] = ""


class BattleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""
    project_id: Optional[str] = None
    prd_id: Optional[str] = None
    days: Optional[List[BattleDay]] = None


class BattleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|cancelled)$")
    current_day: Optional[int] = Field(None, ge=1, le=10)
    days: Optional[List[BattleDay]] = None
    project_id: Optional[str] = None
    prd_id: Optional[str] = None


def _default_battle_days() -> List[dict]:
    return [
        {"day": "Day 1", "task": "用户调研", "status": "pending", "tool": "research", "notes": ""},
        {"day": "Day 2", "task": "竞品分析", "status": "pending", "tool": "research", "notes": ""},
        {"day": "Day 3", "task": "PRD框架搭建", "status": "pending", "tool": "prd", "notes": ""},
        {"day": "Day 4", "task": "功能规格撰写", "status": "pending", "tool": "prd", "notes": ""},
        {"day": "Day 5", "task": "评审材料准备", "status": "pending", "tool": "review", "notes": ""},
    ]


@router.get("", response_model=dict)
async def list_battles(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """List all battles for current user"""
    query = select(Battle).where(Battle.created_by == user_id)

    if status_filter:
        try:
            status_enum = BattleStatus(status_filter)
            query = query.where(Battle.status == status_enum)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(desc(Battle.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    battles = result.scalars().all()

    items = []
    for b in battles:
        items.append({
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "project_id": b.project_id,
            "prd_id": b.prd_id,
            "status": b.status.value,
            "current_day": b.current_day,
            "total_days": b.total_days,
            "days": b.days or _default_battle_days(),
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        })

    return ResponseBuilder.paginated(data=items, page=page, limit=limit, total=total)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_battle(
    data: BattleCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new battle campaign"""
    # Validate project_id if provided
    if data.project_id:
        result = await db.execute(
            select(Project).where(Project.id == data.project_id, Project.created_by == user_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

    days_data = [d.model_dump() for d in data.days] if data.days else _default_battle_days()

    battle = Battle(
        name=data.name,
        description=data.description or "",
        created_by=user_id,
        project_id=data.project_id,
        prd_id=data.prd_id,
        status=BattleStatus.ACTIVE,
        current_day=1,
        total_days=len(days_data),
        days=days_data,
    )

    db.add(battle)
    await db.commit()
    await db.refresh(battle)

    return ResponseBuilder.created({
        "id": battle.id,
        "name": battle.name,
        "description": battle.description,
        "project_id": battle.project_id,
        "prd_id": battle.prd_id,
        "status": battle.status.value,
        "current_day": battle.current_day,
        "total_days": battle.total_days,
        "days": battle.days,
        "created_at": battle.created_at.isoformat() if battle.created_at else None,
    })


@router.get("/{battle_id}", response_model=dict)
async def get_battle(
    battle_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get battle by ID"""
    result = await db.execute(
        select(Battle).where(Battle.id == battle_id, Battle.created_by == user_id)
    )
    battle = result.scalar_one_or_none()

    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    return ResponseBuilder.success({
        "id": battle.id,
        "name": battle.name,
        "description": battle.description,
        "project_id": battle.project_id,
        "prd_id": battle.prd_id,
        "status": battle.status.value,
        "current_day": battle.current_day,
        "total_days": battle.total_days,
        "days": battle.days or _default_battle_days(),
        "created_at": battle.created_at.isoformat() if battle.created_at else None,
        "updated_at": battle.updated_at.isoformat() if battle.updated_at else None,
    })


@router.put("/{battle_id}", response_model=dict)
async def update_battle(
    battle_id: str,
    data: BattleUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update battle"""
    result = await db.execute(
        select(Battle).where(Battle.id == battle_id, Battle.created_by == user_id)
    )
    battle = result.scalar_one_or_none()

    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    if data.name is not None:
        battle.name = data.name
    if data.description is not None:
        battle.description = data.description
    if data.status is not None:
        battle.status = BattleStatus(data.status)
    if data.current_day is not None:
        battle.current_day = data.current_day
    if data.days is not None:
        battle.days = [d.model_dump() for d in data.days]
    if data.project_id is not None:
        battle.project_id = data.project_id
    if data.prd_id is not None:
        battle.prd_id = data.prd_id

    await db.commit()
    await db.refresh(battle)

    return ResponseBuilder.success({
        "id": battle.id,
        "name": battle.name,
        "description": battle.description,
        "project_id": battle.project_id,
        "prd_id": battle.prd_id,
        "status": battle.status.value,
        "current_day": battle.current_day,
        "total_days": battle.total_days,
        "days": battle.days or _default_battle_days(),
        "updated_at": battle.updated_at.isoformat() if battle.updated_at else None,
    })


@router.delete("/{battle_id}", response_model=dict)
async def delete_battle(
    battle_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete battle"""
    result = await db.execute(
        select(Battle).where(Battle.id == battle_id, Battle.created_by == user_id)
    )
    battle = result.scalar_one_or_none()

    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    await db.delete(battle)
    await db.commit()

    return ResponseBuilder.success({"id": battle_id, "deleted": True})


async def _execute_day_tool(
    day_idx: int,
    day_task: str,
    battle: Battle,
    user_id: str,
    db: AsyncSession,
) -> str:
    """Auto-execute the AI tool for a given battle day."""
    project_id = battle.project_id
    if not project_id:
        return "未关联项目，跳过自动执行"

    # Query project for context
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.created_by == user_id)
    )
    project = result.scalar_one_or_none()
    project_name = project.name if project else "未命名项目"
    project_desc = project.description if project else ""
    industry = project.industry if project else "general"

    notes = ""

    if day_idx == 0:
        # Day 1: user research
        prompt = f"""为项目「{project_name}」生成用户研究报告。
项目描述: {project_desc}
行业: {industry}

要求：
1. 输出研究发现、关键洞察、行动建议
2. 使用 Markdown 格式，结构清晰"""
        content = await ai_service.chat(prompt)
        notes = content

    elif day_idx == 1:
        # Day 2: competitor analysis
        prompt = f"""为项目「{project_name}」生成竞品分析报告。
项目描述: {project_desc}
行业: {industry}

要求：
1. 识别 2-3 个核心竞品
2. 输出对比矩阵和差异化策略
3. 使用 Markdown 格式"""
        content = await ai_service.chat(prompt)
        notes = content

    elif day_idx == 2:
        # Day 3: PRD framework generation - create a PRD if none exists
        result = await db.execute(
            select(PRD).where(PRD.project_id == project_id, PRD.created_by == user_id).order_by(desc(PRD.created_at))
        )
        existing_prd = result.scalars().first()
        template = industry if industry in ("medical", "saas", "ecommerce") else "default"
        if existing_prd:
            notes = f"已存在 PRD：{existing_prd.title}。系统自动补充了背景与目标章节内容。"
            # Generate chapter 1 and append
            try:
                ai_result = await ai_service.generate_prd_chapter(
                    chapter="1",
                    prompt=f"项目：{project_name}，描述：{project_desc}",
                    context=existing_prd.ai_generated if existing_prd.ai_generated else {},
                    industry=industry,
                )
                new_md = ai_result.get("markdown", "")
                existing_prd.markdown = (existing_prd.markdown or "") + "\n\n" + new_md
                content_struct = existing_prd.content or {"chapters": {}, "template": template, "industry": industry}
                content_struct["chapters"] = content_struct.get("chapters", {})
                content_struct["chapters"]["1"] = {
                    "title": ai_result.get("content", {}).get("sections", [{}])[0].get("title", "背景与目标"),
                    "content": new_md,
                    "status": "generated"
                }
                existing_prd.content = content_struct
            except Exception as e:
                notes = f"AI生成失败：{str(e)}。请检查API配置。"
        else:
            ai_result = await ai_service.generate_prd(
                title=project_name,
                description=project_desc or project_name,
                industry=industry,
                template=template,
            )
            markdown = prd_json_to_markdown(ai_result, project_name)
            chapters = {}
            outline = ai_result.get("outline", {}) if isinstance(ai_result.get("outline"), dict) else {}
            for sec in outline.get("sections", []):
                if isinstance(sec, dict):
                    chapter_num = str(sec.get("chapter", ""))
                    chapters[chapter_num] = {
                        "title": sec.get("title", ""),
                        "content": "\n".join([f"- {kp}" for kp in sec.get("key_points", [])]),
                        "status": "draft"
                    }
            new_prd = PRD(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=f"{project_name} PRD",
                version="1.0",
                status=PRDStatus.DRAFT,
                content={"chapters": chapters, "template": template, "industry": industry},
                markdown=markdown,
                ai_generated=ai_result,
                created_by=user_id,
            )
            db.add(new_prd)
            notes = f"已自动生成 PRD：{project_name} PRD，包含完整 8 章结构。"

    elif day_idx == 3:
        # Day 4: feature specification (generate chapter 4)
        result = await db.execute(
            select(PRD).where(PRD.project_id == project_id, PRD.created_by == user_id).order_by(desc(PRD.created_at))
        )
        prd = result.scalars().first()
        if prd:
            try:
                ai_result = await ai_service.generate_prd_chapter(
                    chapter="4",
                    prompt=f"项目：{project_name}，描述：{project_desc}",
                    context=prd.ai_generated if prd.ai_generated else {},
                    industry=industry,
                )
                new_md = ai_result.get("markdown", "")
                prd.markdown = (prd.markdown or "") + "\n\n" + new_md
                content_struct = prd.content or {"chapters": {}, "template": "standard", "industry": industry}
                content_struct["chapters"] = content_struct.get("chapters", {})
                content_struct["chapters"]["4"] = {
                    "title": ai_result.get("content", {}).get("sections", [{}])[0].get("title", "功能规格"),
                    "content": new_md,
                    "status": "generated"
                }
                prd.content = content_struct
                notes = f"已为 PRD「{prd.title}」生成功能规格章节。"
            except Exception as e:
                notes = f"AI生成失败：{str(e)}。请检查API配置。"
        else:
            notes = "未找到 PRD，请先完成 Day 3。"

    elif day_idx == 4:
        # Day 5: review materials
        result = await db.execute(
            select(PRD).where(PRD.project_id == project_id, PRD.created_by == user_id).order_by(desc(PRD.created_at))
        )
        prd = result.scalars().first()
        prd_markdown = prd.markdown if prd else ""
        if prd_markdown:
            prompt = f"""基于以下 PRD 内容，生成一份评审会议议程。

PRD 内容：
{prd_markdown}

要求：
1. 基于 PRD 的具体内容，引用实际的功能点
2. 输出 Markdown 格式，包含议程、时间分配、参会人建议"""
            content = await ai_service.chat(prompt)
            notes = content
        else:
            prompt = f"""为项目「{project_name}」生成一份评审会议议程。
项目描述: {project_desc}

要求：
1. 输出 Markdown 格式，包含议程、时间分配、参会人建议"""
            content = await ai_service.chat(prompt)
            notes = content

    else:
        notes = ""

    return notes


@router.post("/{battle_id}/advance", response_model=dict)
async def advance_battle(
    battle_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Advance battle to next day and mark current day as completed. Auto-executes AI tool if project linked."""
    result = await db.execute(
        select(Battle).where(Battle.id == battle_id, Battle.created_by == user_id)
    )
    battle = result.scalar_one_or_none()

    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    days = battle.days or _default_battle_days()
    current = battle.current_day - 1  # 0-based index

    # Auto-execute AI tool for current day before advancing
    if 0 <= current < len(days) and battle.project_id:
        days[current]["status"] = "in-progress"
        try:
            ai_notes = await _execute_day_tool(
                day_idx=current,
                day_task=days[current].get("task", ""),
                battle=battle,
                user_id=user_id,
                db=db,
            )
            days[current]["notes"] = ai_notes
            days[current]["status"] = "completed"
        except Exception as e:
            days[current]["notes"] = f"AI 执行失败: {str(e)}"
            days[current]["status"] = "completed"
    elif 0 <= current < len(days):
        days[current]["status"] = "completed"

    if battle.current_day < len(days):
        battle.current_day += 1
        next_idx = battle.current_day - 1
        if 0 <= next_idx < len(days) and days[next_idx]["status"] == "pending":
            days[next_idx]["status"] = "in-progress"
    else:
        battle.status = BattleStatus.COMPLETED

    battle.days = days
    await db.commit()
    await db.refresh(battle)

    return ResponseBuilder.success({
        "id": battle.id,
        "current_day": battle.current_day,
        "status": battle.status.value,
        "days": battle.days,
    })
