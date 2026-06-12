#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
具体 Agent 实现模块
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from .intent_classifier import IntentClassifier
from .task_planner import TaskPlanner
from .prd_agent import PRDAgent
from .requirement_agent import RequirementAgent
from .competitor_analyst import CompetitorAnalyst
from .compliance_checker import ComplianceChecker
from .review_preparer import ReviewPreparer
from .delivery_planner import DeliveryPlannerAgent
from .risk_manager import RiskManagerAgent
from .stakeholder_coordinator import StakeholderCoordinatorAgent
from .retrospective_agent import RetrospectiveAgent

# Register all agents with the global registry
from ..registry import AgentRegistry

_registry = AgentRegistry()
_registry.register(IntentClassifier)
_registry.register(TaskPlanner)
_registry.register(PRDAgent)
_registry.register(RequirementAgent)
_registry.register(CompetitorAnalyst)
_registry.register(ComplianceChecker)
_registry.register(ReviewPreparer)
_registry.register(DeliveryPlannerAgent)
_registry.register(RiskManagerAgent)
_registry.register(StakeholderCoordinatorAgent)
_registry.register(RetrospectiveAgent)

__all__ = [
    'IntentClassifier',
    'TaskPlanner',
    'PRDAgent',
    'RequirementAgent',
    'CompetitorAnalyst',
    'ComplianceChecker',
    'ReviewPreparer',
    'DeliveryPlannerAgent',
    'RiskManagerAgent',
    'StakeholderCoordinatorAgent',
    'RetrospectiveAgent',
]
