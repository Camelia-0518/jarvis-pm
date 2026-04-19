#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具系统模块

提供 Agent 工具注册、发现和执行功能
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from .base import BaseTool, ToolParameter, ToolResult, ParameterType
from .registry import ToolRegistry, register_tool
from .executor import ToolExecutor
from .web_search import WebSearchTool, WebCrawlerTool
from .doc_write import DocumentWriteTool, DocumentReadTool
from .knowledge import KnowledgeQueryTool, KnowledgeIndexTool

# 自动注册所有工具
def auto_register_tools():
    """自动注册所有内置工具"""
    registry = ToolRegistry()
    registry.register(WebSearchTool)
    registry.register(WebCrawlerTool)
    registry.register(DocumentWriteTool)
    registry.register(DocumentReadTool)
    registry.register(KnowledgeQueryTool)
    registry.register(KnowledgeIndexTool)

__all__ = [
    'BaseTool',
    'ToolParameter',
    'ToolResult',
    'ParameterType',
    'ToolRegistry',
    'register_tool',
    'ToolExecutor',
    'WebSearchTool',
    'WebCrawlerTool',
    'DocumentWriteTool',
    'DocumentReadTool',
    'KnowledgeQueryTool',
    'KnowledgeIndexTool',
    'auto_register_tools',
]
