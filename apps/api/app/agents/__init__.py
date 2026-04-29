#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 系统模块

提供基于 HTTP API 的多提供商 AI Agent 执行框架
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Windows 特殊处理（避免在 pytest 中重定向 stdout 导致捕获异常）
import sys
if sys.platform == 'win32' and 'pytest' not in sys.modules:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from .base import BaseAgent, AgentState, AgentResult
from .llm_client import (
    LLMClient,
    KimiHTTPClient,
    OpenAIHTTPClient,
    AnthropicHTTPClient,
    FallbackLLMClient,
    LLMClientFactory,
    create_default_client,
)
from .registry import AgentRegistry, register_agent, get_agent, list_all_agents, auto_register_agents
from .manager import AgentManager, TaskRecord
from .tasks import TaskQueue, get_task_queue, TaskPriority

__all__ = [
    'BaseAgent',
    'AgentState',
    'AgentResult',
    'LLMClient',
    'KimiHTTPClient',
    'OpenAIHTTPClient',
    'AnthropicHTTPClient',
    'FallbackLLMClient',
    'LLMClientFactory',
    'create_default_client',
    'AgentRegistry',
    'register_agent',
    'get_agent',
    'list_all_agents',
    'auto_register_agents',
    'AgentManager',
    'TaskRecord',
    'TaskQueue',
    'get_task_queue',
    'TaskPriority',
]
