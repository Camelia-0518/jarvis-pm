#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具注册表测试
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import pytest

from app.agents.tools.base import BaseTool, ToolParameter, ToolResult, ParameterType
from app.agents.tools.registry import ToolRegistry, register_tool
from app.agents.tools.executor import ToolExecutor


class MockTool(BaseTool):
    """测试用工具"""
    name = "mock_tool"
    description = "A mock tool for testing"
    parameters = [
        ToolParameter(
            name="input",
            type=ParameterType.STRING,
            description="Input string",
            required=True
        ),
        ToolParameter(
            name="count",
            type=ParameterType.INTEGER,
            description="Repeat count",
            required=False,
            default=1
        )
    ]

    async def execute(self, **kwargs) -> ToolResult:
        input_str = kwargs.get("input", "")
        count = kwargs.get("count", 1)
        output = (input_str + " ") * count
        return ToolResult.success_result(output.strip(), {"length": len(output)})


class TestToolParameter:
    """测试 ToolParameter"""

    def test_creation(self):
        param = ToolParameter(
            name="test",
            type=ParameterType.STRING,
            description="Test parameter",
            required=True
        )
        assert param.name == "test"
        assert param.type == ParameterType.STRING

    def test_to_dict(self):
        param = ToolParameter(
            name="test",
            type=ParameterType.STRING,
            description="Test",
            enum=["a", "b"]
        )
        data = param.to_dict()
        assert data["type"] == "string"
        assert data["enum"] == ["a", "b"]


class TestToolResult:
    """测试 ToolResult"""

    def test_success_result(self):
        result = ToolResult.success_result("output", {"key": "value"})
        assert result.success is True
        assert result.output == "output"
        assert result.data == {"key": "value"}

    def test_error_result(self):
        result = ToolResult.error_result("error message")
        assert result.success is False
        assert result.error == "error message"

    def test_to_dict(self):
        result = ToolResult.success_result("test")
        data = result.to_dict()
        assert data["success"] is True
        assert data["output"] == "test"


class TestBaseTool:
    """测试 BaseTool"""

    def test_tool_info(self):
        tool = MockTool()
        info = tool.get_info()
        assert info["name"] == "mock_tool"
        assert "input" in info["parameters"]

    def test_get_schema(self):
        tool = MockTool()
        schema = tool.get_schema()
        assert schema["name"] == "mock_tool"
        assert "input" in schema["parameters"]["properties"]

    def test_validate_args_valid(self):
        tool = MockTool()
        valid, error = tool.validate_args({"input": "hello", "count": 3})
        assert valid is True
        assert error is None

    def test_validate_args_missing_required(self):
        tool = MockTool()
        valid, error = tool.validate_args({})
        assert valid is False
        assert "Missing required parameter" in error

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = MockTool()
        result = await tool.execute(input="hello", count=2)
        assert result.success is True
        assert "hello hello" in result.output


class TestToolRegistry:
    """测试 ToolRegistry"""

    @pytest.fixture
    def registry(self):
        """创建新的注册表实例"""
        reg = ToolRegistry()
        reg.clear()
        return reg

    def test_register(self, registry):
        registry.register(MockTool)
        assert "mock_tool" in registry

    def test_register_duplicate(self, registry):
        registry.register(MockTool)
        with pytest.raises(ValueError):
            registry.register(MockTool)

    def test_get(self, registry):
        registry.register(MockTool)
        tool_class = registry.get("mock_tool")
        assert tool_class == MockTool

    def test_create_instance(self, registry):
        registry.register(MockTool)
        tool = registry.create_instance("mock_tool")
        assert isinstance(tool, MockTool)

    def test_list_tools(self, registry):
        registry.register(MockTool)
        tools = registry.list_tools()
        assert "mock_tool" in tools

    def test_unregister(self, registry):
        registry.register(MockTool)
        registry.unregister("mock_tool")
        assert "mock_tool" not in registry


class TestToolExecutor:
    """测试 ToolExecutor"""

    @pytest.fixture
    def executor(self):
        registry = ToolRegistry()
        registry.clear()
        registry.register(MockTool)
        return ToolExecutor(registry)

    @pytest.mark.asyncio
    async def test_execute(self, executor):
        result = await executor.execute("mock_tool", {"input": "hello"})
        assert result.success is True
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_execute_not_found(self, executor):
        result = await executor.execute("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_invalid_args(self, executor):
        result = await executor.execute("mock_tool", {})
        assert result.success is False
        assert "Invalid arguments" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
