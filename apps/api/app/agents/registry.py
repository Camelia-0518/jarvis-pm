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

from .base import BaseAgent
from .base_registry import BaseRegistry

logger = logging.getLogger(__name__)


class AgentRegistry(BaseRegistry[BaseAgent]):
    """Agent 注册表 — 单例模式管理所有 Agent 的注册和发现"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, Type[BaseAgent]] = {}
        return cls._instance

    @property
    def _items(self):
        return self._agents

    def register(self, agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class must inherit from BaseAgent: {agent_class}")
        return super().register(agent_class, allow_duplicate=True)

    # unregister, get, list_all, clear, __contains__, __len__ — inherited from BaseRegistry

    def create_instance(self, agent_name: str, llm_client=None, **kwargs) -> Optional[BaseAgent]:
        agent_class = self.get(agent_name)
        if agent_class:
            return agent_class(llm_client=llm_client, **kwargs)
        return None

    def list_agents(self) -> List[str]:
        return self.list()

    def get_all_info(self) -> List[Dict[str, Any]]:
        info_list = []
        for agent_name, agent_class in self._agents.items():
            try:
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
        result = []
        for agent_name, agent_class in self._agents.items():
            if capability in getattr(agent_class, 'capabilities', []):
                result.append(agent_name)
        return result


# ---------- 便捷函数 ----------

def register_agent(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
    return AgentRegistry().register(agent_class)


def get_agent(agent_name: str) -> Optional[Type[BaseAgent]]:
    return AgentRegistry().get(agent_name)


def list_all_agents() -> List[str]:
    return AgentRegistry().list_agents()


def auto_register_agents():
    """自动注册所有内置 Agent"""
    from .agents import (
        IntentClassifier,
        TaskPlanner,
        PRDAgent,
        RequirementAgent,
        CompetitorAnalyst,
        ComplianceChecker,
        ReviewPreparer,
        DeliveryPlannerAgent,
        RiskManagerAgent,
        StakeholderCoordinatorAgent,
    )

    registry = AgentRegistry()
    registry.register(IntentClassifier)
    registry.register(TaskPlanner)
    registry.register(RequirementAgent)
    registry.register(CompetitorAnalyst)
    registry.register(PRDAgent)
    registry.register(ComplianceChecker)
    registry.register(ReviewPreparer)
    registry.register(DeliveryPlannerAgent)
    registry.register(RiskManagerAgent)
    registry.register(StakeholderCoordinatorAgent)
