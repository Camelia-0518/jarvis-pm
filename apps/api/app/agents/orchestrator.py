#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 编排层

实现多 Agent 协作编排、共享上下文内存、Chain 执行
参考 LangChain LCEL 模式
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import asyncio
from typing import Dict, Any, List, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from uuid import uuid4

from .base import BaseAgent, AgentResult, AgentState


class ChainStepType(Enum):
    """链式步骤类型"""
    AGENT = auto()          # 执行 Agent
    TRANSFORM = auto()      # 数据转换
    CONDITION = auto()      # 条件分支
    PARALLEL = auto()       # 并行执行
    MERGE = auto()          # 合并结果


@dataclass
class SharedContext:
    """
    共享上下文内存

    所有 Agent 共享的上下文存储，支持跨步骤数据传递
    """
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _data: Dict[str, Any] = field(default_factory=dict)
    _history: List[Dict[str, Any]] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """设置上下文数据"""
        self._data[key] = value

    def update(self, data: Dict[str, Any]):
        """批量更新上下文数据"""
        self._data.update(data)

    def push_history(self, step_name: str, result: AgentResult):
        """记录执行历史"""
        self._history.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
            "output_preview": result.output[:500] if result.output else "",
            "error": result.error,
            "execution_time": result.execution_time,
        })

    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._history.copy()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "data": self._data,
            "history": self._history,
        }


@dataclass
class ChainStep:
    """链式执行步骤"""
    id: str
    name: str
    step_type: ChainStepType
    # Agent 步骤
    agent: Optional[BaseAgent] = None
    # 转换步骤
    transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    # 条件步骤
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    # 并行步骤（子步骤列表）
    parallel_steps: Optional[List['ChainStep']] = None
    # 输入数据映射（从上下文中提取的键）
    input_map: Dict[str, str] = field(default_factory=dict)
    # 输出数据映射（保存到上下文中的键）
    output_map: str = ""
    # 错误处理：continue / stop / retry
    on_error: str = "stop"
    # 最大重试次数
    max_retries: int = 0


class AgentOrchestrator:
    """
    Agent 编排器

    管理多 Agent 协作执行，支持：
    - 顺序链式执行（Chain）
    - 并行执行
    - 条件分支
    - 共享上下文
    - 错误处理和重试
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.chains: Dict[str, List[ChainStep]] = {}
        self.contexts: Dict[str, SharedContext] = {}

    def register_agent(self, name: str, agent: BaseAgent):
        """注册 Agent"""
        self.agents[name] = agent

    def create_context(self, metadata: Optional[Dict[str, Any]] = None) -> SharedContext:
        """创建新的共享上下文"""
        ctx = SharedContext(metadata=metadata or {})
        self.contexts[ctx.session_id] = ctx
        return ctx

    def define_chain(self, name: str, steps: List[ChainStep]):
        """定义链式执行流程"""
        self.chains[name] = steps

    async def execute_chain(
        self,
        chain_name: str,
        initial_input: Dict[str, Any],
        context: Optional[SharedContext] = None,
        on_step_complete: Optional[Callable[[str, AgentResult], None]] = None,
    ) -> AgentResult:
        """
        执行链式流程

        Args:
            chain_name: 链名称
            initial_input: 初始输入
            context: 共享上下文（可选）
            on_step_complete: 步骤完成回调

        Returns:
            AgentResult: 执行结果
        """
        steps = self.chains.get(chain_name, [])
        if not steps:
            return AgentResult(success=False, error=f"链 '{chain_name}' 未定义")

        if context is None:
            context = self.create_context()

        # 将初始输入放入上下文
        context.update(initial_input)

        start_time = datetime.now()
        final_result: Optional[AgentResult] = None

        for step in steps:
            step_result = await self._execute_step(step, context, on_step_complete)
            final_result = step_result

            if not step_result.success and step.on_error == "stop":
                break

        execution_time = (datetime.now() - start_time).total_seconds()

        if final_result is None:
            return AgentResult(success=False, error="链执行未产生结果")

        return AgentResult(
            success=final_result.success,
            output=final_result.output,
            data={**final_result.data, "context": context.to_dict()},
            error=final_result.error,
            execution_time=execution_time,
        )

    async def _execute_step(
        self,
        step: ChainStep,
        context: SharedContext,
        on_step_complete: Optional[Callable[[str, AgentResult], None]] = None,
    ) -> AgentResult:
        """执行单个步骤"""
        step_start = datetime.now()

        # 从上下文中提取输入
        step_input = {}
        for key, ctx_key in step.input_map.items():
            step_input[key] = context.get(ctx_key)

        result: AgentResult
        retries = 0

        while True:
            try:
                if step.step_type == ChainStepType.AGENT and step.agent:
                    result = await step.agent.execute(step_input)

                elif step.step_type == ChainStepType.TRANSFORM and step.transform:
                    transformed = step.transform(step_input)
                    result = AgentResult(
                        success=True,
                        output="Transform completed",
                        data=transformed,
                    )

                elif step.step_type == ChainStepType.CONDITION and step.condition:
                    condition_met = step.condition(step_input)
                    result = AgentResult(
                        success=True,
                        output=str(condition_met),
                        data={"condition_met": condition_met},
                    )

                elif step.step_type == ChainStepType.PARALLEL and step.parallel_steps:
                    # 并行执行子步骤
                    parallel_results = await asyncio.gather(*[
                        self._execute_step(sub_step, context, on_step_complete)
                        for sub_step in step.parallel_steps
                    ])
                    all_success = all(r.success for r in parallel_results)
                    combined_data = {f"result_{i}": r.data for i, r in enumerate(parallel_results)}
                    result = AgentResult(
                        success=all_success,
                        output=f"Parallel execution: {sum(1 for r in parallel_results if r.success)}/{len(parallel_results)} succeeded",
                        data=combined_data,
                    )

                else:
                    result = AgentResult(success=False, error=f"未知步骤类型: {step.step_type}")

                break  # 成功，跳出重试循环

            except Exception as e:
                retries += 1
                if retries > step.max_retries:
                    result = AgentResult(success=False, error=f"步骤执行失败（重试{step.max_retries}次）: {str(e)}")
                    break
                await asyncio.sleep(2 ** retries)  # 指数退避

        # 保存结果到上下文
        if step.output_map:
            context.set(step.output_map, {
                "success": result.success,
                "output": result.output,
                "data": result.data,
                "error": result.error,
            })

        # 记录历史
        context.push_history(step.name, result)

        # 回调
        if on_step_complete:
            try:
                on_step_complete(step.name, result)
            except Exception:
                pass

        result.execution_time = (datetime.now() - step_start).total_seconds()
        return result

    async def execute_stream(
        self,
        chain_name: str,
        initial_input: Dict[str, Any],
        context: Optional[SharedContext] = None,
    ) -> AsyncIterator[str]:
        """
        流式执行链式流程

        Yields:
            str: 执行过程中的输出片段
        """
        steps = self.chains.get(chain_name, [])
        if not steps:
            yield f"Error: 链 '{chain_name}' 未定义"
            return

        if context is None:
            context = self.create_context()

        context.update(initial_input)

        for step in steps:
            yield f"\n>>> [{step.name}] 开始执行...\n"

            result = await self._execute_step(step, context)

            if result.success:
                yield f"<<< [{step.name}] 完成 ({result.execution_time:.1f}s)\n"
                if result.output:
                    yield result.output[:1000] + "\n"
            else:
                yield f"<<< [{step.name}] 失败: {result.error}\n"
                if step.on_error == "stop":
                    yield "\n链执行已终止\n"
                    break

        yield f"\n链执行完成。上下文 ID: {context.session_id}\n"


# ==================== 预定义常用 Chain ====================

def create_prd_workflow_chain(
    orchestrator: AgentOrchestrator,
    requirement_agent: BaseAgent,
    prd_agent: BaseAgent,
    compliance_agent: BaseAgent,
) -> str:
    """
    创建标准 PRD 工作流 Chain

    流程：需求分析 -> PRD生成 -> 合规检查
    """
    chain_name = "prd_workflow"

    steps = [
        ChainStep(
            id=str(uuid4()),
            name="需求分析",
            step_type=ChainStepType.AGENT,
            agent=requirement_agent,
            input_map={"raw_requirements": "requirements", "product_name": "product_name", "industry": "industry"},
            output_map="requirement_result",
            on_error="stop",
        ),
        ChainStep(
            id=str(uuid4()),
            name="数据准备",
            step_type=ChainStepType.TRANSFORM,
            transform=lambda ctx: {
                "product_name": ctx.get("product_name", ""),
                "description": ctx.get("requirements", ""),
                "industry": ctx.get("industry", ""),
                "requirement_analysis": ctx.get("requirement_result", {}).get("data", {}),
            },
            input_map={"product_name": "product_name", "requirements": "requirements", "industry": "industry", "requirement_result": "requirement_result"},
            output_map="prd_input",
            on_error="stop",
        ),
        ChainStep(
            id=str(uuid4()),
            name="PRD生成",
            step_type=ChainStepType.AGENT,
            agent=prd_agent,
            input_map={"input_data": "prd_input"},
            output_map="prd_result",
            on_error="stop",
        ),
        ChainStep(
            id=str(uuid4()),
            name="合规检查",
            step_type=ChainStepType.AGENT,
            agent=compliance_agent,
            input_map={"content": "prd_result", "industry": "industry"},
            output_map="compliance_result",
            on_error="continue",  # 合规检查失败不阻止流程
        ),
    ]

    orchestrator.define_chain(chain_name, steps)
    return chain_name


def create_battle_chain(
    orchestrator: AgentOrchestrator,
    research_agent: BaseAgent,
    competitor_agent: BaseAgent,
    prd_agent: BaseAgent,
    review_agent: BaseAgent,
) -> str:
    """
    创建 Battle 5天冲刺 Chain

    流程：用户研究 + 竞品分析（并行） -> PRD生成 -> 评审准备
    """
    chain_name = "battle_5day"

    # Day 1 & 2 并行
    parallel_step = ChainStep(
        id=str(uuid4()),
        name="研究阶段",
        step_type=ChainStepType.PARALLEL,
        parallel_steps=[
            ChainStep(
                id=str(uuid4()),
                name="用户研究",
                step_type=ChainStepType.AGENT,
                agent=research_agent,
                input_map={"project_info": "project_info"},
                output_map="research_result",
            ),
            ChainStep(
                id=str(uuid4()),
                name="竞品分析",
                step_type=ChainStepType.AGENT,
                agent=competitor_agent,
                input_map={"project_info": "project_info"},
                output_map="competitor_result",
            ),
        ],
        input_map={"project_info": "project_info"},
        output_map="research_phase",
    )

    steps = [
        parallel_step,
        ChainStep(
            id=str(uuid4()),
            name="PRD框架生成",
            step_type=ChainStepType.AGENT,
            agent=prd_agent,
            input_map={
                "project_info": "project_info",
                "research": "research_phase",
            },
            output_map="prd_result",
            on_error="stop",
        ),
        ChainStep(
            id=str(uuid4()),
            name="评审准备",
            step_type=ChainStepType.AGENT,
            agent=review_agent,
            input_map={"prd": "prd_result"},
            output_map="review_result",
            on_error="continue",
        ),
    ]

    orchestrator.define_chain(chain_name, steps)
    return chain_name
