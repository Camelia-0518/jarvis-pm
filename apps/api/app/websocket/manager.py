# apps/api/app/websocket/manager.py
import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, List, Optional
from fastapi import WebSocket
import json

from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器 - 管理所有客户端连接"""

    def __init__(self):
        # 存储活跃连接: {workflow_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储用户连接: {user_id: workflow_id}
        self.user_workflows: Dict[str, str] = {}

        # Collaboration rooms: {room_id: {user_id: {websocket, name, color, ...}}}
        self.collaboration_rooms: Dict[str, Dict[str, dict]] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """接受新连接"""
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)
        logger.info(f"[WebSocket] Client connected to workflow: {workflow_id}")

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        """断开连接"""
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].remove(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]
        logger.info(f"[WebSocket] Client disconnected from workflow: {workflow_id}")

    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """向特定工作流的所有客户端广播消息"""
        if workflow_id not in self.active_connections:
            return

        # 添加时间戳
        message["timestamp"] = datetime.now().isoformat()
        message_str = json.dumps(message, ensure_ascii=False)

        # 发送给所有连接的客户端
        disconnected = []
        for websocket in self.active_connections[workflow_id]:
            try:
                await websocket.send_text(message_str)
            except Exception:
                disconnected.append(websocket)

        # 清理断开的连接
        for websocket in disconnected:
            self.disconnect(websocket, workflow_id)

    async def send_progress(self, workflow_id: str, step: str, progress: int, detail: str = ""):
        """发送进度更新"""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "progress",
            "step": step,
            "progress": progress,
            "detail": detail
        })

    async def send_agent_status(self, workflow_id: str, agent_name: str, status: str, result: Optional[dict] = None):
        """发送 Agent 状态更新"""
        message = {
            "type": "agent_status",
            "agent": agent_name,
            "status": status  # "started", "completed", "failed"
        }
        if result:
            message["result"] = result
        await self.broadcast_to_workflow(workflow_id, message)

    async def send_checkpoint(self, workflow_id: str, checkpoint_id: str, title: str, content: dict):
        """发送检查点（等待用户确认）"""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "checkpoint",
            "checkpoint_id": checkpoint_id,
            "title": title,
            "content": content
        })

    async def send_complete(self, workflow_id: str, final_result: dict):
        """发送完成事件"""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "complete",
            "result": final_result
        })

    async def send_error(self, workflow_id: str, error: str):
        """发送错误事件"""
        await self.broadcast_to_workflow(workflow_id, {
            "type": "error",
            "error": error
        })

    # ==================== Collaboration Room Methods ====================

    async def connect_collaboration(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str, user_color: str):
        """Accept a new collaboration room connection"""
        await websocket.accept()
        if room_id not in self.collaboration_rooms:
            self.collaboration_rooms[room_id] = {}

        self.collaboration_rooms[room_id][user_id] = {
            "websocket": websocket,
            "name": user_name,
            "color": user_color,
            "last_seen": datetime.now().isoformat(),
        }
        logger.info(f"[WebSocket] User {user_name} ({user_id}) joined collaboration room: {room_id}")

        # Send init message with current collaborators
        collaborators = []
        for uid, info in self.collaboration_rooms[room_id].items():
            if uid != user_id:
                collaborators.append({
                    "id": uid,
                    "name": info["name"],
                    "color": info["color"],
                    "lastSeen": int(datetime.now().timestamp() * 1000),
                })
        try:
            await websocket.send_text(json.dumps({"type": "init", "collaborators": collaborators}, ensure_ascii=False))
        except Exception:
            pass

        # Broadcast join to others
        await self.broadcast_to_collaboration_room(
            room_id, user_id,
            {
                "type": "presence",
                "event": "join",
                "user": {
                    "id": user_id,
                    "name": user_name,
                    "color": user_color,
                    "lastSeen": int(datetime.now().timestamp() * 1000),
                },
            }
        )

    def disconnect_collaboration(self, websocket: WebSocket, room_id: str, user_id: str):
        """Disconnect from collaboration room"""
        if room_id in self.collaboration_rooms and user_id in self.collaboration_rooms[room_id]:
            del self.collaboration_rooms[room_id][user_id]
            if not self.collaboration_rooms[room_id]:
                del self.collaboration_rooms[room_id]
        logger.info(f"[WebSocket] User {user_id} left collaboration room: {room_id}")

    async def broadcast_to_collaboration_room(self, room_id: str, sender_id: str, message: dict):
        """Broadcast message to all collaborators in a room except sender"""
        if room_id not in self.collaboration_rooms:
            return
        message["timestamp"] = int(datetime.now().timestamp() * 1000)
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = []
        for uid, info in self.collaboration_rooms[room_id].items():
            if uid == sender_id:
                continue
            try:
                await info["websocket"].send_text(message_str)
            except Exception:
                disconnected.append(uid)
        for uid in disconnected:
            if uid in self.collaboration_rooms.get(room_id, {}):
                del self.collaboration_rooms[room_id][uid]

    async def relay_collaboration_message(self, room_id: str, sender_id: str, message: dict):
        """Relay a message from one collaborator to all others"""
        await self.broadcast_to_collaboration_room(room_id, sender_id, message)


# 全局管理器实例
websocket_manager = WebSocketManager()