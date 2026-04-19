#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具执行器

负责执行工具调用并处理结果
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, Any, Optional
from .base import BaseTool, ToolResult
from .registry import ToolRegistry


class ToolExecutor:
    """
    工具执行器

    负责安全地执行工具调用
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        初始化执行器

        Args:
            registry: 工具注册表，默认使用全局注册表
        """
        self.registry = registry or ToolRegistry()

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        # 获取工具实例
        tool = self.registry.create_instance(tool_name)
        if not tool:
            return ToolResult.error_result(f"Tool not found: {tool_name}")

        # 验证参数
        valid, error = tool.validate_args(arguments)
        if not valid:
            return ToolResult.error_result(f"Invalid arguments: {error}")

        # 执行工具
        try:
            # 添加默认值
            for param in tool.parameters:
                if param.name not in arguments and param.default is not None:
                    arguments[param.name] = param.default

            result = await tool.execute(**arguments)
            return result

        except Exception as e:
            return ToolResult.error_result(
                f"Tool execution failed: {str(e)}",
                output=getattr(e, '__traceback__', None)
            )

    async def execute_batch(
        self,
        calls: list[Dict[str, Any]]
    ) -> list[ToolResult]:
        """
        批量执行工具调用

        Args:
            calls: 工具调用列表，每项包含 {tool_name, arguments}

        Returns:
            ToolResult 列表
        """
        results = []
        for call in calls:
            result = await self.execute(
                call.get("tool_name"),
                call.get("arguments", {})
            )
            results.append(result)
        return results

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具 Schema

        Args:
            tool_name: 工具名称

        Returns:
            工具 Schema 或 None
        """
        tool = self.registry.create_instance(tool_name)
        if tool:
            return tool.get_schema()
        return None

    def validate_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        验证工具调用（不执行）

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            (是否有效, 错误信息)
        """
        tool = self.registry.create_instance(tool_name)
        if not tool:
            return False, f"Tool not found: {tool_name}"

        return tool.validate_args(arguments)
