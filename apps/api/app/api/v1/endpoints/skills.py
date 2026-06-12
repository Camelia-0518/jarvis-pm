"""技能系统 API 端点

提供技能定义查询、技能执行、执行历史管理等功能。
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

import asyncio
import logging
import traceback

from app.services.skill_processor import skill_processor
from app.services.skill_processor_enhanced import SkillProcessorEnhanced
from app.core.config import settings
from app.core.responses import ResponseBuilder
from app.core.rate_limit import rate_limit
from app.core.database import get_db
from app.models.skill_execution import SkillExecution
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

router = APIRouter()

logger = logging.getLogger(__name__)


# ============== Request/Response Models ==============

class SkillParameter(BaseModel):
    """技能参数定义"""
    name: str
    label: str
    type: Literal["string", "number", "boolean", "select", "textarea", "array"]
    description: Optional[str] = None
    required: bool = False
    defaultValue: Optional[Any] = None
    options: Optional[List[dict]] = None
    placeholder: Optional[str] = None


class SkillDefinition(BaseModel):
    """技能定义"""
    id: str
    name: str
    description: str
    agentRole: str
    category: Literal["analysis", "design", "development", "review", "medical", "planning"]
    parameters: List[SkillParameter]
    outputSchema: Dict[str, Any]
    examples: Optional[List[dict]] = None
    icon: Optional[str] = None
    tags: Optional[List[str]] = None


class SkillExecutionRequest(BaseModel):
    """技能执行请求"""
    skillId: str = Field(..., min_length=1, description="技能ID")
    inputs: Dict[str, Any] = Field(..., description="输入参数")
    context: Optional[Dict[str, str]] = Field(
        default=None,
        description="执行上下文（项目ID、对话ID等）"
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="执行选项（temperature、maxTokens等）"
    )


class SkillExecutionResponse(BaseModel):
    """技能执行响应"""
    success: bool
    skillId: str
    output: Dict[str, Any]
    formattedOutput: Optional[str] = None
    executionTime: int
    tokenUsage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class SkillExecutionRecord(BaseModel):
    """技能执行记录"""
    id: str
    skillId: str
    skillName: str
    agentRole: str
    inputs: Dict[str, Any]
    output: Dict[str, Any]
    status: Literal["pending", "running", "completed", "failed"]
    createdAt: datetime
    completedAt: Optional[datetime] = None
    executionTime: Optional[int] = None
    error: Optional[str] = None


class SkillValidationRequest(BaseModel):
    """技能输入验证请求"""
    skillId: str
    inputs: Dict[str, Any]


class SkillValidationResponse(BaseModel):
    """技能输入验证响应"""
    valid: bool
    errors: List[str]


class SkillFilterOptions(BaseModel):
    """技能筛选选项"""
    category: Optional[str] = None
    agentRole: Optional[str] = None
    searchQuery: Optional[str] = None


# ============== Endpoints ==============

@rate_limit(requests=100, window=60)
@router.get("/definitions", response_model=dict)
async def get_all_skills(
    category: Optional[str] = None,
    agent_role: Optional[str] = None,
    search: Optional[str] = None
):
    """获取所有技能定义

    可选筛选参数：
    - category: 技能分类
    - agent_role: Agent 角色
    - search: 搜索关键词
    """
    try:
        skills = skill_processor.get_all_skills()

        # 应用筛选
        if category:
            skills = [s for s in skills if s.get("category") == category]

        if agent_role:
            skills = [s for s in skills if s.get("agentRole") == agent_role]

        if search:
            search_lower = search.lower()
            skills = [
                s for s in skills
                if search_lower in s.get("name", "").lower()
                or search_lower in s.get("description", "").lower()
                or any(search_lower in tag.lower() for tag in s.get("tags", []))
            ]

        return ResponseBuilder.success({
            "skills": skills,
            "total": len(skills)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=30, window=60)
@router.post("/definitions/reload", response_model=dict)
async def reload_skills():
    """重新加载技能定义（热更新，无需重启后端进程）"""
    try:
        result = skill_processor.reload_skills()
        return ResponseBuilder.success(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=100, window=60)
@router.get("/definitions/{skill_id}", response_model=dict)
async def get_skill_by_id(skill_id: str):
    """获取特定技能定义"""
    try:
        skill = skill_processor.get_skill_by_id(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail=f"技能 {skill_id} 不存在")

        return ResponseBuilder.success(skill)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=100, window=60)
@router.get("/by-role/{role}", response_model=dict)
async def get_skills_by_role(role: str):
    """根据 Agent 角色获取技能列表"""
    try:
        skills = skill_processor.get_skills_by_role(role)
        return ResponseBuilder.success({
            "role": role,
            "skills": skills,
            "total": len(skills)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=100, window=60)
@router.get("/categories", response_model=dict)
async def get_skill_categories():
    """获取技能分类列表"""
    try:
        categories = [
            {"value": "analysis", "label": "分析", "icon": "🔍"},
            {"value": "design", "label": "设计", "icon": "🎨"},
            {"value": "development", "label": "开发", "icon": "💻"},
            {"value": "review", "label": "评审", "icon": "👀"},
            {"value": "medical", "label": "医疗", "icon": "🏥"},
            {"value": "planning", "label": "规划", "icon": "📅"},
        ]
        return ResponseBuilder.success(categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=30, window=60)
@router.post("/validate", response_model=dict)
async def validate_skill_input(request: SkillValidationRequest):
    """验证技能输入参数"""
    try:
        skill = skill_processor.get_skill_by_id(request.skillId)
        if not skill:
            raise HTTPException(
                status_code=404,
                detail=f"技能 {request.skillId} 不存在"
            )

        errors = []
        parameters = skill.get("parameters", [])

        for param in parameters:
            if param.get("required"):
                param_name = param.get("name")
                value = request.inputs.get(param_name)
                if value is None or value == "":
                    errors.append(f"参数 '{param.get('label', param_name)}' 是必填项")

        return ResponseBuilder.success({
            "valid": len(errors) == 0,
            "errors": errors
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=10, window=60)
@router.post("/execute")
async def execute_skill(
    request: SkillExecutionRequest,
    db: AsyncSession = Depends(get_db)
):
    """同步执行技能

    等待 AI 处理完成并返回结果。
    适用于执行时间较短（<30秒）的技能。
    """
    try:
        # 验证技能存在
        skill = skill_processor.get_skill_by_id(request.skillId)
        if not skill:
            raise HTTPException(
                status_code=404,
                detail=f"技能 {request.skillId} 不存在"
            )

        # 直接使用增强版处理器执行技能（确保真实AI调用，不使用mock缓存）
        start_time = datetime.now()
        enhanced = SkillProcessorEnhanced(
            llm_provider=settings.DEFAULT_AI_PROVIDER,
            enable_cache=False
        )
        result = await enhanced.execute_skill(
            skill_id=request.skillId,
            inputs=request.inputs,
            context=request.context or {},
            skip_cache=True
        )
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 构建响应
        response = {
            "success": result.get("success", False),
            "skillId": request.skillId,
            "output": result.get("output", {}),
            "formattedOutput": result.get("formatted_output"),
            "executionTime": execution_time,
        }

        if result.get("token_usage"):
            response["tokenUsage"] = result["token_usage"]

        if result.get("error"):
            response["error"] = result["error"]

        # 持久化执行记录
        execution_record = SkillExecution(
            skill_id=request.skillId,
            project_id=request.context.get("project_id") if request.context else None,
            inputs=request.inputs,
            output=result.get("output", {}),
            success=result.get("success", False),
            execution_time_ms=execution_time,
            token_usage=result.get("token_usage", {}),
            error_message=result.get("error"),
        )
        db.add(execution_record)
        await db.commit()
        await db.refresh(execution_record)
        response["executionId"] = execution_record.id

        return ResponseBuilder.success(response)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=5, window=60)
@router.post("/execute-async")
async def execute_skill_async(
    request: SkillExecutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """异步执行技能

    立即返回执行ID，后台执行技能。
    适用于执行时间较长或需要流式输出的场景。
    """
    try:
        # 验证技能存在
        skill = skill_processor.get_skill_by_id(request.skillId)
        if not skill:
            raise HTTPException(
                status_code=404,
                detail=f"技能 {request.skillId} 不存在"
            )

        # 持久化 pending 执行记录
        execution_record = SkillExecution(
            skill_id=request.skillId,
            project_id=request.context.get("project_id") if request.context else None,
            inputs=request.inputs,
            output={},
            success=False,
            execution_time_ms=0,
            token_usage={},
            error_message=None,
        )
        db.add(execution_record)
        await db.commit()
        await db.refresh(execution_record)

        # 后台执行
        background_tasks.add_task(
            _execute_skill_background,
            execution_record.id,
            request.skillId,
            request.inputs,
            request.context,
            request.options
        )

        return ResponseBuilder.success({
            "executionId": execution_record.id,
            "status": "pending",
            "message": "技能执行已启动，请通过 /executions/{id} 查询结果"
        })

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_skill_background(
    execution_id: str,
    skill_id: str,
    inputs: Dict[str, Any],
    context: Optional[Dict[str, str]],
    options: Optional[Dict[str, Any]]
):
    """后台执行技能"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # 执行技能
            start_time = datetime.now()
            result = await skill_processor.execute_skill(
                skill_id=skill_id,
                inputs=inputs,
                context=context,
                options=options
            )
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # 更新执行记录
            record = await db.get(SkillExecution, execution_id)
            if record:
                record.output = result.get("output", {})
                record.success = result.get("success", False)
                record.execution_time_ms = execution_time
                record.token_usage = result.get("token_usage", {})
                record.error_message = result.get("error")
                await db.commit()

        except Exception as e:
            # 更新失败状态
            tb = traceback.format_exc()
            logger.error(
                "Skill background execution failed: execution_id=%s skill=%s error=%s\n%s",
                execution_id, skill_id, e, tb
            )
            record = await db.get(SkillExecution, execution_id)
            if record:
                record.success = False
                record.error_message = f"{type(e).__name__}: {e}"
                await db.commit()
            raise


@rate_limit(requests=100, window=60)
@router.get("/executions/{execution_id}", response_model=dict)
async def get_execution_status(
    execution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取技能执行状态"""
    try:
        record = await db.get(SkillExecution, execution_id)
        if not record:
            raise HTTPException(status_code=404, detail="执行记录不存在")

        return ResponseBuilder.success(record.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=100, window=60)
@router.get("/executions", response_model=dict)
async def list_executions(
    skill_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """获取执行历史列表"""
    try:
        query = select(SkillExecution).order_by(desc(SkillExecution.created_at))

        if skill_id:
            query = query.where(SkillExecution.skill_id == skill_id)

        if status is not None:
            is_success = status.lower() == "completed"
            query = query.where(SkillExecution.success == is_success)

        # 分页
        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        records = result.scalars().all()

        return ResponseBuilder.paginated(
            data=[r.to_dict() for r in records],
            page=offset // limit + 1,
            limit=limit,
            total=total
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=100, window=60)
@router.get("/examples/{skill_id}", response_model=dict)
async def get_skill_examples(skill_id: str):
    """获取技能的示例输入"""
    try:
        skill = skill_processor.get_skill_by_id(skill_id)
        if not skill:
            raise HTTPException(
                status_code=404,
                detail=f"技能 {skill_id} 不存在"
            )

        examples = skill.get("examples", [])
        return ResponseBuilder.success(examples)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rate_limit(requests=100, window=60)
@router.get("/agent-roles", response_model=dict)
async def get_agent_roles():
    """获取所有 Agent 角色及其技能"""
    try:
        roles = {
            "ceo": {
                "name": "产品战略官",
                "description": "负责产品战略、需求分析和商业逻辑",
                "skills": skill_processor.get_skills_by_role("ceo")
            },
            "designer": {
                "name": "体验设计师",
                "description": "负责 UI/UX 设计和用户流程",
                "skills": skill_processor.get_skills_by_role("designer")
            },
            "engManager": {
                "name": "工程经理",
                "description": "负责技术架构和代码实现",
                "skills": skill_processor.get_skills_by_role("engManager")
            },
            "medical-officer": {
                "name": "医疗业务专家",
                "description": "负责医疗业务评审",
                "skills": skill_processor.get_skills_by_role("medical-officer")
            },
            "compliance-officer": {
                "name": "合规专员",
                "description": "负责合规检查",
                "skills": skill_processor.get_skills_by_role("compliance-officer")
            },
            "multi-branch-pm": {
                "name": "多院区产品经理",
                "description": "负责多院区需求分析",
                "skills": skill_processor.get_skills_by_role("multi-branch-pm")
            },
        }

        return ResponseBuilder.success(roles)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))