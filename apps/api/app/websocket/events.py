# apps/api/app/websocket/events.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Optional
from .manager import websocket_manager


class EventEmitter:
    """事件发射器 - 供 Agent 系统发送事件"""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id

    async def emit_progress(self, step: str, progress: int, detail: str = ""):
        """发射进度事件"""
        await websocket_manager.send_progress(
            self.workflow_id, step, progress, detail
        )

    async def emit_agent_start(self, agent_name: str, input_data: dict):
        """发射 Agent 开始事件"""
        await websocket_manager.send_agent_status(
            self.workflow_id, agent_name, "started",
            {"input": input_data}
        )

    async def emit_agent_complete(self, agent_name: str, result: dict):
        """发射 Agent 完成事件"""
        await websocket_manager.send_agent_status(
            self.workflow_id, agent_name, "completed", result
        )

    async def emit_agent_failed(self, agent_name: str, error: str):
        """发射 Agent 失败事件"""
        await websocket_manager.send_agent_status(
            self.workflow_id, agent_name, "failed",
            {"error": error}
        )

    async def emit_checkpoint(self, checkpoint_id: str, title: str, content: dict):
        """发射检查点事件"""
        await websocket_manager.send_checkpoint(
            self.workflow_id, checkpoint_id, title, content
        )

    async def emit_complete(self, final_result: dict):
        """发射完成事件"""
        await websocket_manager.send_complete(self.workflow_id, final_result)

    async def emit_error(self, error: str):
        """发射错误事件"""
        await websocket_manager.send_error(self.workflow_id, error)
