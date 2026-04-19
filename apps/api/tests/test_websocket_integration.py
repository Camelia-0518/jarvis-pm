#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 集成测试

测试 WebSocket 连接、事件流、并发性能
"""

import os
import sys
import asyncio
import pytest
import json
import websockets
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, List

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..'))

from app.websocket.manager import WebSocketManager, websocket_manager
from app.websocket.events import EventEmitter
from app.websocket.router import websocket_router
from app.agents.progress import ProgressTracker, StepStatus


# ==================== WebSocket 连接测试 ====================

class TestWebSocketConnection:
    """测试 WebSocket 连接"""

    @pytest.fixture
    def websocket_manager(self):
        """创建新的 WebSocket 管理器实例"""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_manager):
        """测试 WebSocket 连接建立"""
        workflow_id = "test-workflow-001"

        # 创建模拟 WebSocket
        mock_websocket = AsyncMock()

        # 建立连接
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 验证连接已接受
        mock_websocket.accept.assert_called_once()

        # 验证连接已注册
        assert workflow_id in websocket_manager.active_connections
        assert mock_websocket in websocket_manager.active_connections[workflow_id]

    @pytest.mark.asyncio
    async def test_websocket_disconnection(self, websocket_manager):
        """测试 WebSocket 断开连接"""
        workflow_id = "test-workflow-002"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 断开连接
        websocket_manager.disconnect(mock_websocket, workflow_id)

        # 验证连接已移除
        assert workflow_id not in websocket_manager.active_connections

    @pytest.mark.asyncio
    async def test_multiple_connections_same_workflow(self, websocket_manager):
        """测试同一工作流的多个连接"""
        workflow_id = "test-workflow-003"

        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await websocket_manager.connect(mock_ws1, workflow_id)
        await websocket_manager.connect(mock_ws2, workflow_id)

        # 验证两个连接都已注册
        assert len(websocket_manager.active_connections[workflow_id]) == 2
        assert mock_ws1 in websocket_manager.active_connections[workflow_id]
        assert mock_ws2 in websocket_manager.active_connections[workflow_id]

        # 断开一个连接
        websocket_manager.disconnect(mock_ws1, workflow_id)

        # 验证另一个连接仍然存在
        assert len(websocket_manager.active_connections[workflow_id]) == 1
        assert mock_ws2 in websocket_manager.active_connections[workflow_id]


# ==================== WebSocket 事件测试 ====================

class TestWebSocketEvents:
    """测试 WebSocket 事件流"""

    @pytest.fixture
    def websocket_manager(self):
        return WebSocketManager()

    @pytest.fixture
    def event_emitter(self):
        return EventEmitter("test-workflow-events")

    @pytest.mark.asyncio
    async def test_websocket_progress_events(self, websocket_manager):
        """测试进度事件流"""
        workflow_id = "test-progress-workflow"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 发送进度更新
        await websocket_manager.send_progress(
            workflow_id,
            step="需求分析",
            progress=50,
            detail="正在分析需求..."
        )

        # 验证消息格式
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])

        assert sent_message["type"] == "progress"
        assert sent_message["step"] == "需求分析"
        assert sent_message["progress"] == 50
        assert sent_message["detail"] == "正在分析需求..."
        assert "timestamp" in sent_message

    @pytest.mark.asyncio
    async def test_websocket_agent_status_events(self, websocket_manager):
        """测试 Agent 状态事件"""
        workflow_id = "test-agent-workflow"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 发送 Agent 开始事件
        await websocket_manager.send_agent_status(
            workflow_id,
            agent_name="product-analyst",
            status="started",
            result={"input": "测试输入"}
        )

        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "agent_status"
        assert sent_message["agent"] == "product-analyst"
        assert sent_message["status"] == "started"
        assert sent_message["result"]["input"] == "测试输入"

    @pytest.mark.asyncio
    async def test_websocket_checkpoint_events(self, websocket_manager):
        """测试检查点事件"""
        workflow_id = "test-checkpoint-workflow"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 发送检查点事件
        await websocket_manager.send_checkpoint(
            workflow_id,
            checkpoint_id="checkpoint-001",
            title="确认需求分析结果",
            content={
                "summary": "需求分析完成",
                "key_points": ["用户管理", "权限控制"]
            }
        )

        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "checkpoint"
        assert sent_message["checkpoint_id"] == "checkpoint-001"
        assert sent_message["title"] == "确认需求分析结果"
        assert "content" in sent_message

    @pytest.mark.asyncio
    async def test_websocket_complete_event(self, websocket_manager):
        """测试完成事件"""
        workflow_id = "test-complete-workflow"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 发送完成事件
        await websocket_manager.send_complete(
            workflow_id,
            final_result={
                "prd_document": "# PRD文档",
                "compliance_check": "通过"
            }
        )

        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "complete"
        assert "result" in sent_message
        assert sent_message["result"]["prd_document"] == "# PRD文档"

    @pytest.mark.asyncio
    async def test_websocket_error_event(self, websocket_manager):
        """测试错误事件"""
        workflow_id = "test-error-workflow"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 发送错误事件
        await websocket_manager.send_error(
            workflow_id,
            error="执行超时，请重试"
        )

        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "error"
        assert sent_message["error"] == "执行超时，请重试"


# ==================== EventEmitter 测试 ====================

class TestEventEmitter:
    """测试事件发射器"""

    @pytest.fixture
    def event_emitter(self):
        return EventEmitter("test-emitter-workflow")

    @pytest.mark.asyncio
    async def test_emit_progress(self, event_emitter):
        """测试发射进度事件"""
        with patch.object(websocket_manager, 'send_progress', new_callable=AsyncMock) as mock_send:
            await event_emitter.emit_progress("需求分析", 75, "分析进行中...")

            mock_send.assert_called_once_with(
                "test-emitter-workflow",
                "需求分析",
                75,
                "分析进行中..."
            )

    @pytest.mark.asyncio
    async def test_emit_agent_start(self, event_emitter):
        """测试发射 Agent 开始事件"""
        with patch.object(websocket_manager, 'send_agent_status', new_callable=AsyncMock) as mock_send:
            await event_emitter.emit_agent_start("prd_generator", {"input": "测试输入"})

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] == "test-emitter-workflow"
            assert args[1] == "prd_generator"
            assert args[2] == "started"
            # EventEmitter wraps input_data in {"input": input_data}
            assert args[3] == {"input": {"input": "测试输入"}}

    @pytest.mark.asyncio
    async def test_emit_agent_complete(self, event_emitter):
        """测试发射 Agent 完成事件"""
        with patch.object(websocket_manager, 'send_agent_status', new_callable=AsyncMock) as mock_send:
            result = {"output": "PRD文档内容"}
            await event_emitter.emit_agent_complete("prd_generator", result)

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[2] == "completed"
            assert args[3] == result

    @pytest.mark.asyncio
    async def test_emit_agent_failed(self, event_emitter):
        """测试发射 Agent 失败事件"""
        with patch.object(websocket_manager, 'send_agent_status', new_callable=AsyncMock) as mock_send:
            await event_emitter.emit_agent_failed("prd_generator", "执行超时")

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[2] == "failed"
            assert args[3]["error"] == "执行超时"

    @pytest.mark.asyncio
    async def test_emit_checkpoint(self, event_emitter):
        """测试发射检查点事件"""
        with patch.object(websocket_manager, 'send_checkpoint', new_callable=AsyncMock) as mock_send:
            await event_emitter.emit_checkpoint(
                "checkpoint-001",
                "确认需求",
                {"summary": "需求分析完成"}
            )

            mock_send.assert_called_once_with(
                "test-emitter-workflow",
                "checkpoint-001",
                "确认需求",
                {"summary": "需求分析完成"}
            )

    @pytest.mark.asyncio
    async def test_emit_complete(self, event_emitter):
        """测试发射完成事件"""
        with patch.object(websocket_manager, 'send_complete', new_callable=AsyncMock) as mock_send:
            final_result = {"status": "success"}
            await event_emitter.emit_complete(final_result)

            mock_send.assert_called_once_with(
                "test-emitter-workflow",
                final_result
            )

    @pytest.mark.asyncio
    async def test_emit_error(self, event_emitter):
        """测试发射错误事件"""
        with patch.object(websocket_manager, 'send_error', new_callable=AsyncMock) as mock_send:
            await event_emitter.emit_error("系统错误")

            mock_send.assert_called_once_with(
                "test-emitter-workflow",
                "系统错误"
            )


# ==================== 并发测试 ====================

class TestWebSocketConcurrency:
    """测试 WebSocket 并发性能"""

    @pytest.fixture
    def websocket_manager(self):
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_multiple_workflows(self, websocket_manager):
        """测试多工作流并发"""
        workflows = [f"workflow-{i}" for i in range(10)]
        mock_websockets = []

        # 为每个工作流创建连接
        for wf_id in workflows:
            mock_ws = AsyncMock()
            mock_websockets.append((wf_id, mock_ws))
            await websocket_manager.connect(mock_ws, wf_id)

        # 并发发送进度更新
        async def send_progress(wf_id, progress):
            await websocket_manager.send_progress(wf_id, "step-1", progress, f"进度 {progress}%")

        tasks = [send_progress(wf_id, i * 10) for i, wf_id in enumerate(workflows)]
        await asyncio.gather(*tasks)

        # 验证每个工作流都收到了消息
        for wf_id, mock_ws in mock_websockets:
            assert mock_ws.send_text.called

    @pytest.mark.asyncio
    async def test_high_frequency_updates(self, websocket_manager):
        """测试高频更新"""
        workflow_id = "high-freq-workflow"

        mock_websocket = AsyncMock()
        await websocket_manager.connect(mock_websocket, workflow_id)

        # 快速发送100个进度更新
        update_count = 100
        for i in range(update_count):
            await websocket_manager.send_progress(
                workflow_id,
                "step-1",
                int((i + 1) / update_count * 100),
                f"更新 {i+1}/{update_count}"
            )

        # 验证所有消息都已发送
        assert mock_websocket.send_text.call_count == update_count

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, websocket_manager):
        """测试向多个客户端广播"""
        workflow_id = "broadcast-workflow"

        # 创建多个客户端连接
        mock_clients = [AsyncMock() for _ in range(5)]
        for client in mock_clients:
            await websocket_manager.connect(client, workflow_id)

        # 发送广播消息
        await websocket_manager.broadcast_to_workflow(
            workflow_id,
            {"type": "test", "message": "广播测试"}
        )

        # 验证所有客户端都收到了消息
        for client in mock_clients:
            assert client.send_text.called
            sent_message = json.loads(client.send_text.call_args[0][0])
            assert sent_message["type"] == "test"
            assert sent_message["message"] == "广播测试"

    @pytest.mark.asyncio
    async def test_disconnected_client_cleanup(self, websocket_manager):
        """测试断开连接的客户端清理"""
        workflow_id = "cleanup-workflow"

        # 创建一个会抛出异常的模拟 WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_text.side_effect = Exception("Connection closed")

        await websocket_manager.connect(mock_ws, workflow_id)

        # 尝试发送消息（应该清理断开的连接）
        await websocket_manager.send_progress(workflow_id, "step-1", 50, "测试")

        # 验证连接已被清理
        assert workflow_id not in websocket_manager.active_connections


# ==================== 集成场景测试 ====================

class TestWebSocketIntegrationScenarios:
    """测试 WebSocket 集成场景"""

    @pytest.fixture
    def websocket_manager(self):
        return WebSocketManager()

    @pytest.fixture
    def progress_tracker(self):
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_progress_tracker_with_websocket(self, progress_tracker):
        """测试进度追踪器与 WebSocket 集成"""
        workflow_id = "integration-workflow"

        # 使用全局 WebSocketManager 并设置模拟连接
        from app.websocket.manager import websocket_manager as global_ws_manager
        mock_websocket = AsyncMock()
        original_connections = global_ws_manager.active_connections
        global_ws_manager.active_connections = {workflow_id: [mock_websocket]}

        try:
            # 初始化工作流
            wf_id = progress_tracker.initialize_workflow(
                user_input="测试集成",
                template_name="prd_only"
            )

            # 执行步骤
            workflow = progress_tracker.get_workflow(wf_id)
            step = workflow.steps[0]

            progress_tracker.start_step(wf_id, step.id)
            progress_tracker.update_step_progress(wf_id, step.id, 50, "执行中...")
            progress_tracker.complete_step(wf_id, step.id, "完成")

            # 手动触发 WebSocket 发送来验证集成
            await global_ws_manager.send_progress(
                workflow_id,
                step.name,
                workflow.overall_progress,
                "测试完成"
            )

            # 验证 WebSocket 收到了消息
            assert mock_websocket.send_text.called
        finally:
            # 恢复原始状态
            global_ws_manager.active_connections = original_connections

    @pytest.mark.asyncio
    async def test_complete_workflow_with_events(self):
        """测试完整工作流的事件流"""
        workflow_id = "complete-events-workflow"

        # 使用全局 WebSocketManager 并设置模拟连接
        from app.websocket.manager import websocket_manager as global_ws_manager
        mock_websocket = AsyncMock()
        original_connections = global_ws_manager.active_connections
        global_ws_manager.active_connections = {workflow_id: [mock_websocket]}

        try:
            emitter = EventEmitter(workflow_id)

            # 模拟完整工作流的事件序列
            events = [
                ("emit_agent_start", ["intent_classifier", {"input": "测试"}]),
                ("emit_progress", ["intent_classification", 50, "分析中..."]),
                ("emit_agent_complete", ["intent_classifier", {"intent": "prd_generation"}]),
                ("emit_agent_start", ["task_planner", {"intent": "prd_generation"}]),
                ("emit_progress", ["planning", 75, "规划中..."]),
                ("emit_agent_complete", ["task_planner", {"plan": ["step1", "step2"]}]),
                ("emit_complete", [{"result": "工作流完成"}])
            ]

            for event_method, args in events:
                method = getattr(emitter, event_method)
                await method(*args)

            # 验证所有事件都已发送
            assert mock_websocket.send_text.call_count == len(events)
        finally:
            # 恢复原始状态
            global_ws_manager.active_connections = original_connections

    @pytest.mark.asyncio
    async def test_checkpoint_interaction_flow(self):
        """测试检查点交互流程"""
        workflow_id = "checkpoint-flow-workflow"

        # 使用全局 WebSocketManager 并设置模拟连接
        from app.websocket.manager import websocket_manager as global_ws_manager
        mock_websocket = AsyncMock()
        original_connections = global_ws_manager.active_connections
        global_ws_manager.active_connections = {workflow_id: [mock_websocket]}

        try:
            emitter = EventEmitter(workflow_id)

            # 发送检查点事件
            await emitter.emit_checkpoint(
                "checkpoint-001",
                "确认需求分析结果",
                {
                    "summary": "需求分析完成",
                    "requirements": ["用户管理", "权限控制"],
                    "questions": ["是否需要支持多院区？"]
                }
            )

            # 验证检查点事件已发送
            sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert sent_message["type"] == "checkpoint"
            assert sent_message["checkpoint_id"] == "checkpoint-001"
        finally:
            # 恢复原始状态
            global_ws_manager.active_connections = original_connections

    @pytest.mark.asyncio
    async def test_error_handling_in_event_flow(self):
        """测试事件流中的错误处理"""
        workflow_id = "error-flow-workflow"

        # 使用全局 WebSocketManager 并设置模拟连接
        from app.websocket.manager import websocket_manager as global_ws_manager
        mock_websocket = AsyncMock()
        original_connections = global_ws_manager.active_connections
        global_ws_manager.active_connections = {workflow_id: [mock_websocket]}

        try:
            emitter = EventEmitter(workflow_id)

            # 发送一些正常事件
            await emitter.emit_progress("step-1", 50, "正常执行...")

            # 发送错误事件
            await emitter.emit_error("执行失败: 连接超时")

            # 验证错误事件已发送
            calls = mock_websocket.send_text.call_args_list
            error_call = None
            for call_args in calls:
                message = json.loads(call_args[0][0])
                if message.get("type") == "error":
                    error_call = message
                    break

            assert error_call is not None
            assert "连接超时" in error_call["error"]
        finally:
            # 恢复原始状态
            global_ws_manager.active_connections = original_connections


# ==================== 主函数 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
