#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD Agent 测试
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import pytest
import asyncio

from app.agents.agents.prd_agent import PRDAgent
from app.agents.base import AgentState


class TestPRDAgent:
    """测试 PRD Agent"""

    @pytest.fixture
    def agent(self):
        """创建 PRD Agent"""
        return PRDAgent()

    def test_agent_info(self, agent):
        """测试 Agent 信息"""
        info = agent.get_info()
        assert info["name"] == "prd_generator"
        assert "prd_generation" in info["capabilities"]

    def test_initial_state(self, agent):
        """测试初始状态"""
        assert agent.state == AgentState.IDLE

    def test_build_prompt(self, agent):
        """测试提示词构建"""
        ctx = {
            "product_name": "测试产品",
            "description": "这是一个测试产品",
            "target_users": "测试用户",
            "key_features": ["功能1", "功能2"],
            "constraints": ["约束1"],
            "sections": ["background", "objectives"],
            "industry": "unknown",
            "template_id": "",
            "template": None,
        }
        prompt = agent._build_prompt(ctx)
        assert "测试产品" in prompt
        assert "功能1" in prompt
        assert "background" in prompt

    def test_post_process(self, agent):
        """测试后处理"""
        content = "一些内容"
        processed = agent._post_process(content)
        assert "# 产品需求文档" in processed or "generated_at" in processed

    @pytest.mark.asyncio
    async def test_execute_mock(self, agent, monkeypatch):
        """测试执行（模拟 LLM）"""
        # 模拟 LLM 调用
        async def mock_call_llm(*args, **kwargs):
            return "# PRD\n\n测试内容"

        agent._call_llm = mock_call_llm

        result = await agent.execute({
            "product_name": "测试产品",
            "description": "测试描述",
            "target_users": "测试用户",
            "key_features": ["功能1"]
        })

        assert result.success is True
        assert result.data["product_name"] == "测试产品"
        assert "markdown" in result.data
        assert "structured" in result.data
        assert agent.state == AgentState.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
