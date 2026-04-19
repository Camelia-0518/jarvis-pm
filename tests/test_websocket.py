#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WebSocket 连接测试"""

import asyncio
import websockets
import json
import pytest


async def test_websocket_connection():
    """测试 WebSocket 连接"""
    workflow_id = "test-workflow-123"
    uri = f"ws://localhost:8000/ws/workflow/{workflow_id}"

    async with websockets.connect(uri) as websocket:
        print(f"[Test] Connected to {uri}")

        # 接收消息
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)
                print(f"[Test] Received: {data}")
        except asyncio.TimeoutError:
            print("[Test] Timeout waiting for messages")


def test_websocket_manager():
    """测试 WebSocketManager 基本功能"""
    from app.websocket import WebSocketManager

    manager = WebSocketManager()
    assert manager is not None
    assert isinstance(manager.active_connections, dict)
    assert isinstance(manager.user_workflows, dict)
    print("[Test] WebSocketManager initialized successfully")


def test_event_emitter():
    """测试 EventEmitter 基本功能"""
    from app.websocket import EventEmitter

    emitter = EventEmitter("test-workflow-123")
    assert emitter is not None
    assert emitter.workflow_id == "test-workflow-123"
    print("[Test] EventEmitter initialized successfully")


@pytest.mark.asyncio
async def test_broadcast_message():
    """测试广播消息功能"""
    from app.websocket import websocket_manager

    # 测试向不存在的 workflow 发送消息（不应报错）
    await websocket_manager.send_progress("non-existent-workflow", "test_step", 50, "test detail")
    print("[Test] Broadcast to non-existent workflow handled correctly")


if __name__ == "__main__":
    # Run basic tests
    print("=" * 50)
    print("Running WebSocket Tests")
    print("=" * 50)

    test_websocket_manager()
    test_event_emitter()

    asyncio.run(test_broadcast_message())

    print("=" * 50)
    print("All basic tests passed!")
    print("=" * 50)
