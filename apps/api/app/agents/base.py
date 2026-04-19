#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 基础类

提供所有 Agent 的抽象基类和通用功能
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import asyncio
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from datetime import datetime
from uuid import uuid4, UUID
import json


class AgentState(Enum):
    """Agent 执行状态"""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    output: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResult':
        return cls(**data)


@dataclass
class AgentStep:
    """Agent 执行步骤"""
    id: str
    name: str
    description: str
    status: AgentState = AgentState.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: str = ""
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Agent 抽象基类

    所有具体 Agent 必须继承此类
    """

    # Agent 元数据
    name: str = "BaseAgent"
    description: str = "Base agent class"
    version: str = "1.0.0"
    author: str = "Jarvis PM"

    # 能力声明
    capabilities: List[str] = []
    required_tools: List[str] = []

    def __init__(
        self,
        llm_client=None,
        max_steps: int = 50,
        timeout: int = 300
    ):
        """
        初始化 Agent

        Args:
            llm_client: LLM 客户端实例
            max_steps: 最大执行步骤数
            timeout: 执行超时时间（秒）
        """
        self.id = uuid4()
        self.llm_client = llm_client
        self.max_steps = max_steps
        self.timeout = timeout

        # 执行状态
        self.state = AgentState.IDLE
        self.steps: List[AgentStep] = []
        self.current_step_index = 0
        self.context: Dict[str, Any] = {}

        # 事件回调
        self._on_step_start: Optional[Callable] = None
        self._on_step_end: Optional[Callable] = None
        self._on_state_change: Optional[Callable] = None

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行 Agent 任务

        Args:
            input_data: 输入数据

        Returns:
            AgentResult: 执行结果
        """
        pass

    async def execute_stream(
        self,
        input_data: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        流式执行 Agent 任务

        Args:
            input_data: 输入数据

        Yields:
            str: 执行过程中的输出片段
        """
        # 默认实现：非流式，一次性返回
        result = await self.execute(input_data)
        yield result.output

    async def run(
        self,
        input_data: Dict[str, Any],
        stream: bool = False
    ) -> AgentResult | AsyncGenerator[str, None]:
        """
        运行 Agent

        Args:
            input_data: 输入数据
            stream: 是否使用流式输出

        Returns:
            AgentResult 或 AsyncGenerator
        """
        if stream:
            return self.execute_stream(input_data)
        else:
            return await self.execute(input_data)

    def set_callbacks(
        self,
        on_step_start: Optional[Callable] = None,
        on_step_end: Optional[Callable] = None,
        on_state_change: Optional[Callable] = None
    ):
        """设置事件回调"""
        self._on_step_start = on_step_start
        self._on_step_end = on_step_end
        self._on_state_change = on_state_change

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """
        调用 LLM

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            stream: 是否流式输出

        Returns:
            LLM 响应
        """
        if self.llm_client is None:
            raise ValueError("LLM client not initialized")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if stream:
            return await self.llm_client.chat_stream(messages)
        else:
            return await self.llm_client.chat(messages)

    def _create_step(self, name: str, description: str) -> AgentStep:
        """创建执行步骤"""
        step = AgentStep(
            id=str(uuid4()),
            name=name,
            description=description,
            status=AgentState.RUNNING,
            start_time=datetime.now()
        )
        self.steps.append(step)
        self.current_step_index = len(self.steps) - 1
        return step

    def _complete_step(self, step: AgentStep, output: str = ""):
        """完成执行步骤"""
        step.status = AgentState.COMPLETED
        step.end_time = datetime.now()
        step.output = output

        if self._on_step_end:
            asyncio.create_task(self._on_step_end(step))

    def _fail_step(self, step: AgentStep, error: str):
        """标记步骤失败"""
        step.status = AgentState.FAILED
        step.end_time = datetime.now()
        step.error = error

    def _set_state(self, state: AgentState):
        """设置 Agent 状态"""
        old_state = self.state
        self.state = state

        if self._on_state_change and old_state != state:
            asyncio.create_task(self._on_state_change(old_state, state))

    def get_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "capabilities": self.capabilities,
            "required_tools": self.required_tools,
            "state": self.state.name,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps)
        }

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """获取执行日志"""
        return [
            {
                "id": step.id,
                "name": step.name,
                "description": step.description,
                "status": step.status.name,
                "start_time": step.start_time.isoformat() if step.start_time else None,
                "end_time": step.end_time.isoformat() if step.end_time else None,
                "output": step.output,
                "error": step.error
            }
            for step in self.steps
        ]

    def reset(self):
        """重置 Agent 状态"""
        self.state = AgentState.IDLE
        self.steps = []
        self.current_step_index = 0
        self.context = {}
