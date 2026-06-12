#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具基类

定义所有工具的抽象基类和数据结构
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum


class ParameterType(Enum):
    """参数类型"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 JSON Schema）"""
        result = {
            "type": self.type.value,
            "description": self.description,
        }
        if self.enum:
            result["enum"] = self.enum
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def success_result(cls, output: str = "", data: Dict[str, Any] = None) -> 'ToolResult':
        """创建成功结果"""
        return cls(success=True, output=output, data=data or {})

    @classmethod
    def error_result(cls, error: str, output: str = "") -> 'ToolResult':
        """创建错误结果"""
        return cls(success=False, error=error, output=output)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error
        }


class BaseTool(ABC):
    """
    工具抽象基类

    所有具体工具必须继承此类
    """

    # 工具元数据
    name: str = "base_tool"
    description: str = "Base tool class"
    version: str = "1.0.0"

    # 参数定义
    parameters: List[ToolParameter] = []

    def __init__(self):
        """初始化工具"""
        self._validate_parameters()

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    def _validate_parameters(self):
        """验证参数定义"""
        param_names = set()
        for param in self.parameters:
            if param.name in param_names:
                raise ValueError(f"Duplicate parameter name: {param.name}")
            param_names.add(param.name)

    def validate_args(self, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数

        Args:
            args: 传入的参数

        Returns:
            (是否有效, 错误信息)
        """
        for param in self.parameters:
            if param.name not in args:
                if param.required and param.default is None:
                    return False, f"Missing required parameter: {param.name}"
                continue

            value = args[param.name]

            # 类型检查
            if param.type == ParameterType.STRING and not isinstance(value, str):
                return False, f"Parameter {param.name} must be a string"
            elif param.type == ParameterType.INTEGER and not isinstance(value, int):
                return False, f"Parameter {param.name} must be an integer"
            elif param.type == ParameterType.NUMBER and not isinstance(value, (int, float)):
                return False, f"Parameter {param.name} must be a number"
            elif param.type == ParameterType.BOOLEAN and not isinstance(value, bool):
                return False, f"Parameter {param.name} must be a boolean"

            # 枚举检查
            if param.enum and value not in param.enum:
                return False, f"Parameter {param.name} must be one of {param.enum}"

        return True, None

    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具的 JSON Schema 描述

        Returns:
            工具描述字典
        """
        required = [p.name for p in self.parameters if p.required]
        properties = {p.name: p.to_dict() for p in self.parameters}

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def get_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [p.name for p in self.parameters]
        }