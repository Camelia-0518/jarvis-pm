#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具注册表

管理所有可用工具的注册和发现
"""

import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, List, Type, Optional, Any
from .base import BaseTool
from ..base_registry import BaseRegistry

logger = logging.getLogger(__name__)


class ToolRegistry(BaseRegistry[BaseTool]):
    """工具注册表 — 单例模式管理所有工具的注册和发现"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Type[BaseTool]] = {}
        return cls._instance

    @property
    def _items(self):
        return self._tools

    def register(self, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"Tool class must inherit from BaseTool: {tool_class}")
        return super().register(tool_class, allow_duplicate=False)

    # unregister, get, list_all, clear, __contains__, __len__ — inherited from BaseRegistry

    def create_instance(self, tool_name: str) -> Optional[BaseTool]:
        tool_class = self.get(tool_name)
        if tool_class:
            return tool_class()
        return None

    def list_tools(self) -> List[str]:
        return self.list()

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        schemas = []
        for tool_name, tool_class in self._tools.items():
            try:
                tool = tool_class()
                schemas.append(tool.get_schema())
            except Exception as e:
                logger.warning(f"Failed to get schema for {tool_name}: {e}")
        return schemas

    def get_all_info(self) -> List[Dict[str, Any]]:
        info_list = []
        for tool_name, tool_class in self._tools.items():
            try:
                tool = tool_class()
                info_list.append(tool.get_info())
            except Exception as e:
                logger.warning(f"Failed to get info for {tool_name}: {e}")
        return info_list


# ---------- 便捷函数 ----------

def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    return ToolRegistry().register(tool_class)


def get_tool(tool_name: str) -> Optional[Type[BaseTool]]:
    return ToolRegistry().get(tool_name)


def list_all_tools() -> List[str]:
    return ToolRegistry().list_tools()
