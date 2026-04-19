#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 管理器

提供 Agent 实例管理、任务调度和执行监控
"""

import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

import asyncio
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4, UUID
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from .base import BaseAgent, AgentResult, AgentState
from .registry import AgentRegistry
from .llm_client import create_default_client


@dataclass
class TaskRecord:
    """任务记录"""
    id: UUID
    agent_name: str
    input_data: Dict[str, Any]
    status: AgentState
    result: Optional[AgentResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AgentManager:
    """
    Agent 管理器

    管理 Agent 实例的生命周期和任务执行
    """

    def __init__(self):
        """初始化管理器"""
        self.registry = AgentRegistry()
        self._instances: Dict[UUID, BaseAgent] = {}
        self._tasks: Dict[UUID, TaskRecord] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "task_start": [],
            "task_complete": [],
            "task_error": []
        }

    def create_agent(
        self,
        agent_name: str,
        llm_client=None,
        **kwargs
    ) -> Optional[UUID]:
        """
        创建 Agent 实例

        Args:
            agent_name: Agent 名称
            llm_client: LLM 客户端
            **kwargs: 其他参数

        Returns:
            实例 ID 或 None
        """
        agent = self.registry.create_instance(
            agent_name,
            llm_client=llm_client or create_default_client(),
            **kwargs
        )

        if agent:
            self._instances[agent.id] = agent
            return agent.id
        return None

    def get_agent(self, agent_id: UUID) -> Optional[BaseAgent]:
        """获取 Agent 实例"""
        return self._instances.get(agent_id)

    def list_instances(self) -> List[Dict[str, Any]]:
        """列出所有实例"""
        return [
            {
                "id": str(agent.id),
                "name": agent.name,
                "state": agent.state.name,
                "steps": len(agent.steps)
            }
            for agent in self._instances.values()
        ]

    async def execute_task(
        self,
        agent_id: UUID,
        input_data: Dict[str, Any],
        stream: bool = False
    ) -> TaskRecord:
        """
        执行任务

        Args:
            agent_id: Agent 实例 ID
            input_data: 输入数据
            stream: 是否流式输出

        Returns:
            任务记录
        """
        agent = self._instances.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # 创建任务记录
        task = TaskRecord(
            id=uuid4(),
            agent_name=agent.name,
            input_data=input_data,
            status=AgentState.RUNNING
        )
        self._tasks[task.id] = task

        # 触发回调
        self._trigger_callback("task_start", task)

        try:
            task.started_at = datetime.now()

            if stream:
                # 流式执行
                async for chunk in agent.execute_stream(input_data):
                    # 流式输出处理
                    pass
                # 获取最终结果
                result = await agent.execute(input_data)
            else:
                result = await agent.execute(input_data)

            task.result = result
            task.status = AgentState.COMPLETED if result.success else AgentState.FAILED
            task.completed_at = datetime.now()

            if result.success:
                self._trigger_callback("task_complete", task)
            else:
                task.error = result.error
                self._trigger_callback("task_error", task)

        except Exception as e:
            task.status = AgentState.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self._trigger_callback("task_error", task)

        return task

    def get_task(self, task_id: UUID) -> Optional[TaskRecord]:
        """获取任务记录"""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        agent_name: Optional[str] = None,
        status: Optional[AgentState] = None
    ) -> List[TaskRecord]:
        """
        列出任务

        Args:
            agent_name: 按 Agent 名称筛选
            status: 按状态筛选

        Returns:
            任务记录列表
        """
        tasks = list(self._tasks.values())

        if agent_name:
            tasks = [t for t in tasks if t.agent_name == agent_name]
        if status:
            tasks = [t for t in tasks if t.status == status]

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def on(self, event: str, callback: Callable):
        """
        注册事件回调

        Args:
            event: 事件名称 (task_start, task_complete, task_error)
            callback: 回调函数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callback(self, event: str, task: TaskRecord):
        """触发回调"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(task))
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def cleanup(self, max_age_hours: int = 24):
        """
        清理旧实例和任务

        Args:
            max_age_hours: 最大保留时间（小时）
        """
        now = datetime.now()

        # 清理已完成的实例
        to_remove = []
        for agent_id, agent in self._instances.items():
            if agent.state in [AgentState.COMPLETED, AgentState.FAILED, AgentState.CANCELLED]:
                # 检查最后步骤时间
                if agent.steps and agent.steps[-1].end_at:
                    age = (now - agent.steps[-1].end_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(agent_id)

        for agent_id in to_remove:
            del self._instances[agent_id]

        # 清理旧任务
        to_remove = []
        for task_id, task in self._tasks.items():
            if task.completed_at:
                age = (now - task.completed_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self._tasks[task_id]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_tasks = len(self._tasks)
        completed = sum(1 for t in self._tasks.values() if t.status == AgentState.COMPLETED)
        failed = sum(1 for t in self._tasks.values() if t.status == AgentState.FAILED)
        running = sum(1 for t in self._tasks.values() if t.status == AgentState.RUNNING)

        return {
            "instances": len(self._instances),
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "success_rate": completed / total_tasks if total_tasks > 0 else 0
        }
