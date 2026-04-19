#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent API 路由

提供 Agent 相关的 REST API 端点
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.agents import (
    AgentRegistry, AgentManager, auto_register_agents,
    TaskQueue, get_task_queue, TaskPriority
)
from app.agents.agents import PRDAgent, RequirementAgent
from app.core.responses import ResponseBuilder
from app.core.rate_limit import rate_limit

router = APIRouter()

# 自动注册 Agent
auto_register_agents()

# 初始化管理器和队列
manager = AgentManager()


# ============== Pydantic 模型 ==============

class AgentInfo(BaseModel):
    name: str
    description: str
    version: str
    capabilities: List[str]


class PRDRequest(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    target_users: str = Field(..., min_length=1)
    key_features: List[str] = Field(..., min_items=1)
    constraints: Optional[List[str]] = []
    sections: Optional[List[str]] = None


class RequirementRequest(BaseModel):
    raw_requirements: str = Field(..., min_length=10)
    product_name: Optional[str] = "未命名产品"
    industry: Optional[str] = ""
    analysis_depth: Optional[str] = "standard"


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


# ============== 启动/关闭事件 ==============

@router.on_event("startup")
async def startup():
    queue = get_task_queue(max_workers=2)
    await queue.start()


@router.on_event("shutdown")
async def shutdown():
    queue = get_task_queue()
    await queue.stop()


# ============== Endpoints ==============

@router.get("", response_model=dict)
async def list_agents():
    """列出所有可用的 Agent"""
    registry = AgentRegistry()
    agents = registry.get_all_info()

    return ResponseBuilder.success([
        {
            "name": agent["name"],
            "description": agent["description"],
            "version": agent["version"],
            "capabilities": agent["capabilities"]
        }
        for agent in agents
    ])


@router.get("/stats", response_model=dict)
async def get_stats():
    """获取系统统计信息"""
    queue = get_task_queue()
    return ResponseBuilder.success({
        "queue": queue.get_stats(),
        "manager": manager.get_stats()
    })


@router.post("/prd/generate", response_model=dict)
@rate_limit(requests=10, window=60)  # 10 PRD generations per minute
async def generate_prd(request: PRDRequest, background_tasks: BackgroundTasks):
    """
    提交 PRD 生成任务

    异步执行，返回任务 ID
    """
    queue = get_task_queue()

    input_data = {
        "product_name": request.product_name,
        "description": request.description,
        "target_users": request.target_users,
        "key_features": request.key_features,
        "constraints": request.constraints or [],
        "sections": request.sections or ["background", "user_stories", "functional_requirements"]
    }

    task_id = await queue.submit(
        agent_name="prd_generator",
        input_data=input_data,
        priority=TaskPriority.NORMAL
    )

    return ResponseBuilder.success({
        "task_id": str(task_id),
        "status": "queued",
        "message": "PRD generation task submitted"
    })


@router.post("/requirements/analyze", response_model=dict)
@rate_limit(requests=10, window=60)  # 10 requirement analyses per minute
async def analyze_requirements(request: RequirementRequest):
    """
    提交需求分析任务

    异步执行，返回任务 ID
    """
    queue = get_task_queue()

    input_data = {
        "raw_requirements": request.raw_requirements,
        "product_name": request.product_name,
        "industry": request.industry,
        "analysis_depth": request.analysis_depth
    }

    task_id = await queue.submit(
        agent_name="requirement_analyzer",
        input_data=input_data,
        priority=TaskPriority.NORMAL
    )

    return ResponseBuilder.success({
        "task_id": str(task_id),
        "status": "queued",
        "message": "Requirement analysis task submitted"
    })


@router.get("/tasks", response_model=dict)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """列出任务"""
    queue = get_task_queue()
    tasks = queue.list_tasks(status=status)

    # Manual pagination
    total = len(tasks)
    offset = (page - 1) * limit
    paginated_tasks = tasks[offset:offset + limit]

    return ResponseBuilder.paginated(
        data=[
            {
                "task_id": str(t.id),
                "agent_name": t.agent_name,
                "status": t.status,
                "created_at": t.created_at.isoformat()
            }
            for t in paginated_tasks
        ],
        page=page,
        limit=limit,
        total=total
    )


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task_status(task_id: str):
    """获取任务状态和结果"""
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task ID")

    queue = get_task_queue()
    task = await queue.get_task(task_uuid)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return ResponseBuilder.success({
        "task_id": str(task.id),
        "status": task.status,
        "result": task.result.to_dict() if task.result else None,
        "error": task.error
    })


@router.get("/{agent_name}", response_model=dict)
async def get_agent_info(agent_name: str):
    """获取 Agent 详细信息"""
    registry = AgentRegistry()
    agent_class = registry.get(agent_name)

    if not agent_class:
        raise HTTPException(status_code=404, detail="Agent not found")

    return ResponseBuilder.success({
        "name": agent_class.name,
        "description": agent_class.description,
        "version": agent_class.version,
        "capabilities": agent_class.capabilities,
        "required_tools": agent_class.required_tools
    })
