# apps/api/app/websocket/router.py
import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

logger = logging.getLogger(__name__)

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import websocket_manager

websocket_router = APIRouter()


@websocket_router.websocket("/workflow/{workflow_id}")
async def workflow_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket 端点 - 客户端连接以接收实时更新"""
    await websocket_manager.connect(websocket, workflow_id)
    try:
        while True:
            # 接收客户端消息（如用户确认检查点）
            data = await websocket.receive_text()
            # 处理客户端指令（如 resume, modify 等）
            await handle_client_message(workflow_id, data)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, workflow_id)


@websocket_router.websocket("/collaboration/{room_id}/{user_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
    user_name: str = "Anonymous",
    user_color: str = "#4ECDC4",
):
    """WebSocket endpoint for real-time PRD collaboration"""
    # Parse query params for user info
    query = dict(websocket.query_params)
    user_name = query.get("user_name", user_name)
    user_color = query.get("user_color", user_color)

    await websocket_manager.connect_collaboration(websocket, room_id, user_id, user_name, user_color)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                # Relay message to other collaborators in the room
                await websocket_manager.relay_collaboration_message(room_id, user_id, msg)
            except json.JSONDecodeError:
                logger.warning(f"[WebSocket] Invalid JSON from {user_id}: {data[:100]}")
    except WebSocketDisconnect:
        websocket_manager.disconnect_collaboration(websocket, room_id, user_id)
        # Notify others that user left
        await websocket_manager.broadcast_to_collaboration_room(
            room_id, user_id,
            {
                "type": "presence",
                "event": "leave",
                "user": {"id": user_id},
            }
        )


async def handle_client_message(workflow_id: str, data: str):
    """处理客户端发来的消息"""
    import json
    try:
        message = json.loads(data)
        action = message.get("action")

        if action == "resume":
            # 用户确认继续
            checkpoint_id = message.get("checkpoint_id")
            # 通知检查点控制器继续执行
            # Note: checkpoint_controller will be imported when implemented
            # from app.agents.checkpoints import checkpoint_controller
            # await checkpoint_controller.resume(workflow_id, checkpoint_id)
            logger.info(f"[WebSocket] Resume checkpoint {checkpoint_id} for workflow {workflow_id}")

        elif action == "modify":
            # 用户修改后继续
            checkpoint_id = message.get("checkpoint_id")
            modifications = message.get("modifications", {})
            # await checkpoint_controller.modify_and_resume(
            #     workflow_id, checkpoint_id, modifications
            # )
            logger.info(f"[WebSocket] Modify checkpoint {checkpoint_id} for workflow {workflow_id}: {modifications}")

        elif action == "skip":
            # 用户跳过当前步骤
            checkpoint_id = message.get("checkpoint_id")
            # await checkpoint_controller.skip(workflow_id, checkpoint_id)
            logger.info(f"[WebSocket] Skip checkpoint {checkpoint_id} for workflow {workflow_id}")

    except Exception as e:
        logger.error(f"[WebSocket] Error handling client message: {e}")
