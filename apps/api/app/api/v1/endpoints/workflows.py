"""Workflow API endpoints

提供工作流定义查询、执行、流式执行等功能。
"""

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
import json
import time
from cachetools import TTLCache

from app.services.workflow_engine import WorkflowEngine, STANDARD_WORKFLOWS
from app.services.skill_processor import skill_processor
from app.core.responses import ResponseBuilder

router = APIRouter()

# In-memory execution storage with TTL to prevent memory leaks
# maxsize=1000, ttl=3600s (1 hour) — old records auto-evicted
execution_records: TTLCache = TTLCache(maxsize=1000, ttl=3600)


# ============== Request/Response Models ==============

class WorkflowExecuteRequest(BaseModel):
    workflow_name: str = Field(..., min_length=1, description="工作流名称/ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="初始输入参数")
    project_id: Optional[str] = Field(default=None, description="关联项目ID")
    context: Optional[Dict[str, str]] = Field(default=None, description="执行上下文")


class WorkflowStepResult(BaseModel):
    step_name: str
    skill_id: str
    status: str
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration: Optional[float] = None


class WorkflowExecuteResponse(BaseModel):
    execution_id: str
    workflow: str
    completed: bool
    results: List[WorkflowStepResult]
    outputs: Dict[str, Any]
    duration: Optional[float] = None
    error: Optional[str] = None


# ============== Helpers ==============

def _create_skill_executor():
    """Create a skill executor bound to the real skill processor."""
    async def executor(skill_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        result = await skill_processor.execute_skill(skill_id, inputs)
        if not result.get("success"):
            raise Exception(result.get("error", "Skill execution failed"))
        output = result.get("output", {})
        # 将 formatted_output 也注入到输出中，方便工作流后续步骤使用
        if "formatted_output" in result and isinstance(output, dict):
            output["formatted_output"] = result["formatted_output"]
        return output
    return executor


# ============== Endpoints ==============

@router.get("/templates", response_model=dict)
async def list_workflows():
    """获取所有预置工作流模板列表"""
    engine = WorkflowEngine(skill_executor=_create_skill_executor())
    return ResponseBuilder.success(engine.get_workflow_list())


@router.get("/templates/{workflow_name}", response_model=dict)
async def get_workflow_detail(workflow_name: str):
    """获取工作流模板详情"""
    engine = WorkflowEngine(skill_executor=_create_skill_executor())
    detail = engine.get_workflow_detail(workflow_name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_name} 不存在")
    return ResponseBuilder.success(detail)


@router.post("/execute", response_model=dict)
async def execute_workflow(request: WorkflowExecuteRequest):
    """同步执行工作流

    按顺序执行工作流中的每个步骤，等待全部完成后返回结果。
    """
    engine = WorkflowEngine(skill_executor=_create_skill_executor())

    if request.workflow_name not in STANDARD_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"工作流 {request.workflow_name} 不存在")

    execution_id = str(uuid.uuid4())

    try:
        result = await engine.execute_workflow(
            workflow_name=request.workflow_name,
            initial_inputs=request.inputs,
            stop_on_error=True
        )

        record = {
            "execution_id": execution_id,
            "workflow": request.workflow_name,
            "project_id": request.project_id,
            "status": "completed" if result.get("completed") else "failed",
            "result": result,
            "context": request.context,
        }
        execution_records[execution_id] = record

        return ResponseBuilder.success({
            "execution_id": execution_id,
            **result
        })
    except Exception as e:
        execution_records[execution_id] = {
            "execution_id": execution_id,
            "workflow": request.workflow_name,
            "project_id": request.project_id,
            "status": "failed",
            "error": str(e),
            "context": request.context,
        }
        raise HTTPException(status_code=500, detail=str(e))


async def _run_workflow_background(execution_id: str, workflow_name: str, inputs: Dict[str, Any], project_id: Optional[str], context: Optional[Dict[str, str]]):
    """后台执行工作流并更新记录"""
    engine = WorkflowEngine(skill_executor=_create_skill_executor())
    try:
        result = await engine.execute_workflow(
            workflow_name=workflow_name,
            initial_inputs=inputs,
            stop_on_error=True
        )
        execution_records[execution_id] = {
            "execution_id": execution_id,
            "workflow": workflow_name,
            "project_id": project_id,
            "status": "completed" if result.get("completed") else "failed",
            "result": result,
            "context": context,
        }
    except Exception as e:
        execution_records[execution_id] = {
            "execution_id": execution_id,
            "workflow": workflow_name,
            "project_id": project_id,
            "status": "failed",
            "error": str(e),
            "context": context,
        }


@router.post("/execute-async", response_model=dict)
async def execute_workflow_async(request: WorkflowExecuteRequest, background_tasks: BackgroundTasks):
    """异步执行工作流

    立即返回 execution_id，工作流在后台执行。
    可通过 /executions/{execution_id} 轮询状态。
    """
    if request.workflow_name not in STANDARD_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"工作流 {request.workflow_name} 不存在")

    execution_id = str(uuid.uuid4())
    execution_records[execution_id] = {
        "execution_id": execution_id,
        "workflow": request.workflow_name,
        "project_id": request.project_id,
        "status": "running",
        "context": request.context,
    }

    background_tasks.add_task(
        _run_workflow_background,
        execution_id,
        request.workflow_name,
        request.inputs,
        request.project_id,
        request.context,
    )

    return ResponseBuilder.success({
        "execution_id": execution_id,
        "workflow": request.workflow_name,
        "status": "running",
        "message": "工作流已提交后台执行，请轮询 /executions/{execution_id} 获取结果"
    })


# Skill chain mapping (matches frontend SKILL_CHAINS)
CHAIN_WORKFLOW_MAP = {
    "from-scratch": "from-scratch",
    "security-review": "security-review",
    "prd-package": "prd-package",
}


class WorkflowChainExecuteRequest(BaseModel):
    chain_id: str = Field(..., min_length=1, description="技能链ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="初始输入参数")
    project_id: Optional[str] = Field(default=None, description="关联项目ID")
    context: Optional[Dict[str, str]] = Field(default=None, description="执行上下文")


@router.post("/execute-chain", response_model=dict)
async def execute_skill_chain(request: WorkflowChainExecuteRequest, background_tasks: BackgroundTasks):
    """执行技能链

    根据 chain_id 映射到对应的工作流定义，在后台异步执行。
    返回 execution_id，前端轮询 /executions/{execution_id} 获取进度和结果。
    """
    workflow_name = CHAIN_WORKFLOW_MAP.get(request.chain_id)
    if not workflow_name:
        raise HTTPException(status_code=404, detail=f"技能链 {request.chain_id} 不存在")

    if workflow_name not in STANDARD_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_name} 未注册")

    execution_id = str(uuid.uuid4())
    execution_records[execution_id] = {
        "execution_id": execution_id,
        "workflow": workflow_name,
        "chain_id": request.chain_id,
        "project_id": request.project_id,
        "status": "running",
        "context": request.context,
        "started_at": time.time(),
    }

    background_tasks.add_task(
        _run_workflow_background,
        execution_id,
        workflow_name,
        request.inputs,
        request.project_id,
        request.context,
    )

    return ResponseBuilder.success({
        "execution_id": execution_id,
        "chain_id": request.chain_id,
        "workflow": workflow_name,
        "status": "running",
        "message": "技能链已提交后台执行，请轮询 /executions/{execution_id} 获取结果"
    })


@router.get("/executions/{execution_id}", response_model=dict)
async def get_execution_status(execution_id: str):
    """获取工作流执行状态"""
    if execution_id not in execution_records:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return ResponseBuilder.success(execution_records[execution_id])


@router.get("/executions", response_model=dict)
async def list_executions(
    workflow: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """获取工作流执行历史列表"""
    records = list(execution_records.values())

    if workflow:
        records = [r for r in records if r.get("workflow") == workflow]
    if status:
        records = [r for r in records if r.get("status") == status]

    total = len(records)
    paginated = records[offset:offset + limit]

    return ResponseBuilder.paginated(
        data=paginated,
        page=offset // limit + 1,
        limit=limit,
        total=total
    )
