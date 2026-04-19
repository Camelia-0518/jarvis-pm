#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 注册表

管理所有 Agent 的注册和发现
"""

import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, List, Type, Optional, Any
from uuid import UUID
from .base import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Agent 注册表

    单例模式管理所有 Agent 的注册和发现
    """

    _instance = None
    _agents: Dict[str, Type[BaseAgent]] = {}

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    def register(self, agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        """
        注册 Agent

        Args:
            agent_class: Agent 类（必须继承 BaseAgent）

        Returns:
            Agent 类（用于装饰器模式）
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class must inherit from BaseAgent: {agent_class}")

        agent_name = agent_class.name

        if agent_name in self._agents:
            raise ValueError(f"Agent already registered: {agent_name}")

        self._agents[agent_name] = agent_class
        return agent_class

    def unregister(self, agent_name: str):
        """
        注销 Agent

        Args:
            agent_name: Agent 名称
        """
        if agent_name in self._agents:
            del self._agents[agent_name]

    def get(self, agent_name: str) -> Optional[Type[BaseAgent]]:
        """
        获取 Agent 类

        Args:
            agent_name: Agent 名称

        Returns:
            Agent 类或 None
        """
        return self._agents.get(agent_name)

    def create_instance(
        self,
        agent_name: str,
        llm_client=None,
        **kwargs
    ) -> Optional[BaseAgent]:
        """
        创建 Agent 实例

        Args:
            agent_name: Agent 名称
            llm_client: LLM 客户端
            **kwargs: 其他参数

        Returns:
            Agent 实例或 None
        """
        agent_class = self.get(agent_name)
        if agent_class:
            return agent_class(llm_client=llm_client, **kwargs)
        return None

    def list_agents(self) -> List[str]:
        """
        列出所有已注册的 Agent 名称

        Returns:
            Agent 名称列表
        """
        return list(self._agents.keys())

    def get_all_info(self) -> List[Dict[str, Any]]:
        """
        获取所有 Agent 的信息

        Returns:
            Agent 信息列表
        """
        info_list = []
        for agent_name, agent_class in self._agents.items():
            try:
                # 不实例化，直接读取类属性
                info_list.append({
                    "name": agent_class.name,
                    "description": agent_class.description,
                    "version": agent_class.version,
                    "capabilities": agent_class.capabilities,
                    "required_tools": agent_class.required_tools,
                })
            except Exception as e:
                logger.warning(f"Failed to get info for {agent_name}: {e}")
        return info_list

    def find_by_capability(self, capability: str) -> List[str]:
        """
        按能力查找 Agent

        Args:
            capability: 能力名称

        Returns:
            符合条件的 Agent 名称列表
        """
        result = []
        for agent_name, agent_class in self._agents.items():
            if capability in getattr(agent_class, 'capabilities', []):
                result.append(agent_name)
        return result

    def clear(self):
        """清空所有注册的 Agent"""
        self._agents.clear()

    def __contains__(self, agent_name: str) -> bool:
        """检查 Agent 是否已注册"""
        return agent_name in self._agents

    def __len__(self) -> int:
        """返回已注册 Agent 数量"""
        return len(self._agents)


# 便捷函数
def register_agent(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
    """装饰器：注册 Agent 到全局注册表"""
    registry = AgentRegistry()
    return registry.register(agent_class)


def get_agent(agent_name: str) -> Optional[Type[BaseAgent]]:
    """获取 Agent 类"""
    registry = AgentRegistry()
    return registry.get(agent_name)


def list_all_agents() -> List[str]:
    """列出所有 Agent 名称"""
    registry = AgentRegistry()
    return registry.list_agents()


def auto_register_agents():
    """
    自动注册所有内置 Agent

    导入并注册所有已实现的 Agent
    """
    from .agents import (
        IntentClassifier,
        TaskPlanner,
        PRDAgent,
        RequirementAgent,
        CompetitorAnalyst,
        ComplianceChecker,
        ReviewPreparer
    )

    registry = AgentRegistry()
    registry.register(IntentClassifier)
    registry.register(TaskPlanner)
    registry.register(RequirementAgent)
    registry.register(CompetitorAnalyst)
    registry.register(PRDAgent)
    registry.register(ComplianceChecker)
    registry.register(ReviewPreparer)
