#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 基础类测试
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import pytest
import asyncio
from datetime import datetime

from app.agents.base import (
    BaseAgent,
    AgentState,
    AgentResult,
    AgentStep
)


class MockAgent(BaseAgent):
    """测试用 Agent"""
    name = "MockAgent"
    description = "Agent for testing"
    capabilities = ["test"]

    async def execute(self, input_data: dict) -> AgentResult:
        """模拟执行"""
        step = self._create_step("mock_step", "Mock execution step")

        # 模拟处理
        output = f"Processed: {input_data.get('message', 'no message')}"

        self._complete_step(step, output)

        return AgentResult(
            success=True,
            output=output,
            data={"processed": True}
        )


class TestAgentState:
    """测试 AgentState 枚举"""

    def test_states_exist(self):
        """测试所有状态都存在"""
        assert AgentState.IDLE
        assert AgentState.RUNNING
        assert AgentState.PAUSED
        assert AgentState.COMPLETED
        assert AgentState.FAILED
        assert AgentState.CANCELLED


class TestAgentResult:
    """测试 AgentResult 数据类"""

    def test_result_creation(self):
        """测试创建结果"""
        result = AgentResult(
            success=True,
            output="test output",
            data={"key": "value"},
            execution_time=1.5
        )

        assert result.success is True
        assert result.output == "test output"
        assert result.data == {"key": "value"}
        assert result.execution_time == 1.5

    def test_result_to_dict(self):
        """测试转换为字典"""
        result = AgentResult(
            success=True,
            output="test",
            data={"key": "value"}
        )

        data = result.to_dict()
        assert data["success"] is True
        assert data["output"] == "test"
        assert data["data"] == {"key": "value"}

    def test_result_from_dict(self):
        """测试从字典创建"""
        data = {
            "success": True,
            "output": "test",
            "data": {"key": "value"},
            "error": None,
            "execution_time": 1.0,
            "metadata": {}
        }

        result = AgentResult.from_dict(data)
        assert result.success is True
        assert result.output == "test"


class TestBaseAgent:
    """测试 BaseAgent 类"""

    @pytest.fixture
    def agent(self):
        """创建测试 Agent"""
        return MockAgent()

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        assert agent.name == "MockAgent"
        assert agent.state == AgentState.IDLE
        assert agent.steps == []
        assert agent.context == {}

    @pytest.mark.asyncio
    async def test_agent_execute(self, agent):
        """测试 Agent 执行"""
        result = await agent.execute({"message": "hello"})

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert "Processed: hello" in result.output
        assert result.data["processed"] is True

    @pytest.mark.asyncio
    async def test_agent_info(self, agent):
        """测试获取 Agent 信息"""
        info = agent.get_info()

        assert info["name"] == "MockAgent"
        assert info["description"] == "Agent for testing"
        assert "test" in info["capabilities"]
        assert info["state"] == "IDLE"

    @pytest.mark.asyncio
    async def test_step_creation(self, agent):
        """测试步骤创建"""
        step = agent._create_step("test_step", "Test description")

        assert isinstance(step, AgentStep)
        assert step.name == "test_step"
        assert step.description == "Test description"
        assert step.status == AgentState.RUNNING
        assert step.start_time is not None

    @pytest.mark.asyncio
    async def test_step_completion(self, agent):
        """测试步骤完成"""
        step = agent._create_step("test_step", "Test")
        agent._complete_step(step, "output content")

        assert step.status == AgentState.COMPLETED
        assert step.output == "output content"
        assert step.end_time is not None

    @pytest.mark.asyncio
    async def test_state_management(self, agent):
        """测试状态管理"""
        assert agent.state == AgentState.IDLE

        agent._set_state(AgentState.RUNNING)
        assert agent.state == AgentState.RUNNING

        agent._set_state(AgentState.COMPLETED)
        assert agent.state == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_reset(self, agent):
        """测试重置功能"""
        await agent.execute({"message": "test"})
        agent._set_state(AgentState.COMPLETED)

        agent.reset()

        assert agent.state == AgentState.IDLE
        assert agent.steps == []
        assert agent.current_step_index == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
