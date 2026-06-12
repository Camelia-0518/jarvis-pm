"""PRD 评审批注 API 端点"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.core.permissions import require_project_owner, require_resource_owner
from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.prd_revision_task import PRDRevisionTask
from app.models.prd import PRD
from app.models.state_machine import annotation_sm
from app.core.exceptions import AppException

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


@rate_limit(requests=30, window=60)
@router.post("", response_model=dict)
async def create_annotation(
    prd_id: str,
    request: AnnotationCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """创建评审批注"""
    # Verify PRD exists and belongs to user
    prd = await require_resource_owner(db, PRD, prd_id, user_id)

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


@rate_limit(requests=100, window=60)
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
    await require_resource_owner(db, PRD, prd_id, user_id)
    query = select(PRDAnnotation).where(PRDAnnotation.prd_id == prd_id, PRDAnnotation.deleted_at.is_(None)).order_by(desc(PRDAnnotation.created_at))

    if status:
        query = query.where(PRDAnnotation.status == AnnotationStatus(status))
    if chapter_num:
        query = query.where(PRDAnnotation.chapter_num == chapter_num)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # 查询关联的任务信息
    task_ids = [a.revision_task_id for a in items if a.revision_task_id]
    task_map = {}
    if task_ids:
        task_result = await db.execute(
            select(PRDRevisionTask).where(PRDRevisionTask.id.in_(task_ids))
        )
        for t in task_result.scalars().all():
            task_map[t.id] = {
                "id": t.id,
                "title": t.title,
                "status": t.status,
            }

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
            "revision_task": task_map.get(a.revision_task_id) if a.revision_task_id else None,
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


@rate_limit(requests=30, window=60)
@router.put("/{annotation_id}", response_model=dict)
async def update_annotation(
    prd_id: str,
    annotation_id: str,
    request: AnnotationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """更新批注（内容或状态）"""
    await require_resource_owner(db, PRD, prd_id, user_id)
    result = await db.execute(
        select(PRDAnnotation).where(
            PRDAnnotation.id == annotation_id,
            PRDAnnotation.prd_id == prd_id,
            PRDAnnotation.deleted_at.is_(None),
        )
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise AppException("批注不存在", code="NOT_FOUND", status_code=404)

    if request.content is not None:
        annotation.content = request.content
    if request.status is not None:
        annotation_sm.transition(annotation, request.status)
        if request.status == "resolved":
            from sqlalchemy.sql import func as sql_func
            annotation.resolved_at = sql_func.now()
            annotation.resolved_by = user_id

    await db.commit()
    await db.refresh(annotation)

    return ResponseBuilder.success({"id": annotation.id, "message": "批注已更新"})


@rate_limit(requests=20, window=60)
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
            PRDAnnotation.created_by == user_id,
            PRDAnnotation.deleted_at.is_(None),
        )
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise AppException("批注不存在或无权删除", code="NOT_FOUND", status_code=404)

    annotation.soft_delete()
    await db.commit()

    return ResponseBuilder.success({"message": "批注已删除"})


@rate_limit(requests=30, window=60)
@router.post("/{annotation_id}/convert-to-task", response_model=dict)
async def convert_to_task(
    prd_id: str,
    annotation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """快捷接口：将批注转为修改任务"""
    await require_resource_owner(db, PRD, prd_id, user_id)
    # 验证批注
    result = await db.execute(
        select(PRDAnnotation).where(
            PRDAnnotation.id == annotation_id,
            PRDAnnotation.prd_id == prd_id,
            PRDAnnotation.deleted_at.is_(None),
        )
    )
    annotation = result.scalar_one_or_none()
    if not annotation:
        raise AppException("批注不存在", code="NOT_FOUND", status_code=404)

    if annotation.revision_task_id:
        raise AppException("该批注已关联修改任务", code="CONFLICT", status_code=409)

    # 创建任务
    task = PRDRevisionTask(
        prd_id=prd_id,
        annotation_id=annotation_id,
        title=f"[{annotation.annotation_type.value if annotation.annotation_type else '批注'}] {annotation.content[:50]}...",
        description=annotation.content,
        assigned_to=user_id,
        created_by=user_id,
        status="todo",
    )
    db.add(task)
    await db.flush()

    annotation.revision_task_id = task.id
    await db.commit()
    await db.refresh(task)

    return ResponseBuilder.created({
        "id": task.id,
        "annotation_id": annotation_id,
        "title": task.title,
        "status": task.status,
        "message": "已转为修改任务"
    })


@rate_limit(requests=100, window=60)
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
        .where(PRDAnnotation.prd_id == prd_id, PRDAnnotation.deleted_at.is_(None))
        .group_by(PRDAnnotation.status)
    )

    stats = {row.status.value: row.count for row in result.all()}
    return ResponseBuilder.success({
        "open": stats.get("open", 0),
        "resolved": stats.get("resolved", 0),
        "dismissed": stats.get("dismissed", 0),
        "total": sum(stats.values()),
    })


@rate_limit(requests=5, window=60)
@router.post("/auto-review", response_model=dict)
async def auto_review(
    prd_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """AI 自动评审 PRD，自动创建 issue 批注"""
    from app.models.prd import PRD
    from app.agents.llm_client import create_default_client
    import json
    import re

    # 读取 PRD 内容
    prd_result = await db.execute(select(PRD).where(PRD.id == prd_id, PRD.deleted_at.is_(None)))
    prd = prd_result.scalar_one_or_none()
    if not prd:
        raise AppException("PRD 不存在", code="NOT_FOUND", status_code=404)

    content = prd.markdown or ""
    if not content or len(content.strip()) < 100:
        raise AppException("PRD 内容太短，无法评审", code="BAD_REQUEST", status_code=400)

    # 调用 LLM 评审
    llm = create_default_client()

    prompt = f"""你是资深产品经理评审专家。请对以下 PRD 进行结构化评审，找出具体问题。

评审维度（严格检查）：
1. MVP边界：是否明确定义了一期/二期？每个功能点是否标注了一期或二期？
2. 状态机：是否包含状态转换图（Mermaid）和状态转换表（Markdown表格）？
3. 流程图：核心业务流程是否使用 Mermaid/PlantUML 泳道图？
4. 信息架构：是否包含信息架构图(IA)和核心页面字段清单？
5. 验收标准：用户故事是否使用 Given-When-Then 格式？
6. 对账规则：如涉及支付/财务，是否明确长款/短款/单边账处理？
7. 章节编号：是否存在重复编号（如"1. 1."）？
8. 合规要求：是否覆盖行业合规要点？

输出要求（必须严格遵循 JSON 格式）：
```json
[
  {{
    "chapter": "章节标题或编号",
    "selected_text": "PRD中相关的原文片段（不超过100字）",
    "issue_type": "missing|incorrect|unclear|format",
    "severity": "critical|high|medium|low",
    "content": "具体问题描述 + 整改建议"
  }}
]
```

如果没有问题，返回空数组 []。

---
PRD 内容：
{content[:8000]}
"""

    try:
        response = await llm.chat([
            {"role": "system", "content": "你是一位严格的产品经理评审专家，只输出 JSON 数组，不输出其他文字。"},
            {"role": "user", "content": prompt}
        ])
    except Exception as e:
        raise AppException(f"AI 评审失败: {str(e)}", code="LLM_ERROR", status_code=503)

    # 解析 JSON
    issues = []
    try:
        # 尝试从代码块中提取 JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = response.strip()

        # 如果 LLM 有额外文字，尝试找到第一个 [ 和最后一个 ]
        start = json_str.find('[')
        end = json_str.rfind(']')
        if start != -1 and end != -1 and end > start:
            json_str = json_str[start:end+1]

        issues = json.loads(json_str)
        if not isinstance(issues, list):
            issues = []
    except Exception:
        issues = []

    # 过滤无效项
    valid_issues = [i for i in issues if isinstance(i, dict) and i.get("content")]

    # 批量创建批注
    created_count = 0
    for issue in valid_issues[:20]:  # 最多创建 20 个，避免刷屏
        selected = issue.get("selected_text", "") or ""
        if len(selected) > 1000:
            selected = selected[:997] + "..."

        annotation = PRDAnnotation(
            prd_id=prd_id,
            chapter_title=issue.get("chapter", "")[:200] or None,
            selected_text=selected or None,
            content=f"[{issue.get('severity', 'medium').upper()}] {issue.get('issue_type', 'issue')} — {issue.get('content', '')}"[:2000],
            annotation_type=AnnotationType.ISSUE,
            created_by=user_id,
        )
        db.add(annotation)
        created_count += 1

    await db.commit()

    return ResponseBuilder.success({
        "message": f"AI 评审完成，发现 {len(valid_issues)} 个问题，已创建 {created_count} 条批注",
        "issues_found": len(valid_issues),
        "annotations_created": created_count,
        "sample_issues": [{"chapter": i.get("chapter"), "severity": i.get("severity"), "content": i.get("content", "")[:100]} for i in valid_issues[:3]],
    })


@router.post("/{annotation_id}/fix", response_model=dict)
async def fix_annotation(
    prd_id: str,
    annotation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """AI 修复批注：根据批注内容自动修改 PRD"""
    from app.models.prd import PRD
    from app.agents.llm_client import create_default_client

    # Load annotation
    ann_result = await db.execute(
        select(PRDAnnotation).where(
            PRDAnnotation.id == annotation_id,
            PRDAnnotation.prd_id == prd_id,
        )
    )
    annotation = ann_result.scalar_one_or_none()
    if not annotation:
        raise AppException("批注不存在", code="NOT_FOUND", status_code=404)

    # Load PRD
    prd_result = await db.execute(select(PRD).where(PRD.id == prd_id, PRD.deleted_at.is_(None)))
    prd = prd_result.scalar_one_or_none()
    if not prd:
        raise AppException("PRD 不存在", code="NOT_FOUND", status_code=404)

    prd_content = prd.markdown or ""
    issue = annotation.content or ""

    # Call LLM to fix
    llm = create_default_client()
    prompt = f"""你是资深产品经理，负责根据评审意见修复 PRD 文档。

## 当前 PRD 文档
{prd_content[:8000]}

## 需要修复的问题
{issue[:1000]}

## 修复要求
1. 只修改与问题直接相关的部分，保持其他内容完全不变
2. 确保修改后的内容与文档整体风格一致
3. 如果问题涉及缺失内容（如缺少流程图、状态机），请补充完整
4. 输出修改后的**完整 PRD 文档**（Markdown 格式）
5. 不要输出任何解释或说明，直接输出修复后的完整文档"""

    try:
        response = await llm.chat([
            {"role": "system", "content": "你是一位产品经理，根据评审意见修复 PRD 文档。只输出修复后的完整 Markdown 文档，不要输出其他内容。"},
            {"role": "user", "content": prompt}
        ])
    except Exception as e:
        raise AppException(f"AI 修复失败: {str(e)}", code="LLM_ERROR", status_code=503)

    # Clean response - extract markdown
    fixed_content = response.strip()
    # Remove markdown code block wrapper if present
    if fixed_content.startswith("```markdown"):
        fixed_content = fixed_content[len("```markdown"):].strip()
    if fixed_content.startswith("```"):
        lines = fixed_content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        fixed_content = "\n".join(lines).strip()

    return ResponseBuilder.success({
        "fixed_content": fixed_content,
        "annotation_id": annotation_id,
        "message": "AI 修复建议已生成",
    })