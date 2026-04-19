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

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表

    单例模式管理所有工具的注册和发现
    """

    _instance = None
    _tools: Dict[str, Type[BaseTool]] = {}

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """
        注册工具

        Args:
            tool_class: 工具类（必须继承 BaseTool）

        Returns:
            工具类（用于装饰器模式）
        """
        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"Tool class must inherit from BaseTool: {tool_class}")

        tool_name = tool_class.name

        if tool_name in self._tools:
            raise ValueError(f"Tool already registered: {tool_name}")

        self._tools[tool_name] = tool_class
        return tool_class

    def unregister(self, tool_name: str):
        """
        注销工具

        Args:
            tool_name: 工具名称
        """
        if tool_name in self._tools:
            del self._tools[tool_name]

    def get(self, tool_name: str) -> Optional[Type[BaseTool]]:
        """
        获取工具类

        Args:
            tool_name: 工具名称

        Returns:
            工具类或 None
        """
        return self._tools.get(tool_name)

    def create_instance(self, tool_name: str) -> Optional[BaseTool]:
        """
        创建工具实例

        Args:
            tool_name: 工具名称

        Returns:
            工具实例或 None
        """
        tool_class = self.get(tool_name)
        if tool_class:
            return tool_class()
        return None

    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具名称

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的 Schema

        Returns:
            工具 Schema 列表
        """
        schemas = []
        for tool_name, tool_class in self._tools.items():
            try:
                tool = tool_class()
                schemas.append(tool.get_schema())
            except Exception as e:
                # 跳过无法实例化的工具
                logger.warning(f"Failed to get schema for {tool_name}: {e}")
        return schemas

    def get_all_info(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的信息

        Returns:
            工具信息列表
        """
        info_list = []
        for tool_name, tool_class in self._tools.items():
            try:
                tool = tool_class()
                info_list.append(tool.get_info())
            except Exception as e:
                logger.warning(f"Failed to get info for {tool_name}: {e}")
        return info_list

    def clear(self):
        """清空所有注册的工具"""
        self._tools.clear()

    def __contains__(self, tool_name: str) -> bool:
        """检查工具是否已注册"""
        return tool_name in self._tools

    def __len__(self) -> int:
        """返回已注册工具数量"""
        return len(self._tools)


# 便捷函数
def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """装饰器：注册工具到全局注册表"""
    registry = ToolRegistry()
    return registry.register(tool_class)


def get_tool(tool_name: str) -> Optional[Type[BaseTool]]:
    """获取工具类"""
    registry = ToolRegistry()
    return registry.get(tool_name)


def list_all_tools() -> List[str]:
    """列出所有工具名称"""
    registry = ToolRegistry()
    return registry.list_tools()
