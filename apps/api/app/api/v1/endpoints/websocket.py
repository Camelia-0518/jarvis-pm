"""WebSocket endpoints for real-time collaboration

Supports:
- Multi-user cursor sync
- Selection sync
- Document update broadcast
- Chat messages
- Presence (join/leave)
"""

import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class CollaborationRoom:
    """A single collaboration room (e.g., one PRD document)"""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.connections: Dict[WebSocket, dict] = {}  # ws -> user_info
        self._lock = asyncio.Lock()

    async def add(self, websocket: WebSocket, user_info: dict):
        async with self._lock:
            self.connections[websocket] = user_info

    async def remove(self, websocket: WebSocket) -> dict:
        async with self._lock:
            return self.connections.pop(websocket, {})

    def get_users(self) -> list:
        return [
            {
                "id": info.get("id"),
                "name": info.get("name"),
                "color": info.get("color"),
                "cursor": info.get("cursor"),
                "selection": info.get("selection"),
                "lastSeen": info.get("last_seen", 0),
            }
            for info in self.connections.values()
        ]

    def update_user_state(self, websocket: WebSocket, state_update: dict):
        if websocket in self.connections:
            self.connections[websocket].update(state_update)

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """Broadcast message to all connected clients in this room"""
        disconnected = []
        for ws in list(self.connections.keys()):
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Clean up dead connections
        for ws in disconnected:
            self.connections.pop(ws, None)

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    def __len__(self):
        return len(self.connections)


class RoomManager:
    """Manages all collaboration rooms"""

    def __init__(self):
        self.rooms: Dict[str, CollaborationRoom] = {}

    def get_or_create(self, room_id: str) -> CollaborationRoom:
        if room_id not in self.rooms:
            self.rooms[room_id] = CollaborationRoom(room_id)
        return self.rooms[room_id]

    def cleanup_empty(self, room_id: str):
        if room_id in self.rooms and len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]
            logger.info("Cleaned up empty room: %s", room_id)


# Global room manager instance
room_manager = RoomManager()


@router.websocket("/ws/collaboration/{room_id}/{user_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    room_id: str,
    user_id: str,
):
    """
    WebSocket endpoint for real-time collaboration on a document.

    URL: ws://host:port/api/v1/ws/collaboration/{room_id}/{user_id}?user_name=xxx&user_color=xxx

    Message Protocol (JSON):
    - Client -> Server:
      { "type": "cursor", "data": { "x": 100, "y": 200, "documentId": "doc-1" } }
      { "type": "selection", "data": { "start": 10, "end": 20, "documentId": "doc-1" } }
      { "type": "update", "data": { "operation": "insert", "position": 5, "text": "hello", "documentId": "doc-1" } }
      { "type": "chat", "content": "Hello everyone" }
      { "type": "ping" }

    - Server -> Client:
      { "type": "init", "collaborators": [...] }
      { "type": "presence", "event": "join|leave", "user": {...} }
      { "type": "cursor", "userId": "...", "userName": "...", "color": "...", "data": {...} }
      { "type": "selection", "userId": "...", "userName": "...", "color": "...", "data": {...} }
      { "type": "update", "userId": "...", "userName": "...", "data": {...} }
      { "type": "chat", "userId": "...", "userName": "...", "content": "...", "timestamp": 1234567890 }
      { "type": "pong" }
    """
    # Extract query params
    user_name = websocket.query_params.get("user_name", "Anonymous")
    user_color = websocket.query_params.get("user_color", "#3B82F6")

    user_info = {
        "id": user_id,
        "name": user_name,
        "color": user_color,
        "last_seen": 0,
    }

    room = room_manager.get_or_create(room_id)

    # Accept connection
    await websocket.accept()
    await room.add(websocket, user_info)

    logger.info("User %s joined room %s (total: %d)", user_id, room_id, len(room))

    # Send init message with current collaborators
    await room.send_personal(websocket, {
        "type": "init",
        "collaborators": room.get_users(),
    })

    # Broadcast join to others
    await room.broadcast({
        "type": "presence",
        "event": "join",
        "user": user_info,
    }, exclude=websocket)

    # Heartbeat/ping-pong
    ping_interval = 10  # seconds
    last_pong = asyncio.get_event_loop().time()

    async def heartbeat():
        nonlocal last_pong
        while True:
            await asyncio.sleep(ping_interval)
            now = asyncio.get_event_loop().time()
            if now - last_pong > ping_interval * 2:
                # Client hasn't responded, close connection
                logger.warning("Heartbeat timeout for user %s in room %s", user_id, room_id)
                try:
                    await websocket.close(code=1001)
                except Exception:
                    pass
                break
            try:
                await room.send_personal(websocket, {"type": "ping"})
            except Exception:
                break

    # Run heartbeat in background
    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_json()
            except Exception:
                break

            message_type = data.get("type", "unknown")

            # Update last activity
            room.update_user_state(websocket, {"last_seen": asyncio.get_event_loop().time()})

            if message_type == "cursor":
                cursor_data = data.get("data", {})
                room.update_user_state(websocket, {"cursor": cursor_data})
                await room.broadcast({
                    "type": "cursor",
                    "userId": user_id,
                    "userName": user_name,
                    "color": user_color,
                    "data": cursor_data,
                }, exclude=websocket)

            elif message_type == "selection":
                selection_data = data.get("data", {})
                room.update_user_state(websocket, {"selection": selection_data})
                await room.broadcast({
                    "type": "selection",
                    "userId": user_id,
                    "userName": user_name,
                    "color": user_color,
                    "data": selection_data,
                }, exclude=websocket)

            elif message_type == "update":
                update_data = data.get("data", {})
                await room.broadcast({
                    "type": "update",
                    "userId": user_id,
                    "userName": user_name,
                    "data": update_data,
                }, exclude=websocket)

            elif message_type == "chat":
                content = data.get("content", "")
                timestamp = data.get("timestamp", int(asyncio.get_event_loop().time() * 1000))
                await room.broadcast({
                    "type": "chat",
                    "userId": user_id,
                    "userName": user_name,
                    "color": user_color,
                    "content": content,
                    "timestamp": timestamp,
                })

            elif message_type == "pong":
                last_pong = asyncio.get_event_loop().time()

            elif message_type == "ping":
                await room.send_personal(websocket, {"type": "pong"})

            else:
                # Unknown message type, echo back
                await room.send_personal(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                })

    except WebSocketDisconnect:
        logger.info("User %s disconnected from room %s", user_id, room_id)
    except Exception as e:
        logger.warning("WebSocket error for user %s in room %s: %s", user_id, room_id, e)
    finally:
        # Cancel heartbeat
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        # Remove user and broadcast leave
        removed_info = await room.remove(websocket)
        await room.broadcast({
            "type": "presence",
            "event": "leave",
            "user": removed_info or user_info,
        })

        # Cleanup empty room
        room_manager.cleanup_empty(room_id)
        logger.info("User %s left room %s (remaining: %d)", user_id, room_id, len(room))
