# Jarvis PM Agent 系统优化 - 第一阶段实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 解决"执行时间长"和"输出质量不稳定"的核心痛点，实现流式输出、进度可视化、人机协作检查点、医疗行业模板系统和故障恢复机制

**Architecture:** 在现有 FastAPI + Agent 系统基础上，添加 WebSocket 实时通信层、进度追踪器、检查点控制器和模板引擎。保持向后兼容，前端使用简单 HTML/JS 演示，用户可后续自行优化。

**Tech Stack:** FastAPI, WebSocket, Python asyncio, Jinja2 Templates, SQLite/JSON 存储

---

## 前置检查

**Step 1: 确认项目结构**

Run: `ls -la apps/api/app/agents/`
Expected: 显示 agents/ 目录存在（包含 base.py, strategy.py, agents/ 等）

**Step 2: 确认依赖**

Run: `cat apps/api/requirements.txt | grep -E "fastapi|websockets"`
Expected: fastapi>=0.100.0, websockets 已安装

---

## Task 1: WebSocket 基础设施

**Files:**
- Create: `apps/api/app/websocket/__init__.py`
- Create: `apps/api/app/websocket/manager.py`
- Create: `apps/api/app/websocket/events.py`
- Modify: `apps/api/main.py` - 添加 WebSocket 路由

**Step 1: 创建 WebSocket 连接管理器**

```python
# apps/api/app/websocket/__init__.py
from .manager import WebSocketManager
from .events import EventEmitter

__all__ = ["WebSocketManager", "EventEmitter"]
```

```python
# apps/api/app/websocket/manager.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, List, Optional
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime


class WebSocketManager:
    """WebSocket 连接管理器 - 管理所有客户端连接"""

    def __init__(self):
        # 存储活跃连接: {workflow_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 存储用户连接: {user_id: workflow_id}
        self.user_workflows: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, workflow_id: str):
        """接受新连接"""
        await websocket.accept()
        if workflow_id not in self.active_connections:
            self.active_connections[workflow_id] = []
        self.active_connections[workflow_id].append(websocket)
        print(f"[WebSocket] Client connected to workflow: {workflow_id}")

    def disconnect(self, websocket: WebSocket, workflow_id: str):
        """断开连接"""
        if workflow_id in self.active_connections:
            self.active_connections[workflow_id].remove(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]
        print(f"[WebSocket] Client disconnected from workflow: {workflow_id}")

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


# 全局管理器实例
websocket_manager = WebSocketManager()
```

**Step 2: 创建事件发射器（供 Agent 系统调用）**

```python
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
```

**Step 3: 在 main.py 中添加 WebSocket 路由**

Modify: `apps/api/main.py`

在文件顶部导入区域添加：
```python
# 在现有导入后添加
from app.websocket import websocket_manager
from app.websocket.router import websocket_router
```

在创建 FastAPI app 后添加路由：
```python
# 在 app = FastAPI(...) 之后添加
app.include_router(websocket_router, prefix="/ws")
```

创建 WebSocket 路由文件：

```python
# apps/api/app/websocket/router.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

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
            from app.agents.checkpoints import checkpoint_controller
            await checkpoint_controller.resume(workflow_id, checkpoint_id)

        elif action == "modify":
            # 用户修改后继续
            checkpoint_id = message.get("checkpoint_id")
            modifications = message.get("modifications", {})
            await checkpoint_controller.modify_and_resume(
                workflow_id, checkpoint_id, modifications
            )

        elif action == "skip":
            # 用户跳过当前步骤
            checkpoint_id = message.get("checkpoint_id")
            await checkpoint_controller.skip(workflow_id, checkpoint_id)

    except Exception as e:
        print(f"[WebSocket] Error handling client message: {e}")
```

**Step 4: 创建测试脚本**

Create: `tests/test_websocket.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WebSocket 连接测试"""

import asyncio
import websockets
import json


async def test_websocket():
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


if __name__ == "__main__":
    asyncio.run(test_websocket())
```

**Step 5: 运行测试**

Run: `cd apps/api && python -m pytest tests/test_websocket.py -v -s`
Expected: 测试通过，能够连接 WebSocket 并接收消息

**Step 6: Commit**

```bash
git add apps/api/app/websocket/ apps/api/main.py tests/test_websocket.py
git commit -m "feat: add WebSocket infrastructure for real-time updates

- WebSocket connection manager for workflow-based communication
- Event emitter for Agent system integration
- Client message handling (resume/modify/skip actions)
- Test script for WebSocket connectivity"
```

---

## Task 2: 进度追踪器 (Progress Tracker)

**Files:**
- Create: `apps/api/app/agents/progress.py`
- Modify: `apps/api/app/agents/strategy.py` - 集成进度追踪

**Step 1: 创建进度追踪器**

```python
# apps/api/app/agents/progress.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"  # 等待用户确认


@dataclass
class StepInfo:
    """步骤信息"""
    id: str
    name: str
    agent_name: str
    status: StepStatus = StepStatus.PENDING
    progress: int = 0  # 0-100
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    detail: str = ""  # 当前正在做什么
    result_summary: str = ""  # 结果摘要


@dataclass
class WorkflowProgress:
    """工作流进度"""
    workflow_id: str
    user_input: str = ""
    steps: List[StepInfo] = field(default_factory=list)
    current_step_index: int = -1
    overall_progress: int = 0
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ProgressTracker:
    """进度追踪器 - 跟踪 Agent 执行进度"""

    # 预定义的工作流模板
    WORKFLOW_TEMPLATES = {
        "full_workflow": [
            {"id": "intent", "name": "意图识别", "agent": "IntentClassifier", "weight": 5},
            {"id": "plan", "name": "任务规划", "agent": "TaskPlanner", "weight": 5},
            {"id": "requirement", "name": "需求分析", "agent": "RequirementAgent", "weight": 25},
            {"id": "competitor", "name": "竞品分析", "agent": "CompetitorAnalyst", "weight": 20},
            {"id": "compliance", "name": "合规检查", "agent": "ComplianceChecker", "weight": 15},
            {"id": "prd", "name": "PRD生成", "agent": "PRDAgent", "weight": 25},
            {"id": "review", "name": "评审准备", "agent": "ReviewPreparer", "weight": 5},
        ],
        "prd_only": [
            {"id": "intent", "name": "意图识别", "agent": "IntentClassifier", "weight": 10},
            {"id": "plan", "name": "任务规划", "agent": "TaskPlanner", "weight": 10},
            {"id": "prd", "name": "PRD生成", "agent": "PRDAgent", "weight": 80},
        ],
        "compliance_only": [
            {"id": "intent", "name": "意图识别", "agent": "IntentClassifier", "weight": 10},
            {"id": "compliance", "name": "合规检查", "agent": "ComplianceChecker", "weight": 90},
        ]
    }

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.progress = WorkflowProgress(workflow_id=workflow_id)
        self._callbacks: List[Callable] = []
        self._step_map: Dict[str, StepInfo] = {}

    def register_callback(self, callback: Callable):
        """注册进度更新回调"""
        self._callbacks.append(callback)

    def _notify(self, event_type: str, data: dict):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                asyncio.create_task(callback(event_type, data))
            except Exception as e:
                print(f"[ProgressTracker] Callback error: {e}")

    def initialize_workflow(self, workflow_type: str, user_input: str):
        """初始化工作流"""
        self.progress.user_input = user_input
        template = self.WORKFLOW_TEMPLATES.get(workflow_type, self.WORKFLOW_TEMPLATES["full_workflow"])

        for step_template in template:
            step = StepInfo(
                id=step_template["id"],
                name=step_template["name"],
                agent_name=step_template["agent"],
            )
            self.progress.steps.append(step)
            self._step_map[step.id] = step

        self.progress.status = "running"
        self._notify("workflow_started", self._to_dict())

    def start_step(self, step_id: str, detail: str = ""):
        """开始一个步骤"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()
        step.detail = detail
        self.progress.current_step_index = self.progress.steps.index(step)

        self._notify("step_started", {
            "step_id": step_id,
            "step_name": step.name,
            "detail": detail
        })

    def update_step_progress(self, step_id: str, progress: int, detail: str = ""):
        """更新步骤进度"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.progress = progress
        if detail:
            step.detail = detail

        # 计算总体进度
        self._calculate_overall_progress()

        self._notify("step_progress", {
            "step_id": step_id,
            "step_name": step.name,
            "step_progress": progress,
            "overall_progress": self.progress.overall_progress,
            "detail": detail
        })

    def complete_step(self, step_id: str, result_summary: str = ""):
        """完成一个步骤"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.status = StepStatus.COMPLETED
        step.progress = 100
        step.end_time = datetime.now()
        step.result_summary = result_summary

        if step.start_time:
            step.duration_ms = int((step.end_time - step.start_time).total_seconds() * 1000)

        self._calculate_overall_progress()

        self._notify("step_completed", {
            "step_id": step_id,
            "step_name": step.name,
            "duration_ms": step.duration_ms,
            "result_summary": result_summary,
            "overall_progress": self.progress.overall_progress
        })

    def fail_step(self, step_id: str, error: str):
        """步骤失败"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.status = StepStatus.FAILED
        step.end_time = datetime.now()
        step.result_summary = f"Error: {error}"

        self.progress.status = "failed"

        self._notify("step_failed", {
            "step_id": step_id,
            "step_name": step.name,
            "error": error
        })

    def wait_for_checkpoint(self, step_id: str, checkpoint_title: str):
        """步骤等待用户确认"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.status = StepStatus.WAITING
        step.detail = f"等待用户确认: {checkpoint_title}"

        self._notify("step_waiting", {
            "step_id": step_id,
            "step_name": step.name,
            "checkpoint_title": checkpoint_title
        })

    def complete_workflow(self):
        """完成工作流"""
        self.progress.status = "completed"
        self.progress.completed_at = datetime.now()
        self.progress.overall_progress = 100

        self._notify("workflow_completed", self._to_dict())

    def _calculate_overall_progress(self):
        """计算总体进度"""
        if not self.progress.steps:
            return

        total_weight = sum(
            self.WORKFLOW_TEMPLATES["full_workflow"][i]["weight"]
            for i in range(len(self.progress.steps))
        )

        weighted_progress = 0
        for i, step in enumerate(self.progress.steps):
            weight = self.WORKFLOW_TEMPLATES["full_workflow"][i]["weight"]
            weighted_progress += (step.progress * weight)

        self.progress.overall_progress = int(weighted_progress / total_weight)

    def _to_dict(self) -> dict:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "user_input": self.progress.user_input,
            "status": self.progress.status,
            "overall_progress": self.progress.overall_progress,
            "current_step": self.progress.current_step_index,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "agent": step.agent_name,
                    "status": step.status.value,
                    "progress": step.progress,
                    "detail": step.detail,
                    "duration_ms": step.duration_ms,
                    "result_summary": step.result_summary
                }
                for step in self.progress.steps
            ],
            "created_at": self.progress.created_at.isoformat(),
            "completed_at": self.progress.completed_at.isoformat() if self.progress.completed_at else None
        }

    def get_current_step(self) -> Optional[StepInfo]:
        """获取当前步骤"""
        if 0 <= self.progress.current_step_index < len(self.progress.steps):
            return self.progress.steps[self.progress.current_step_index]
        return None

    def get_step(self, step_id: str) -> Optional[StepInfo]:
        """获取指定步骤"""
        return self._step_map.get(step_id)
```

**Step 2: 修改 Strategy Layer 集成进度追踪**

Modify: `apps/api/app/agents/strategy.py`

在 StrategyLayer 类中添加进度追踪：

```python
# 在 imports 中添加
from .progress import ProgressTracker
from ..websocket import websocket_manager

# 在 StrategyLayer.__init__ 中添加
async def _process_sync(self, user_input: str, context: Optional[Dict]) -> WorkflowContext:
    # ... existing code ...

    # 初始化进度追踪器
    progress_tracker = ProgressTracker(str(workflow.workflow_id))

    # 注册 WebSocket 回调
    async def on_progress(event_type: str, data: dict):
        await websocket_manager.broadcast_to_workflow(
            str(workflow.workflow_id),
            {"type": event_type, "data": data}
        )
    progress_tracker.register_callback(on_progress)

    # 初始化工作流
    workflow_type = "full_workflow"  # 可以根据意图结果调整
    progress_tracker.initialize_workflow(workflow_type, user_input)

    try:
        # 步骤1: 意图识别
        workflow.status = "intent_classification"
        progress_tracker.start_step("intent", "正在分析用户意图...")
        intent_result = await self.intent_classifier.execute({
            "user_input": user_input
        })
        workflow.intent_result = intent_result.data
        progress_tracker.complete_step("intent", f"识别意图: {intent_result.data.get('task_type')}")

        # 步骤2: 任务规划
        workflow.status = "planning"
        progress_tracker.start_step("plan", "正在规划执行步骤...")
        plan_result = await self.task_planner.execute({
            "intent_result": intent_result.data,
            "user_input": user_input,
            "context": context or {}
        })
        workflow.plan = plan_result.data
        progress_tracker.complete_step("plan", f"规划完成: {len(plan_result.data.get('plan', {}).get('steps', []))} 个步骤")

        # 根据计划执行步骤
        await self._execute_plan_with_progress(workflow, progress_tracker)

        # 完成
        workflow.status = "completed"
        workflow.completed_at = datetime.now()
        progress_tracker.complete_workflow()

    except Exception as e:
        workflow.status = "failed"
        progress_tracker.fail_step(progress_tracker.get_current_step().id if progress_tracker.get_current_step() else "unknown", str(e))
        workflow.results.append({
            "step": workflow.status,
            "error": str(e)
        })

    return workflow
```

**Step 3: 创建测试**

Create: `tests/test_progress_tracker.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""进度追踪器测试"""

import pytest
import asyncio
from app.agents.progress import ProgressTracker, StepStatus


@pytest.mark.asyncio
async def test_progress_tracker():
    """测试进度追踪器基本功能"""
    tracker = ProgressTracker("test-workflow")

    # 记录事件
    events = []
    async def on_event(event_type, data):
        events.append((event_type, data))
    tracker.register_callback(on_event)

    # 初始化工作流
    tracker.initialize_workflow("full_workflow", "测试产品")

    assert len(tracker.progress.steps) == 7
    assert tracker.progress.status == "running"

    # 开始步骤
    tracker.start_step("intent", "正在分析...")
    assert tracker.get_step("intent").status == StepStatus.RUNNING

    # 更新进度
    tracker.update_step_progress("intent", 50, "分析中...")
    assert tracker.progress.overall_progress > 0

    # 完成步骤
    tracker.complete_step("intent", "识别成功")
    assert tracker.get_step("intent").status == StepStatus.COMPLETED
    assert tracker.get_step("intent").progress == 100

    # 完成工作流
    tracker.complete_workflow()
    assert tracker.progress.status == "completed"
    assert tracker.progress.overall_progress == 100

    print(f"[Test] Events captured: {len(events)}")
    for event_type, data in events:
        print(f"  - {event_type}: {data.get('step_name', '')}")


if __name__ == "__main__":
    asyncio.run(test_progress_tracker())
```

**Step 4: 运行测试**

Run: `cd apps/api && python -m pytest tests/test_progress_tracker.py -v -s`
Expected: 测试通过，显示所有事件

**Step 5: Commit**

```bash
git add apps/api/app/agents/progress.py tests/test_progress_tracker.py
git add apps/api/app/agents/strategy.py  # 修改的部分
git commit -m "feat: add progress tracker with WebSocket integration

- ProgressTracker class for step-by-step execution tracking
- Weighted progress calculation across all workflow steps
- WebSocket event broadcasting for real-time UI updates
- Support for workflow templates (full/prd-only/compliance-only)"
```

---

## Task 3: 人机协作检查点机制

**Files:**
- Create: `apps/api/app/agents/checkpoints.py`
- Modify: `apps/api/app/agents/strategy.py` - 集成检查点

**Step 1: 创建检查点控制器**

```python
# apps/api/app/agents/checkpoints.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json
import os


class CheckpointAction(Enum):
    RESUME = "resume"      # 继续执行
    MODIFY = "modify"      # 修改后继续
    SKIP = "skip"          # 跳过此步骤
    RETRY = "retry"        # 重试当前步骤


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    workflow_id: str
    step_id: str
    title: str
    description: str
    content: Dict[str, Any]  # 需要用户确认的内容
    action: Optional[CheckpointAction] = None
    modifications: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    status: str = "pending"  # pending, resolved, skipped


class CheckpointController:
    """检查点控制器 - 管理人-AI 协作检查点"""

    # 预定义检查点配置
    CHECKPOINTS_CONFIG = {
        "after_intent": {
            "title": "意图确认",
            "description": "请确认我对您需求的理解是否正确",
            "enabled": True,
            "editable_fields": ["task_type", "entities"]
        },
        "after_plan": {
            "title": "执行计划确认",
            "description": "这个执行计划是否符合您的预期？",
            "enabled": True,
            "editable_fields": ["steps"]
        },
        "after_requirement": {
            "title": "需求分析确认",
            "description": "需求分析是否完整？有没有遗漏的关键点？",
            "enabled": True,
            "editable_fields": ["user_personas", "pain_points", "features"]
        },
        "after_competitor": {
            "title": "竞品分析确认",
            "description": "竞品对标结果是否符合您的认知？",
            "enabled": False,  # 默认关闭
            "editable_fields": ["competitors", "differentiation"]
        },
        "before_prd": {
            "title": "PRD生成前确认",
            "description": "有额外的合规要求或特殊需求要补充吗？",
            "enabled": True,
            "editable_fields": ["compliance_requirements", "special_notes"]
        }
    }

    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._workflow_checkpoints: Dict[str, list] = {}
        self._resolvers: Dict[str, asyncio.Event] = {}
        self._results: Dict[str, Dict[str, Any]] = {}

    def create_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
        step_id: str,
        content: Dict[str, Any],
        config_override: Optional[Dict] = None
    ) -> Checkpoint:
        """创建检查点"""
        config = self.CHECKPOINTS_CONFIG.get(checkpoint_id, {})
        if config_override:
            config.update(config_override)

        checkpoint = Checkpoint(
            id=checkpoint_id,
            workflow_id=workflow_id,
            step_id=step_id,
            title=config.get("title", "确认"),
            description=config.get("description", "请确认"),
            content=content
        )

        self._checkpoints[checkpoint.id] = checkpoint

        if workflow_id not in self._workflow_checkpoints:
            self._workflow_checkpoints[workflow_id] = []
        self._workflow_checkpoints[workflow_id].append(checkpoint.id)

        # 创建等待事件
        self._resolvers[checkpoint.id] = asyncio.Event()

        return checkpoint

    async def wait_for_resolution(
        self,
        checkpoint_id: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """等待检查点被解决"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

        event = self._resolvers[checkpoint_id]

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # 超时自动继续
            checkpoint.action = CheckpointAction.RESUME
            checkpoint.status = "resolved"
            checkpoint.resolved_at = datetime.now()
            return {"action": "resume", "modifications": {}}

        # 返回结果
        return self._results.get(checkpoint_id, {
            "action": checkpoint.action.value if checkpoint.action else "resume",
            "modifications": checkpoint.modifications
        })

    async def resume(self, workflow_id: str, checkpoint_id: str):
        """用户选择继续"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint or checkpoint.workflow_id != workflow_id:
            return False

        checkpoint.action = CheckpointAction.RESUME
        checkpoint.status = "resolved"
        checkpoint.resolved_at = datetime.now()

        self._results[checkpoint_id] = {
            "action": "resume",
            "modifications": {}
        }

        self._resolvers[checkpoint_id].set()
        return True

    async def modify_and_resume(
        self,
        workflow_id: str,
        checkpoint_id: str,
        modifications: Dict[str, Any]
    ):
        """用户修改后继续"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint or checkpoint.workflow_id != workflow_id:
            return False

        checkpoint.action = CheckpointAction.MODIFY
        checkpoint.modifications = modifications
        checkpoint.status = "resolved"
        checkpoint.resolved_at = datetime.now()

        # 更新内容
        checkpoint.content.update(modifications)

        self._results[checkpoint_id] = {
            "action": "modify",
            "modifications": modifications
        }

        self._resolvers[checkpoint_id].set()
        return True

    async def skip(self, workflow_id: str, checkpoint_id: str):
        """用户选择跳过"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint or checkpoint.workflow_id != workflow_id:
            return False

        checkpoint.action = CheckpointAction.SKIP
        checkpoint.status = "skipped"
        checkpoint.resolved_at = datetime.now()

        self._results[checkpoint_id] = {
            "action": "skip",
            "modifications": {}
        }

        self._resolvers[checkpoint_id].set()
        return True

    async def retry(self, workflow_id: str, checkpoint_id: str):
        """用户选择重试"""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint or checkpoint.workflow_id != workflow_id:
            return False

        checkpoint.action = CheckpointAction.RETRY
        checkpoint.status = "resolved"
        checkpoint.resolved_at = datetime.now()

        self._results[checkpoint_id] = {
            "action": "retry",
            "modifications": {}
        }

        self._resolvers[checkpoint_id].set()
        return True

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取检查点"""
        return self._checkpoints.get(checkpoint_id)

    def get_workflow_checkpoints(self, workflow_id: str) -> list:
        """获取工作流的所有检查点"""
        checkpoint_ids = self._workflow_checkpoints.get(workflow_id, [])
        return [self._checkpoints[cid] for cid in checkpoint_ids if cid in self._checkpoints]

    def should_pause_at(self, checkpoint_id: str) -> bool:
        """检查是否应该在此检查点暂停"""
        config = self.CHECKPOINTS_CONFIG.get(checkpoint_id, {})
        return config.get("enabled", False)

    def to_dict(self, checkpoint: Checkpoint) -> dict:
        """转换为字典"""
        return {
            "id": checkpoint.id,
            "title": checkpoint.title,
            "description": checkpoint.description,
            "content": checkpoint.content,
            "step_id": checkpoint.step_id,
            "status": checkpoint.status,
            "created_at": checkpoint.created_at.isoformat(),
            "editable_fields": self.CHECKPOINTS_CONFIG.get(checkpoint.id, {}).get("editable_fields", [])
        }


# 全局检查点控制器实例
checkpoint_controller = CheckpointController()
```

**Step 2: 创建检查点包装器（用于 Strategy Layer）**

```python
# apps/api/app/agents/checkpoints.py （继续添加）

class CheckpointWrapper:
    """检查点包装器 - 简化在 Strategy Layer 中的使用"""

    def __init__(self, workflow_id: str, event_emitter=None):
        self.workflow_id = workflow_id
        self.event_emitter = event_emitter
        self.controller = checkpoint_controller

    async def check(
        self,
        checkpoint_id: str,
        step_id: str,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查点检查

        Returns:
            {"action": "resume|modify|skip|retry", "content": 最终内容}
        """
        if not self.controller.should_pause_at(checkpoint_id):
            # 检查点未启用，直接继续
            return {"action": "resume", "content": content}

        # 创建检查点
        checkpoint = self.controller.create_checkpoint(
            workflow_id=self.workflow_id,
            checkpoint_id=checkpoint_id,
            step_id=step_id,
            content=content
        )

        # 发送检查点事件到前端
        if self.event_emitter:
            await self.event_emitter.emit_checkpoint(
                checkpoint_id=checkpoint.id,
                title=checkpoint.title,
                content=self.controller.to_dict(checkpoint)
            )

        # 等待用户响应
        result = await self.controller.wait_for_resolution(
            checkpoint.id,
            timeout=300  # 5分钟超时
        )

        # 根据用户选择处理
        action = result.get("action", "resume")
        modifications = result.get("modifications", {})

        if action == "modify":
            final_content = {**content, **modifications}
        elif action == "skip":
            final_content = content  # 保持原样，但上层逻辑可能会跳过此步骤
        elif action == "retry":
            final_content = None  # 信号：需要重试
        else:  # resume
            final_content = content

        return {"action": action, "content": final_content}
```

**Step 3: 在 Strategy Layer 中集成检查点**

Modify: `apps/api/app/agents/strategy.py`

添加导入：
```python
from .checkpoints import CheckpointWrapper
from ..websocket.events import EventEmitter
```

修改 `_process_sync` 方法：

```python
async def _process_sync_with_checkpoints(
    self,
    user_input: str,
    context: Optional[Dict]
) -> WorkflowContext:
    """带检查点的同步处理流程"""
    workflow = WorkflowContext(
        workflow_id=uuid4(),
        user_input=user_input
    )
    self._workflows[workflow.workflow_id] = workflow

    # 初始化进度追踪器
    progress_tracker = ProgressTracker(str(workflow.workflow_id))
    event_emitter = EventEmitter(str(workflow.workflow_id))

    async def on_progress(event_type: str, data: dict):
        await websocket_manager.broadcast_to_workflow(
            str(workflow.workflow_id),
            {"type": event_type, "data": data}
        )
    progress_tracker.register_callback(on_progress)

    # 初始化检查点包装器
    checkpoint = CheckpointWrapper(
        workflow_id=str(workflow.workflow_id),
        event_emitter=event_emitter
    )

    progress_tracker.initialize_workflow("full_workflow", user_input)

    try:
        # 步骤1: 意图识别
        workflow.status = "intent_classification"
        progress_tracker.start_step("intent", "正在分析用户意图...")
        intent_result = await self.intent_classifier.execute({
            "user_input": user_input
        })

        # 检查点: 意图确认
        checkpoint_result = await checkpoint.check(
            checkpoint_id="after_intent",
            step_id="intent",
            content={
                "task_type": intent_result.data.get("task_type"),
                "confidence": intent_result.data.get("confidence"),
                "entities": intent_result.data.get("entities", {}),
                "suggested_agents": intent_result.data.get("suggested_agents", [])
            }
        )

        if checkpoint_result["action"] == "retry":
            # 重新执行意图识别（可以修改输入）
            pass

        workflow.intent_result = checkpoint_result["content"]
        progress_tracker.complete_step(
            "intent",
            f"识别意图: {intent_result.data.get('task_type')}"
        )

        # 步骤2: 任务规划
        workflow.status = "planning"
        progress_tracker.start_step("plan", "正在规划执行步骤...")
        plan_result = await self.task_planner.execute({
            "intent_result": intent_result.data,
            "user_input": user_input,
            "context": context or {}
        })

        # 检查点: 计划确认
        checkpoint_result = await checkpoint.check(
            checkpoint_id="after_plan",
            step_id="plan",
            content={
                "workflow_name": plan_result.data.get("plan", {}).get("workflow_name"),
                "steps": [
                    {"id": s["id"], "agent": s["agent_name"], "description": s.get("description", "")}
                    for s in plan_result.data.get("plan", {}).get("steps", [])
                ]
            }
        )

        workflow.plan = plan_result.data
        progress_tracker.complete_step(
            "plan",
            f"规划完成: {len(plan_result.data.get('plan', {}).get('steps', []))} 个步骤"
        )

        # 步骤3+: 执行计划（带检查点）
        await self._execute_plan_with_checkpoints(
            workflow, progress_tracker, checkpoint
        )

        # 完成
        workflow.status = "completed"
        workflow.completed_at = datetime.now()
        progress_tracker.complete_workflow()

    except Exception as e:
        workflow.status = "failed"
        current_step = progress_tracker.get_current_step()
        if current_step:
            progress_tracker.fail_step(current_step.id, str(e))
        workflow.results.append({
            "step": workflow.status,
            "error": str(e)
        })

    return workflow
```

**Step 4: 创建测试**

Create: `tests/test_checkpoints.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查点机制测试"""

import pytest
import asyncio
from app.agents.checkpoints import (
    CheckpointController, CheckpointWrapper,
    CheckpointAction
)


@pytest.mark.asyncio
async def test_checkpoint_lifecycle():
    """测试检查点完整生命周期"""
    controller = CheckpointController()

    # 创建检查点
    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd_generation", "confidence": 0.9}
    )

    assert checkpoint.status == "pending"
    assert checkpoint.workflow_id == "test-workflow"

    # 模拟用户继续
    async def user_resume():
        await asyncio.sleep(0.1)
        await controller.resume("test-workflow", checkpoint.id)

    # 启动用户模拟和等待
    await asyncio.gather(
        user_resume(),
        controller.wait_for_resolution(checkpoint.id)
    )

    assert checkpoint.status == "resolved"
    assert checkpoint.action == CheckpointAction.RESUME


@pytest.mark.asyncio
async def test_checkpoint_modify():
    """测试检查点修改功能"""
    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-workflow",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "prd_generation", "confidence": 0.9}
    )

    # 模拟用户修改
    async def user_modify():
        await asyncio.sleep(0.1)
        await controller.modify_and_resume(
            "test-workflow",
            checkpoint.id,
            {"task_type": "requirement_analysis"}
        )

    result = await asyncio.gather(
        user_modify(),
        controller.wait_for_resolution(checkpoint.id)
    )

    resolution = result[1]
    assert resolution["action"] == "modify"
    assert resolution["modifications"]["task_type"] == "requirement_analysis"


if __name__ == "__main__":
    asyncio.run(test_checkpoint_lifecycle())
    asyncio.run(test_checkpoint_modify())
    print("All checkpoint tests passed!")
```

**Step 5: 运行测试**

Run: `cd apps/api && python -m pytest tests/test_checkpoints.py -v -s`
Expected: 测试通过

**Step 6: Commit**

```bash
git add apps/api/app/agents/checkpoints.py tests/test_checkpoints.py
git commit -m "feat: add human-AI collaborative checkpoint mechanism

- CheckpointController for managing pause/resume/modify/skip actions
- CheckpointWrapper for easy integration in Strategy Layer
- Predefined checkpoints: after_intent, after_plan, after_requirement, before_prd
- WebSocket events for real-time checkpoint notifications
- Timeout handling with automatic resume"
```

---

## Task 4: 医疗行业智能模板系统

**Files:**
- Create: `apps/api/app/agents/templates.py`
- Create: `apps/api/app/agents/templates/medical_slide_lending.json`
- Create: `apps/api/app/agents/templates/medical_admin_system.json`
- Modify: `apps/api/app/agents/agents/task_planner.py` - 集成模板

**Step 1: 创建模板系统核心**

```python
# apps/api/app/agents/templates.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class IndustryTemplate:
    """行业模板"""
    id: str
    name: str
    industry: str  # medical, finance, education, etc.
    description: str
    keywords: List[str]  # 触发关键词
    workflow_type: str  # full_workflow, prd_only, compliance_only

    # PRD 结构
    sections: List[str] = field(default_factory=list)
    mandatory_sections: List[str] = field(default_factory=list)

    # 合规要求
    compliance_required: bool = False
    compliance_categories: List[str] = field(default_factory=list)
    mandatory_checks: List[str] = field(default_factory=list)

    # 竞品分析
    competitor_keywords: List[str] = field(default_factory=list)
    analysis_focus: List[str] = field(default_factory=list)

    # 需求分析
    user_persona_templates: List[Dict[str, str]] = field(default_factory=list)
    common_pain_points: List[str] = field(default_factory=list)

    # 知识库关联
    reference_docs: List[str] = field(default_factory=list)
    related_notes: List[str] = field(default_factory=list)

    # 提示词增强
    system_prompt_addons: Dict[str, str] = field(default_factory=dict)


class TemplateSystem:
    """智能模板系统"""

    def __init__(self, templates_dir: Optional[str] = None):
        self.templates: Dict[str, IndustryTemplate] = {}
        self._industry_keywords: Dict[str, List[str]] = {
            "medical": ["医疗", "医院", "患者", "医生", "病理", "病案", "诊疗", "挂号", "处方", "医保", "HIS", "电子病历", "互联互通", "等保", "患者隐私", "医疗数据"],
            "finance": ["金融", "银行", "支付", "理财", "风控", "合规", "反洗钱", "KYC"],
            "education": ["教育", "学校", "学生", "教师", "课程", "考试", "学习", "教务"],
            "saas": ["SaaS", "B2B", "企业", "CRM", "ERP", "协同", "OA"]
        }

        # 加载内置模板
        self._load_builtin_templates()

        # 加载外部模板
        if templates_dir:
            self._load_external_templates(templates_dir)

    def _load_builtin_templates(self):
        """加载内置模板"""
        # 病理切片借阅平台模板
        self.register_template(IndustryTemplate(
            id="medical_slide_lending",
            name="病理切片借阅平台",
            industry="medical",
            description="医院病理科切片数字化借阅管理系统",
            keywords=["切片", "病理", "玻片", "借阅", "病理科"],
            workflow_type="full_workflow",
            sections=[
                "background",
                "compliance",
                "user_personas",
                "user_stories",
                "workflow",
                "data_model",
                "security",
                "integration",
                "appendix"
            ],
            mandatory_sections=["compliance", "security", "data_model"],
            compliance_required=True,
            compliance_categories=["data_security", "patient_privacy", "medical_records"],
            mandatory_checks=["等保三级", "患者隐私保护", "医疗数据安全", "电子病历管理规范", "互联互通标准化成熟度测评"],
            competitor_keywords=["切片管理", "病理系统", "数字化病理", "远程会诊"],
            analysis_focus=["数据安全", "合规性", "医院集成", "病理科工作流"],
            user_persona_templates=[
                {"role": "病理科医生", "goal": "高效管理切片借阅流程", "pain_points": "手工登记繁琐、追踪困难"},
                {"role": "患者", "goal": "便捷申请切片借阅", "pain_points": "流程不透明、等待时间长"},
                {"role": "管理人员", "goal": "合规监管和数据安全", "pain_points": "审计追踪、权限管理"}
            ],
            common_pain_points=[
                "手工登记效率低",
                "切片流转状态不透明",
                "合规审计困难",
                "多院区协同复杂"
            ],
            reference_docs=["病案复印经验", "医疗产品合规检查清单", "等保三级要求"],
            related_notes=["病案复印功能设计", "多院区数据同步方案"],
            system_prompt_addons={
                "requirement_agent": "注意：医疗产品需求必须包含数据安全、合规性、权限控制三个维度。用户故事必须覆盖患者、医生、管理员三类角色。",
                "compliance_checker": "重点检查：等保三级要求、患者隐私保护、医疗数据安全法、电子病历管理规范。",
                "prd_generator": "PRD必须包含：合规章节、数据安全章节、与HIS/LIS集成章节。技术方案需考虑医院内网部署环境。"
            }
        ))

        # 医疗管理后台模板
        self.register_template(IndustryTemplate(
            id="medical_admin_system",
            name="医疗管理后台",
            industry="medical",
            description="医院集团化管理后台系统",
            keywords=["管理后台", "医院管理", "集团化", "多院区", "HIS管理"],
            workflow_type="full_workflow",
            sections=[
                "background",
                "architecture",
                "user_personas",
                "modules",
                "data_security",
                "compliance",
                "integration",
                "deployment"
            ],
            mandatory_sections=["compliance", "data_security", "architecture"],
            compliance_required=True,
            compliance_categories=["data_security", "access_control", "audit"],
            mandatory_checks=["等保三级", "数据分级分类", "操作审计", "权限最小化原则"],
            competitor_keywords=["医院管理系统", "医疗信息化", "智慧医院"],
            analysis_focus=["系统稳定性", "数据安全", "多租户", "可扩展性"],
            user_persona_templates=[
                {"role": "系统管理员", "goal": "管理医院信息和用户权限", "pain_points": "权限复杂、操作繁琐"},
                {"role": "业务人员", "goal": "快速查询和处理业务数据", "pain_points": "数据分散、报表难生成"},
                {"role": "管理层", "goal": "掌握集团运营数据", "pain_points": "数据滞后、决策支持不足"}
            ],
            common_pain_points=[
                "多院区数据孤岛",
                "权限管理复杂",
                "报表统计困难",
                "系统响应慢"
            ],
            reference_docs=["医疗信息化管理系统群", "多院区数据同步方案"],
            system_prompt_addons={
                "requirement_agent": "注意：管理后台需求必须包含权限管理、操作审计、数据报表三个核心模块。考虑多院区、多角色的复杂权限场景。",
                "prd_generator": "PRD必须详细描述：RBAC权限模型、操作日志审计、数据报表导出、系统性能指标。"
            }
        ))

    def _load_external_templates(self, templates_dir: str):
        """从目录加载外部模板"""
        template_path = Path(templates_dir)
        if not template_path.exists():
            return

        for template_file in template_path.glob("*.json"):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    template = IndustryTemplate(**data)
                    self.register_template(template)
            except Exception as e:
                print(f"[TemplateSystem] Error loading {template_file}: {e}")

    def register_template(self, template: IndustryTemplate):
        """注册模板"""
        self.templates[template.id] = template

    def detect_industry(self, user_input: str) -> str:
        """检测行业类型"""
        user_input_lower = user_input.lower()

        scores = {}
        for industry, keywords in self._industry_keywords.items():
            score = sum(1 for kw in keywords if kw in user_input_lower)
            scores[industry] = score

        # 返回得分最高的行业
        if scores:
            best_match = max(scores, key=scores.get)
            if scores[best_match] > 0:
                return best_match

        return "general"

    def match_template(self, user_input: str) -> Optional[IndustryTemplate]:
        """匹配最适合的模板"""
        user_input_lower = user_input.lower()

        best_match = None
        best_score = 0

        for template in self.templates.values():
            score = sum(1 for kw in template.keywords if kw in user_input_lower)
            if score > best_score:
                best_score = score
                best_match = template

        return best_match if best_score > 0 else None

    def get_template(self, template_id: str) -> Optional[IndustryTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)

    def list_templates(self, industry: Optional[str] = None) -> List[IndustryTemplate]:
        """列出所有模板"""
        if industry:
            return [t for t in self.templates.values() if t.industry == industry]
        return list(self.templates.values())

    def apply_template_to_plan(self, template_id: str, base_plan: Dict) -> Dict:
        """将模板应用到任务计划"""
        template = self.templates.get(template_id)
        if not template:
            return base_plan

        # 根据模板调整计划
        plan = base_plan.copy()

        # 设置工作流类型
        plan["workflow_type"] = template.workflow_type

        # 添加合规检查步骤（如果需要）
        if template.compliance_required:
            steps = plan.get("plan", {}).get("steps", [])
            # 确保有合规检查步骤
            has_compliance = any(
                s.get("agent_name") == "ComplianceChecker" for s in steps
            )
            if not has_compliance:
                # 在 PRD 生成前插入合规检查
                for i, step in enumerate(steps):
                    if step.get("agent_name") == "PRDAgent":
                        steps.insert(i, {
                            "id": f"compliance_{i}",
                            "agent_name": "ComplianceChecker",
                            "description": "医疗合规检查",
                            "input_data": {
                                "mandatory_checks": template.mandatory_checks
                            }
                        })
                        break

        # 添加模板元数据
        plan["template"] = {
            "id": template.id,
            "name": template.name,
            "industry": template.industry,
            "compliance_required": template.compliance_required,
            "mandatory_checks": template.mandatory_checks
        }

        return plan

    def get_agent_prompt_addon(self, template_id: str, agent_name: str) -> str:
        """获取 Agent 的提示词增强"""
        template = self.templates.get(template_id)
        if not template:
            return ""
        return template.system_prompt_addons.get(agent_name, "")


# 全局模板系统实例
template_system = TemplateSystem()
```

**Step 2: 创建模板目录和 JSON 文件**

Create: `apps/api/app/agents/templates/__init__.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模板目录"""

import os

TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))
```

**Step 3: 修改 Task Planner 集成模板**

Modify: `apps/api/app/agents/agents/task_planner.py`

添加导入：
```python
from ..templates import template_system
```

修改 `execute` 方法：

```python
async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
    start_time = datetime.now()
    self._set_state(AgentState.RUNNING)

    try:
        user_input = input_data.get("user_input", "")
        intent_result = input_data.get("intent_result", {})

        step1 = self._create_step("detect_template", "检测行业模板")

        # 检测并匹配模板
        template = template_system.match_template(user_input)
        industry = template_system.detect_industry(user_input) if not template else template.industry

        template_info = {
            "template_id": template.id if template else None,
            "template_name": template.name if template else None,
            "industry": industry
        }

        self._complete_step(step1, f"模板: {template.name if template else '通用模板'}")

        step2 = self._create_step("select_workflow", "选择工作流")

        # 根据意图和模板选择工作流
        task_type = intent_result.get("task_type", "full_workflow")

        if template:
            workflow_type = template.workflow_type
        elif task_type == "prd_generation":
            workflow_type = "prd_only"
        elif task_type == "compliance_check":
            workflow_type = "compliance_only"
        else:
            workflow_type = "full_workflow"

        self._complete_step(step2, f"工作流: {workflow_type}")

        step3 = self._create_step("generate_plan", "生成执行计划")

        # 生成基础计划
        plan = self._generate_plan(
            workflow_type=workflow_type,
            user_input=user_input,
            intent_result=intent_result,
            template=template
        )

        self._complete_step(step3, f"计划: {len(plan['plan']['steps'])} 步骤")

        execution_time = (datetime.now() - start_time).total_seconds()
        self._set_state(AgentState.COMPLETED)

        # 将模板信息加入结果
        result_data = {
            "plan": plan,
            "template": template_info,
            "industry": industry
        }

        return AgentResult(
            success=True,
            output=f"Generated {workflow_type} plan with {len(plan['plan']['steps'])} steps",
            data=result_data,
            execution_time=execution_time
        )

    except Exception as e:
        self._set_state(AgentState.FAILED)
        return AgentResult(success=False, error=str(e))


def _generate_plan(
    self,
    workflow_type: str,
    user_input: str,
    intent_result: Dict,
    template: Optional[Any]
) -> Dict:
    """生成执行计划"""

    base_plan = self.WORKFLOW_TEMPLATES.get(workflow_type, self.WORKFLOW_TEMPLATES["full_workflow"]).copy()

    # 添加模板特定的输入数据
    if template:
        for step in base_plan["steps"]:
            agent_name = step["agent_name"]

            if agent_name == "RequirementAgent":
                step["input_data"]["user_persona_templates"] = template.user_persona_templates
                step["input_data"]["common_pain_points"] = template.common_pain_points
                step["input_data"]["system_prompt_addon"] = template.system_prompt_addons.get("requirement_agent", "")

            elif agent_name == "CompetitorAnalyst":
                step["input_data"]["competitor_keywords"] = template.competitor_keywords
                step["input_data"]["analysis_focus"] = template.analysis_focus

            elif agent_name == "ComplianceChecker":
                step["input_data"]["mandatory_checks"] = template.mandatory_checks
                step["input_data"]["compliance_categories"] = template.compliance_categories
                step["input_data"]["system_prompt_addon"] = template.system_prompt_addons.get("compliance_checker", "")

            elif agent_name == "PRDAgent":
                step["input_data"]["sections"] = template.sections
                step["input_data"]["mandatory_sections"] = template.mandatory_sections
                step["input_data"]["system_prompt_addon"] = template.system_prompt_addons.get("prd_generator", "")

    return base_plan
```

**Step 4: 创建测试**

Create: `tests/test_templates.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模板系统测试"""

import pytest
from app.agents.templates import TemplateSystem, IndustryTemplate


def test_detect_medical_industry():
    """测试医疗行业检测"""
    ts = TemplateSystem()

    # 医疗相关输入
    assert ts.detect_industry("病理切片借阅平台") == "medical"
    assert ts.detect_industry("医院挂号系统") == "medical"
    assert ts.detect_industry("患者管理系统") == "medical"

    # 非医疗输入
    assert ts.detect_industry("电商购物车") != "medical"


def test_match_slide_lending_template():
    """测试病理切片模板匹配"""
    ts = TemplateSystem()

    template = ts.match_template("我要做病理切片借阅平台")
    assert template is not None
    assert template.id == "medical_slide_lending"
    assert template.industry == "medical"
    assert template.compliance_required is True
    assert "等保三级" in template.mandatory_checks


def test_template_prompt_addons():
    """测试模板提示词增强"""
    ts = TemplateSystem()

    addon = ts.get_agent_prompt_addon("medical_slide_lending", "compliance_checker")
    assert "等保三级" in addon
    assert "患者隐私保护" in addon


def test_apply_template_to_plan():
    """测试模板应用到计划"""
    ts = TemplateSystem()

    base_plan = {
        "plan": {
            "workflow_name": "Full Workflow",
            "steps": [
                {"id": "1", "agent_name": "IntentClassifier"},
                {"id": "2", "agent_name": "PRDAgent"}
            ]
        }
    }

    result = ts.apply_template_to_plan("medical_slide_lending", base_plan)

    assert "template" in result
    assert result["template"]["compliance_required"] is True
    assert "workflow_type" in result


if __name__ == "__main__":
    test_detect_medical_industry()
    test_match_slide_lending_template()
    test_template_prompt_addons()
    test_apply_template_to_plan()
    print("All template tests passed!")
```

**Step 5: 运行测试**

Run: `cd apps/api && python -m pytest tests/test_templates.py -v -s`
Expected: 测试通过

**Step 6: Commit**

```bash
git add apps/api/app/agents/templates.py apps/api/app/agents/templates/
git add apps/api/app/agents/agents/task_planner.py
git add tests/test_templates.py
git commit -m "feat: add medical industry smart template system

- TemplateSystem with industry detection and keyword matching
- Built-in templates: medical_slide_lending, medical_admin_system
- Automatic compliance requirement detection
- Agent prompt enhancement based on templates
- Integration with TaskPlanner for workflow customization"
```

---

## Task 5: 故障恢复（断点续传）

**Files:**
- Create: `apps/api/app/agents/persistence.py`
- Create: `apps/api/app/agents/recovery.py`
- Modify: `apps/api/app/agents/strategy.py` - 集成持久化

**Step 1: 创建工作流持久化层**

```python
# apps/api/app/agents/persistence.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import asyncio
import pickle
import base64


class WorkflowPersistence:
    """工作流持久化 - 保存和恢复工作流状态"""

    def __init__(self, db_path: str = "data/workflows.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    user_input TEXT NOT NULL,
                    status TEXT NOT NULL,
                    intent_result TEXT,
                    plan TEXT,
                    results TEXT,
                    current_step TEXT,
                    checkpoints TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    content TEXT,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                )
            """)

            conn.commit()

    async def save_workflow(self, workflow_id: str, data: Dict[str, Any]):
        """保存工作流状态"""
        await asyncio.to_thread(self._save_workflow_sync, workflow_id, data)

    def _save_workflow_sync(self, workflow_id: str, data: Dict[str, Any]):
        """同步保存工作流（在线程中执行）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflows
                (workflow_id, user_input, status, intent_result, plan, results,
                 current_step, checkpoints, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                data.get("user_input", ""),
                data.get("status", "pending"),
                json.dumps(data.get("intent_result"), ensure_ascii=False),
                json.dumps(data.get("plan"), ensure_ascii=False),
                json.dumps(data.get("results", []), ensure_ascii=False),
                data.get("current_step", ""),
                json.dumps(data.get("checkpoints", []), ensure_ascii=False),
                datetime.now().isoformat()
            ))
            conn.commit()

    async def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """加载工作流状态"""
        return await asyncio.to_thread(self._load_workflow_sync, workflow_id)

    def _load_workflow_sync(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """同步加载工作流"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM workflows WHERE workflow_id = ?",
                (workflow_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "workflow_id": row["workflow_id"],
                "user_input": row["user_input"],
                "status": row["status"],
                "intent_result": json.loads(row["intent_result"]) if row["intent_result"] else None,
                "plan": json.loads(row["plan"]) if row["plan"] else None,
                "results": json.loads(row["results"]) if row["results"] else [],
                "current_step": row["current_step"],
                "checkpoints": json.loads(row["checkpoints"]) if row["checkpoints"] else [],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    async def save_checkpoint(self, checkpoint_id: str, workflow_id: str,
                             step_id: str, content: Dict, result: Dict = None):
        """保存检查点状态"""
        await asyncio.to_thread(self._save_checkpoint_sync,
                               checkpoint_id, workflow_id, step_id, content, result)

    def _save_checkpoint_sync(self, checkpoint_id: str, workflow_id: str,
                             step_id: str, content: Dict, result: Dict = None):
        """同步保存检查点"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO checkpoints
                (checkpoint_id, workflow_id, step_id, status, content, result)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                checkpoint_id,
                workflow_id,
                step_id,
                "completed",
                json.dumps(content, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False) if result else None
            ))
            conn.commit()

    async def list_incomplete_workflows(self, limit: int = 10) -> list:
        """列出未完成的工作流"""
        return await asyncio.to_thread(self._list_incomplete_sync, limit)

    def _list_incomplete_sync(self, limit: int) -> list:
        """同步列出未完成工作流"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT workflow_id, user_input, status, current_step, updated_at
                FROM workflows
                WHERE status NOT IN ('completed', 'failed')
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    async def mark_completed(self, workflow_id: str):
        """标记工作流为完成"""
        await asyncio.to_thread(self._mark_completed_sync, workflow_id)

    def _mark_completed_sync(self, workflow_id: str):
        """同步标记完成"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE workflows
                SET status = 'completed', completed_at = ?
                WHERE workflow_id = ?
            """, (datetime.now().isoformat(), workflow_id))
            conn.commit()

    async def delete_workflow(self, workflow_id: str):
        """删除工作流"""
        await asyncio.to_thread(self._delete_workflow_sync, workflow_id)

    def _delete_workflow_sync(self, workflow_id: str):
        """同步删除工作流"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM checkpoints WHERE workflow_id = ?", (workflow_id,))
            conn.execute("DELETE FROM workflows WHERE workflow_id = ?", (workflow_id,))
            conn.commit()


# 全局持久化实例
workflow_persistence = WorkflowPersistence()
```

**Step 2: 创建故障恢复管理器**

```python
# apps/api/app/agents/recovery.py
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, Any, Optional, List
from datetime import datetime
from .persistence import workflow_persistence
from .progress import ProgressTracker


class WorkflowRecovery:
    """工作流故障恢复 - 断点续传"""

    def __init__(self):
        self.persistence = workflow_persistence

    async def save_checkpoint(
        self,
        workflow_id: str,
        step_id: str,
        step_data: Dict[str, Any]
    ):
        """
        保存执行检查点

        每完成一个步骤后调用，保存当前状态
        """
        checkpoint_data = {
            "step_id": step_id,
            "step_data": step_data,
            "saved_at": datetime.now().isoformat()
        }

        await self.persistence.save_checkpoint(
            checkpoint_id=f"{workflow_id}_{step_id}",
            workflow_id=workflow_id,
            step_id=step_id,
            content=checkpoint_data
        )

        print(f"[Recovery] Checkpoint saved: {workflow_id}/{step_id}")

    async def can_resume(self, workflow_id: str) -> bool:
        """检查工作流是否可以恢复"""
        workflow = await self.persistence.load_workflow(workflow_id)
        if not workflow:
            return False

        return workflow["status"] in ["running", "paused", "failed"]

    async def get_resume_point(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取恢复点信息

        Returns:
            {
                "workflow_id": str,
                "user_input": str,
                "last_completed_step": str,
                "next_step": str,
                "progress": int,
                "intent_result": dict,
                "plan": dict,
                "results": list
            }
        """
        workflow = await self.persistence.load_workflow(workflow_id)
        if not workflow:
            return None

        # 确定下一步
        current_step = workflow.get("current_step", "")
        plan = workflow.get("plan", {})
        steps = plan.get("plan", {}).get("steps", [])

        next_step = None
        for i, step in enumerate(steps):
            if step["id"] == current_step and i + 1 < len(steps):
                next_step = steps[i + 1]
                break

        # 计算进度
        completed_steps = len(workflow.get("results", []))
        total_steps = len(steps)
        progress = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0

        return {
            "workflow_id": workflow_id,
            "user_input": workflow["user_input"],
            "status": workflow["status"],
            "last_completed_step": current_step,
            "next_step": next_step,
            "progress": progress,
            "intent_result": workflow.get("intent_result"),
            "plan": workflow.get("plan"),
            "results": workflow.get("results", [])
        }

    async def resume_workflow(
        self,
        workflow_id: str,
        strategy_layer
    ):
        """
        恢复工作流执行

        从断点继续执行，跳过已完成的步骤
        """
        if not await self.can_resume(workflow_id):
            raise ValueError(f"Workflow {workflow_id} cannot be resumed")

        resume_point = await self.get_resume_point(workflow_id)
        if not resume_point:
            raise ValueError(f"Cannot determine resume point for {workflow_id}")

        print(f"[Recovery] Resuming workflow {workflow_id} from step: {resume_point['last_completed_step']}")

        # 恢复进度追踪器状态
        # 创建新的工作流上下文，但复用之前的结果
        from .strategy import WorkflowContext
        from uuid import UUID

        workflow = WorkflowContext(
            workflow_id=UUID(workflow_id),
            user_input=resume_point["user_input"]
        )
        workflow.intent_result = resume_point["intent_result"]
        workflow.plan = resume_point["plan"]
        workflow.results = resume_point["results"]
        workflow.status = "running"

        strategy_layer._workflows[workflow.workflow_id] = workflow

        return workflow

    async def list_recoverable_workflows(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """列出可恢复的工作流"""
        workflows = await self.persistence.list_incomplete_workflows(limit)

        result = []
        for wf in workflows:
            resume_point = await self.get_resume_point(wf["workflow_id"])
            if resume_point:
                result.append({
                    "workflow_id": wf["workflow_id"],
                    "user_input": wf["user_input"][:50] + "..." if len(wf["user_input"]) > 50 else wf["user_input"],
                    "status": wf["status"],
                    "progress": resume_point["progress"],
                    "last_updated": wf["updated_at"],
                    "next_step": resume_point["next_step"]["name"] if resume_point["next_step"] else "完成"
                })

        return result

    async def cleanup_old_workflows(self, days: int = 7):
        """清理旧的工作流记录"""
        # 这里可以实现定期清理逻辑
        pass


# 全局恢复管理器
workflow_recovery = WorkflowRecovery()
```

**Step 3: 在 Strategy Layer 中集成持久化**

Modify: `apps/api/app/agents/strategy.py`

添加导入：
```python
from .persistence import workflow_persistence
from .recovery import workflow_recovery
```

在 `_process_sync_with_checkpoints` 方法中添加持久化逻辑：

```python
async def _process_sync_with_checkpoints(
    self,
    user_input: str,
    context: Optional[Dict]
) -> WorkflowContext:
    """带检查点和持久化的处理流程"""
    workflow = WorkflowContext(
        workflow_id=uuid4(),
        user_input=user_input
    )
    self._workflows[workflow.workflow_id] = workflow

    # 初始化进度追踪器和检查点
    progress_tracker = ProgressTracker(str(workflow.workflow_id))
    event_emitter = EventEmitter(str(workflow.workflow_id))
    checkpoint = CheckpointWrapper(
        workflow_id=str(workflow.workflow_id),
        event_emitter=event_emitter
    )

    # 注册进度回调
    async def on_progress(event_type: str, data: dict):
        await websocket_manager.broadcast_to_workflow(
            str(workflow.workflow_id),
            {"type": event_type, "data": data}
        )
    progress_tracker.register_callback(on_progress)

    progress_tracker.initialize_workflow("full_workflow", user_input)

    try:
        # 步骤1: 意图识别
        workflow.status = "intent_classification"
        progress_tracker.start_step("intent", "正在分析用户意图...")
        intent_result = await self.intent_classifier.execute({"user_input": user_input})

        # 检查点
        checkpoint_result = await checkpoint.check(...)
        workflow.intent_result = checkpoint_result["content"]
        progress_tracker.complete_step("intent", ...)

        # 保存检查点
        await workflow_recovery.save_checkpoint(
            str(workflow.workflow_id),
            "intent",
            {"result": workflow.intent_result}
        )
        await self._persist_workflow_state(workflow, "intent")

        # 步骤2: 任务规划
        workflow.status = "planning"
        progress_tracker.start_step("plan", "正在规划...")
        plan_result = await self.task_planner.execute(...)
        checkpoint_result = await checkpoint.check(...)
        workflow.plan = plan_result.data
        progress_tracker.complete_step("plan", ...)

        await workflow_recovery.save_checkpoint(
            str(workflow.workflow_id),
            "plan",
            {"result": workflow.plan}
        )
        await self._persist_workflow_state(workflow, "plan")

        # 执行后续步骤...
        await self._execute_plan_with_recovery(workflow, progress_tracker, checkpoint)

        # 完成
        workflow.status = "completed"
        workflow.completed_at = datetime.now()
        progress_tracker.complete_workflow()
        await workflow_persistence.mark_completed(str(workflow.workflow_id))

    except Exception as e:
        workflow.status = "failed"
        # 即使失败也保存状态，方便恢复
        await self._persist_workflow_state(workflow, progress_tracker.get_current_step().id if progress_tracker.get_current_step() else "unknown")
        workflow.results.append({"step": workflow.status, "error": str(e)})

    return workflow


async def _persist_workflow_state(self, workflow: WorkflowContext, current_step: str):
    """持久化工作流状态"""
    await workflow_persistence.save_workflow(
        str(workflow.workflow_id),
        {
            "user_input": workflow.user_input,
            "status": workflow.status,
            "intent_result": workflow.intent_result,
            "plan": workflow.plan,
            "results": workflow.results,
            "current_step": current_step
        }
    )


async def resume_workflow(self, workflow_id: str) -> WorkflowContext:
    """恢复工作流"""
    if not await workflow_recovery.can_resume(workflow_id):
        raise ValueError(f"Workflow {workflow_id} cannot be resumed")

    workflow = await workflow_recovery.resume_workflow(workflow_id, self)

    # 继续执行剩余步骤
    progress_tracker = ProgressTracker(workflow_id)
    checkpoint = CheckpointWrapper(workflow_id)

    await self._execute_plan_with_recovery(workflow, progress_tracker, checkpoint)

    return workflow
```

**Step 4: 创建测试**

Create: `tests/test_recovery.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""故障恢复测试"""

import pytest
import asyncio
import tempfile
import os
from app.agents.persistence import WorkflowPersistence
from app.agents.recovery import WorkflowRecovery


@pytest.mark.asyncio
async def test_persistence_save_load():
    """测试工作流持久化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = WorkflowPersistence(db_path)

        # 保存工作流
        workflow_id = "test-wf-123"
        await persistence.save_workflow(workflow_id, {
            "user_input": "测试产品",
            "status": "running",
            "intent_result": {"task_type": "prd_generation"},
            "current_step": "intent"
        })

        # 加载工作流
        loaded = await persistence.load_workflow(workflow_id)
        assert loaded is not None
        assert loaded["user_input"] == "测试产品"
        assert loaded["status"] == "running"
        assert loaded["intent_result"]["task_type"] == "prd_generation"


@pytest.mark.asyncio
async def test_recovery_can_resume():
    """测试恢复判断"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        persistence = WorkflowPersistence(db_path)

        workflow_id = "test-wf-456"
        await persistence.save_workflow(workflow_id, {
            "user_input": "测试",
            "status": "running",
            "current_step": "plan"
        })

        recovery = WorkflowRecovery()
        recovery.persistence = persistence

        assert await recovery.can_resume(workflow_id) is True

        # 标记完成后不能恢复
        await persistence.mark_completed(workflow_id)
        assert await recovery.can_resume(workflow_id) is False


if __name__ == "__main__":
    asyncio.run(test_persistence_save_load())
    asyncio.run(test_recovery_can_resume())
    print("All recovery tests passed!")
```

**Step 5: 运行测试**

Run: `cd apps/api && python -m pytest tests/test_recovery.py -v -s`
Expected: 测试通过

**Step 6: Commit**

```bash
git add apps/api/app/agents/persistence.py apps/api/app/agents/recovery.py
git add apps/api/app/agents/strategy.py  # 修改部分
git add tests/test_recovery.py
git commit -m "feat: add fault tolerance with checkpoint/resume

- WorkflowPersistence with SQLite storage for state management
- WorkflowRecovery for resuming failed workflows from checkpoints
- Automatic checkpoint saving after each step completion
- List recoverable workflows API for UI display
- Recovery point calculation with progress tracking"
```

---

## Task 6: 前端演示页面

**Files:**
- Create: `apps/web/static/progress-demo.html`

**Step 1: 创建实时进度展示页面**

```html
<!-- apps/web/static/progress-demo.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jarvis PM Agent - 实时进度</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f23;
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }

        .container { max-width: 800px; margin: 0 auto; }

        h1 {
            text-align: center;
            margin-bottom: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* 输入区域 */
        .input-section {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }

        textarea {
            width: 100%;
            min-height: 100px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 12px;
            color: #fff;
            font-size: 14px;
            resize: vertical;
        }

        textarea::placeholder { color: rgba(255,255,255,0.4); }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: #fff;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
            transition: transform 0.2s;
        }

        .btn:hover { transform: translateY(-2px); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* 进度条 */
        .progress-section {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            display: none;
        }

        .progress-section.active { display: block; }

        .overall-progress {
            margin-bottom: 20px;
        }

        .progress-bar-bg {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 4px;
            transition: width 0.3s ease;
            width: 0%;
        }

        .progress-text {
            text-align: center;
            margin-top: 8px;
            font-size: 14px;
            color: rgba(255,255,255,0.7);
        }

        /* 步骤列表 */
        .steps-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .step-item {
            display: flex;
            align-items: center;
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05);
            transition: all 0.3s;
        }

        .step-item.running {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.1);
        }

        .step-item.completed {
            opacity: 0.7;
        }

        .step-item.waiting {
            border-color: #f59e0b;
            background: rgba(245, 158, 11, 0.1);
        }

        .step-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            font-size: 14px;
        }

        .step-item.pending .step-icon {
            background: rgba(255,255,255,0.1);
            color: rgba(255,255,255,0.5);
        }

        .step-item.running .step-icon {
            background: #667eea;
            animation: pulse 2s infinite;
        }

        .step-item.completed .step-icon {
            background: #10b981;
        }

        .step-item.waiting .step-icon {
            background: #f59e0b;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .step-content {
            flex: 1;
        }

        .step-name {
            font-weight: 500;
            margin-bottom: 4px;
        }

        .step-detail {
            font-size: 12px;
            color: rgba(255,255,255,0.5);
        }

        .step-duration {
            font-size: 12px;
            color: rgba(255,255,255,0.4);
        }

        /* 检查点对话框 */
        .checkpoint-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .checkpoint-modal.active { display: flex; }

        .checkpoint-content {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .checkpoint-title {
            font-size: 18px;
            margin-bottom: 12px;
        }

        .checkpoint-description {
            color: rgba(255,255,255,0.7);
            margin-bottom: 20px;
        }

        .checkpoint-actions {
            display: flex;
            gap: 10px;
        }

        .btn-secondary {
            background: rgba(255,255,255,0.1);
        }

        /* 结果展示 */
        .result-section {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            display: none;
        }

        .result-section.active { display: block; }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-bottom: 16px;
        }

        .status-success { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .status-error { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

        pre {
            background: rgba(0,0,0,0.3);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Jarvis PM Agent</h1>

        <!-- 输入区域 -->
        <div class="input-section">
            <textarea id="userInput" placeholder="描述你的产品需求，例如：我要做病理切片借阅平台，支持患者在线申请、医生审核、物流跟踪..."></textarea>
            <button class="btn" id="startBtn" onclick="startWorkflow()">开始生成 PRD</button>
        </div>

        <!-- 进度区域 -->
        <div class="progress-section" id="progressSection">
            <div class="overall-progress">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="overallProgressBar"></div>
                </div>
                <div class="progress-text" id="overallProgressText">准备开始...</div>
            </div>

            <div class="steps-list" id="stepsList">
                <!-- 步骤项将动态生成 -->
            </div>
        </div>

        <!-- 结果区域 -->
        <div class="result-section" id="resultSection">
            <div id="statusBadge" class="status-badge"></div>
            <pre id="resultContent"></pre>
        </div>
    </div>

    <!-- 检查点对话框 -->
    <div class="checkpoint-modal" id="checkpointModal">
        <div class="checkpoint-content">
            <div class="checkpoint-title" id="checkpointTitle">确认</div>
            <div class="checkpoint-description" id="checkpointDesc">请确认</div>
            <div id="checkpointContent"></div>
            <div class="checkpoint-actions">
                <button class="btn" onclick="resumeCheckpoint()">✓ 确认继续</button>
                <button class="btn btn-secondary" onclick="modifyCheckpoint()">✎ 修改</button>
                <button class="btn btn-secondary" onclick="skipCheckpoint()">⊘ 跳过</button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'http://localhost:8000';
        let ws = null;
        let currentWorkflowId = null;
        let currentCheckpointId = null;
        let steps = [];

        // 步骤配置
        const stepConfig = {
            intent: { name: '意图识别', icon: '🎯' },
            plan: { name: '任务规划', icon: '📋' },
            requirement: { name: '需求分析', icon: '📊' },
            competitor: { name: '竞品分析', icon: '🔍' },
            compliance: { name: '合规检查', icon: '🔒' },
            prd: { name: 'PRD 生成', icon: '📝' },
            review: { name: '评审准备', icon: '✅' }
        };

        async function startWorkflow() {
            const userInput = document.getElementById('userInput').value.trim();
            if (!userInput) {
                alert('请输入产品需求');
                return;
            }

            // 重置 UI
            document.getElementById('progressSection').classList.add('active');
            document.getElementById('resultSection').classList.remove('active');
            document.getElementById('startBtn').disabled = true;
            document.getElementById('overallProgressBar').style.width = '0%';
            document.getElementById('overallProgressText').textContent = '准备开始...';

            // 生成工作流 ID
            currentWorkflowId = 'wf_' + Date.now();

            // 初始化步骤列表
            initStepsList();

            // 连接 WebSocket
            connectWebSocket();

            // 发送请求
            try {
                const response = await fetch(`${API_BASE}/api/v1/ai/workflow`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_input: userInput,
                        workflow_id: currentWorkflowId,
                        enable_checkpoints: true
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to start workflow');
                }

            } catch (error) {
                console.error('Error:', error);
                showError('启动失败: ' + error.message);
            }
        }

        function initStepsList() {
            const container = document.getElementById('stepsList');
            container.innerHTML = '';
            steps = [];

            for (const [stepId, config] of Object.entries(stepConfig)) {
                const stepEl = document.createElement('div');
                stepEl.className = 'step-item pending';
                stepEl.id = `step-${stepId}`;
                stepEl.innerHTML = `
                    <div class="step-icon">${config.icon}</div>
                    <div class="step-content">
                        <div class="step-name">${config.name}</div>
                        <div class="step-detail" id="detail-${stepId}">等待中...</div>
                    </div>
                    <div class="step-duration" id="duration-${stepId}"></div>
                `;
                container.appendChild(stepEl);
                steps.push(stepId);
            }
        }

        function connectWebSocket() {
            if (ws) {
                ws.close();
            }

            ws = new WebSocket(`ws://localhost:8000/ws/workflow/${currentWorkflowId}`);

            ws.onopen = () => {
                console.log('WebSocket connected');
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                console.log('WebSocket closed');
            };
        }

        function handleWebSocketMessage(message) {
            console.log('Received:', message);

            switch (message.type) {
                case 'workflow_started':
                    document.getElementById('overallProgressText').textContent = '工作流已启动';
                    break;

                case 'step_started':
                    updateStepStatus(message.data.step_id, 'running', message.data.detail);
                    break;

                case 'step_progress':
                    updateProgress(message.data.overall_progress, message.data.detail);
                    break;

                case 'step_completed':
                    updateStepStatus(message.data.step_id, 'completed', message.data.result_summary);
                    updateStepDuration(message.data.step_id, message.data.duration_ms);
                    break;

                case 'step_failed':
                    updateStepStatus(message.data.step_id, 'error', message.data.error);
                    showError(message.data.error);
                    break;

                case 'step_waiting':
                    updateStepStatus(message.data.step_id, 'waiting', message.data.checkpoint_title);
                    break;

                case 'checkpoint':
                    showCheckpoint(message.data);
                    break;

                case 'workflow_completed':
                    showResult('success', message.data);
                    break;

                case 'error':
                    showError(message.data.error);
                    break;
            }
        }

        function updateStepStatus(stepId, status, detail) {
            const stepEl = document.getElementById(`step-${stepId}`);
            if (!stepEl) return;

            stepEl.className = `step-item ${status}`;

            const iconMap = {
                pending: stepConfig[stepId]?.icon || '○',
                running: '◌',
                completed: '✓',
                waiting: '!',
                error: '✗'
            };

            stepEl.querySelector('.step-icon').textContent = iconMap[status] || iconMap.pending;

            if (detail) {
                document.getElementById(`detail-${stepId}`).textContent = detail;
            }
        }

        function updateStepDuration(stepId, durationMs) {
            const durationEl = document.getElementById(`duration-${stepId}`);
            if (durationEl && durationMs) {
                const seconds = (durationMs / 1000).toFixed(1);
                durationEl.textContent = `${seconds}s`;
            }
        }

        function updateProgress(progress, detail) {
            document.getElementById('overallProgressBar').style.width = `${progress}%`;
            if (detail) {
                document.getElementById('overallProgressText').textContent = detail;
            } else {
                document.getElementById('overallProgressText').textContent = `${progress}% 完成`;
            }
        }

        function showCheckpoint(data) {
            currentCheckpointId = data.checkpoint_id;
            document.getElementById('checkpointTitle').textContent = data.title;
            document.getElementById('checkpointDesc').textContent = data.description;

            // 显示检查点内容
            const contentEl = document.getElementById('checkpointContent');
            contentEl.innerHTML = `<pre>${JSON.stringify(data.content, null, 2)}</pre>`;

            document.getElementById('checkpointModal').classList.add('active');
        }

        function hideCheckpoint() {
            document.getElementById('checkpointModal').classList.remove('active');
        }

        function resumeCheckpoint() {
            if (ws && currentCheckpointId) {
                ws.send(JSON.stringify({
                    action: 'resume',
                    checkpoint_id: currentCheckpointId
                }));
            }
            hideCheckpoint();
        }

        function modifyCheckpoint() {
            // 简化实现：通过 prompt 获取修改
            const modifications = prompt('请输入修改内容（JSON格式）：', '{}');
            if (modifications && ws && currentCheckpointId) {
                try {
                    ws.send(JSON.stringify({
                        action: 'modify',
                        checkpoint_id: currentCheckpointId,
                        modifications: JSON.parse(modifications)
                    }));
                } catch (e) {
                    alert('JSON格式错误');
                    return;
                }
            }
            hideCheckpoint();
        }

        function skipCheckpoint() {
            if (ws && currentCheckpointId) {
                ws.send(JSON.stringify({
                    action: 'skip',
                    checkpoint_id: currentCheckpointId
                }));
            }
            hideCheckpoint();
        }

        function showResult(status, data) {
            document.getElementById('progressSection').classList.remove('active');
            document.getElementById('resultSection').classList.add('active');
            document.getElementById('startBtn').disabled = false;

            const badge = document.getElementById('statusBadge');
            badge.className = `status-badge status-${status}`;
            badge.textContent = status === 'success' ? '✓ 生成成功' : '✗ 生成失败';

            document.getElementById('resultContent').textContent = JSON.stringify(data, null, 2);

            // 关闭 WebSocket
            if (ws) {
                ws.close();
                ws = null;
            }
        }

        function showError(error) {
            document.getElementById('startBtn').disabled = false;
            document.getElementById('overallProgressText').textContent = '执行出错';

            const badge = document.getElementById('statusBadge');
            badge.className = 'status-badge status-error';
            badge.textContent = '✗ 执行出错';

            document.getElementById('resultSection').classList.add('active');
            document.getElementById('resultContent').textContent = error;

            if (ws) {
                ws.close();
                ws = null;
            }
        }
    </script>
</body>
</html>
```

**Step 2: 添加 API 路由**

Modify: `apps/api/app/api/v1/endpoints/ai.py`

添加 WebSocket 工作流启动端点：

```python
from fastapi import APIRouter, WebSocket, BackgroundTasks
from app.agents.strategy import get_strategy_layer
from app.websocket import websocket_manager

router = APIRouter()

@router.post("/workflow")
async def start_workflow(request: dict, background_tasks: BackgroundTasks):
    """启动工作流（后台执行）"""
    user_input = request.get("user_input")
    workflow_id = request.get("workflow_id")

    strategy = get_strategy_layer()

    # 在后台执行任务
    background_tasks.add_task(
        strategy.process,
        user_input=user_input,
        context={"workflow_id": workflow_id}
    )

    return {"workflow_id": workflow_id, "status": "started"}


@router.get("/workflows/recoverable")
async def list_recoverable_workflows():
    """列出可恢复的工作流"""
    from app.agents.recovery import workflow_recovery
    workflows = await workflow_recovery.list_recoverable_workflows()
    return {"workflows": workflows}


@router.post("/workflows/{workflow_id}/resume")
async def resume_workflow(workflow_id: str):
    """恢复工作流"""
    from app.agents.strategy import get_strategy_layer
    strategy = get_strategy_layer()

    workflow = await strategy.resume_workflow(workflow_id)
    return {"workflow_id": str(workflow.workflow_id), "status": workflow.status}
```

**Step 3: Commit**

```bash
git add apps/web/static/progress-demo.html
git add apps/api/app/api/v1/endpoints/ai.py
git commit -m "feat: add real-time progress visualization frontend

- Interactive progress tracking with WebSocket integration
- Step-by-step visualization with status indicators
- Checkpoint modal for human-AI collaboration
- API endpoints for workflow control and recovery
- Responsive dark-themed UI"
```

---

## Task 7: 集成测试

**Files:**
- Create: `tests/test_integration_optimized.py`

**Step 1: 创建集成测试**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化功能集成测试

测试所有优化功能的协同工作
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
sys.path.insert(0, 'apps/api')

import asyncio
import tempfile
import pytest


async def test_full_optimized_workflow():
    """测试完整的优化工作流"""
    print("=" * 60)
    print("优化功能集成测试")
    print("=" * 60)
    print()

    # 1. 测试模板系统
    print("Test 1: 模板系统")
    from app.agents.templates import template_system

    template = template_system.match_template("病理切片借阅平台")
    assert template is not None, "应该匹配医疗模板"
    assert template.id == "medical_slide_lending"
    print(f"  ✓ 模板匹配: {template.name}")
    print(f"  ✓ 合规要求: {template.compliance_required}")
    print(f"  ✓ 强制检查项: {len(template.mandatory_checks)} 项")
    print()

    # 2. 测试进度追踪
    print("Test 2: 进度追踪")
    from app.agents.progress import ProgressTracker

    tracker = ProgressTracker("test-wf")
    events = []

    async def on_event(event_type, data):
        events.append(event_type)

    tracker.register_callback(on_event)
    tracker.initialize_workflow("full_workflow", "测试产品")
    tracker.start_step("intent", "分析中...")
    tracker.update_step_progress("intent", 50)
    tracker.complete_step("intent", "完成")

    assert len(events) >= 4, "应该收到多个事件"
    print(f"  ✓ 收到事件: {events}")
    print(f"  ✓ 总体进度: {tracker.progress.overall_progress}%")
    print()

    # 3. 测试检查点
    print("Test 3: 检查点机制")
    from app.agents.checkpoints import CheckpointController

    controller = CheckpointController()

    checkpoint = controller.create_checkpoint(
        workflow_id="test-wf",
        checkpoint_id="after_intent",
        step_id="intent",
        content={"task_type": "test"}
    )

    assert checkpoint.status == "pending"
    print(f"  ✓ 检查点创建: {checkpoint.id}")

    # 模拟用户继续
    await controller.resume("test-wf", checkpoint.id)
    assert checkpoint.status == "resolved"
    print(f"  ✓ 检查点已解决")
    print()

    # 4. 测试持久化
    print("Test 4: 持久化")
    with tempfile.TemporaryDirectory() as tmpdir:
        from app.agents.persistence import WorkflowPersistence

        db_path = os.path.join(tmpdir, "test.db")
        persistence = WorkflowPersistence(db_path)

        await persistence.save_workflow("test-wf-1", {
            "user_input": "测试",
            "status": "running",
            "intent_result": {"test": True},
            "current_step": "intent"
        })

        loaded = await persistence.load_workflow("test-wf-1")
        assert loaded is not None
        assert loaded["status"] == "running"
        print(f"  ✓ 工作流保存和加载成功")
    print()

    # 5. 测试恢复
    print("Test 5: 故障恢复")
    from app.agents.recovery import WorkflowRecovery

    recovery = WorkflowRecovery()
    # recovery.persistence 会在实际使用时设置
    print(f"  ✓ 恢复管理器创建成功")
    print()

    print("=" * 60)
    print("✅ 所有集成测试通过！")
    print("=" * 60)

    return True


async def test_medical_template_application():
    """测试医疗模板应用"""
    print()
    print("=" * 60)
    print("医疗模板应用测试")
    print("=" * 60)
    print()

    from app.agents.templates import template_system
    from app.agents.agents.task_planner import TaskPlanner

    # 测试输入
    test_inputs = [
        "我要做病理切片借阅平台",
        "医院管理后台系统",
        "电商购物车功能",
    ]

    for user_input in test_inputs:
        print(f"输入: {user_input}")

        # 检测模板
        template = template_system.match_template(user_input)
        industry = template_system.detect_industry(user_input)

        if template:
            print(f"  ✓ 匹配模板: {template.name}")
            print(f"  ✓ 行业: {template.industry}")
            print(f"  ✓ 合规检查: {'需要' if template.compliance_required else '不需要'}")
        else:
            print(f"  ✓ 使用通用模板")
            print(f"  ✓ 行业: {industry}")

        print()

    return True


async def main():
    print("开始优化功能集成测试...\n")

    try:
        await test_full_optimized_workflow()
        await test_medical_template_application()

        print()
        print("🎉 所有测试通过！优化功能已就绪。")
        print()
        print("快速开始:")
        print("1. 启动后端: cd apps/api && python start.py")
        print("2. 打开前端: http://localhost:3000/progress-demo.html")
        print("3. 输入产品需求，观察实时进度")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
```

**Step 2: 运行集成测试**

Run: `cd apps/api && python -m pytest tests/test_integration_optimized.py -v -s`
Expected: 所有测试通过

**Step 3: Commit**

```bash
git add tests/test_integration_optimized.py
git commit -m "test: add integration tests for all optimization features

- Full workflow test covering templates, progress, checkpoints, persistence
- Medical template application test with multiple inputs
- End-to-end validation of optimized system"
```

---

## 总结与下一步

### 完整任务清单

#### Phase 1（立即实施）- 7个任务，42个步骤

| 任务 | 内容 | 预计时间 |
|:---|:---|:---|
| Task 1 | WebSocket 基础设施 | 30分钟 |
| Task 2 | 进度追踪器 | ✅ 已完成 |
| Task 3 | 人机协作检查点 | ✅ 已完成 |
| Task 4 | 医疗智能模板系统 | ✅ 已完成 |
| Task 5 | 故障恢复（断点续传） | ✅ 已完成 |
| Task 6 | 前端演示页面 | ✅ 已完成 |
| Task 7 | 集成测试 | ✅ 已完成 |

**Phase 1 总计：~4.5小时纯编码时间**

#### Phase 2（预留计划）- 2个任务

| 任务 | 内容 | 预计时间 | 启动条件 |
|:---|:---|:---|:---|
| Task 8 | 用户偏好学习系统 | 3-4周 | 使用Phase 1至少1个月，积累15+ PRD |
| Task 9 | 知识图谱关联系统 | 2-3周 | Obsidian笔记≥50篇 |

**Phase 2 总计：~6周（含测试优化）**

**完整系统共9个任务**

---

### 已完成的功能（Phase 1）

1. **WebSocket 基础设施** - 实时通信层
2. **进度追踪器** - 步骤级进度可视化
3. **检查点机制** - 人机协作暂停/继续/修改
4. **智能模板系统** - 医疗行业自动检测和应用
5. **故障恢复** - 断点续传和状态持久化
6. **前端演示** - 实时进度展示页面
7. **集成测试** - 端到端验证

### 如何运行

```bash
# 1. 启动后端
cd apps/api
python start.py

# 2. 在浏览器中打开
cd apps/web
python -m http.server 3000
# 访问 http://localhost:3000/progress-demo.html

# 3. 运行集成测试
cd apps/api
python -m pytest tests/test_integration_optimized.py -v
```

### 成功标准验证

- [x] PRD 生成过程可见进度条
- [x] 关键步骤可暂停和修改
- [x] 医疗产品自动加载合规检查模板
- [x] 任务失败可从断点恢复

### 后续优化方向 (Phase 2)

- **用户偏好学习** - 基于历史行为调整输出
- **知识图谱关联** - 智能关联 Obsidian 笔记
- **并行执行优化** - Requirement + Competitor 并行
- **智能缓存** - 避免重复 LLM 调用

---

## Phase 2: 用户偏好学习 + 知识图谱关联（预留计划）

> **为什么放在 Phase 2**：这两个功能依赖使用数据积累，建议 Phase 1 使用 1-2 个月后再实施

### 前置条件检查清单

Phase 2 开始前必须满足：
- [ ] 已生成至少 15 个 PRD
- [ ] 用户修改/反馈记录 ≥ 10 条
- [ ] Obsidian 知识库 ≥ 50 篇相关笔记
- [ ] Phase 1 系统稳定运行 1 个月以上

---

### Task 8: 用户偏好学习系统

**Files:**
- Create: `apps/api/app/agents/learning/__init__.py`
- Create: `apps/api/app/agents/learning/preference_store.py`
- Create: `apps/api/app/agents/learning/pattern_analyzer.py`
- Create: `apps/api/app/agents/learning/output_adapter.py`

**目标**: 让系统学习用户的 PRD 风格、关注重点、常用修改模式

**核心功能**:

```python
# 学习维度
class UserPreferenceProfile:
    prd_style: str  # "详细型"/"简洁型"/"技术导向"/"业务导向"
    focus_areas: List[str]  # ["合规", "用户体验", "技术架构"]
    section_depth: Dict[str, int]  # {"background": 3, "api": 1}
    common_additions: List[str]  # 用户经常补充的内容
    common_deletions: List[str]  # 用户经常删除的内容
    preferred_templates: List[str]  # 常用模板
    industry_expertise: str  # 用户在哪个行业最专业
```

**数据收集点**:
1. PRD 生成后用户的修改内容（diff 分析）
2. 检查点处的修改模式
3. 用户评分/反馈
4. 模板选择偏好

**预期效果**:
- 第 1 次使用：通用输出
- 第 5 次使用：自动应用用户偏好的章节结构
- 第 10 次使用：预判用户会补充的内容并预填充
- 第 20 次使用：输出风格和用户自己写的难以区分

**工作量**: 3-4 周

---

### Task 9: 知识图谱关联系统

**Files:**
- Create: `apps/api/app/agents/knowledge_graph/__init__.py`
- Create: `apps/api/app/agents/knowledge_graph/graph_builder.py`
- Create: `apps/api/app/agents/knowledge_graph/entity_extractor.py`
- Create: `apps/api/app/agents/knowledge_graph/related_finder.py`

**目标**: 自动发现 Obsidian 知识库中的关联内容，在生成 PRD 时智能引用

**核心功能**:

```python
# 知识图谱节点
class KnowledgeNode:
    id: str
    title: str
    type: str  # "project", "concept", "experience", "checklist"
    tags: List[str]
    entities: List[str]  # 提取的实体 ["病理切片", "等保三级"]
    related_nodes: List[str]  # 关联节点 ID

# 自动关联
class KnowledgeGraph:
    def find_related(self, current_project: str, limit: int = 5) -> List[KnowledgeNode]:
        """
        输入: "病理切片借阅平台"
        输出: [
            "病案复印经验" (相似度: 0.85),
            "医疗产品合规检查清单" (相似度: 0.78),
            "多院区数据同步方案" (相似度: 0.65),
            ...
        ]
        """
```

**Obsidian 集成增强**:

```python
class EnhancedObsidianIntegration:
    def write_with_links(self, content, filename, auto_link=True):
        """
        写入 PRD 时自动添加双向链接:
        - [[病案复印经验]]
        - [[医疗产品合规检查清单]]
        """

    def suggest_tags(self, content) -> List[str]:
        """
        基于内容自动建议标签:
        ["医疗信息化", "患者服务", "合规"]
        """

    def update_existing(self, filename, new_content) -> str:
        """
        PRD v2 生成时，对比 v1 生成 diff 和更新说明
        """
```

**用户界面**:

```
🤖: 生成 PRD 时我发现你的知识库有相关内容：
    ┌─────────────────────────────────────────┐
    │ 📎 相关参考                             │
    │                                         │
    │ • [[病案复印经验]] - 业务流程相似度 85%  │
    │ • [[医疗产品合规检查清单]] - 合规要求相关 │
    │ • [[多院区数据同步方案]] - 技术架构参考  │
    │                                         │
    │ [引用全部] [选择性引用] [忽略]          │
    └─────────────────────────────────────────┘
```

**预期效果**:
- PRD 自动关联历史经验
- 避免重复发明轮子
- 新人也能继承组织知识
- 知识库越丰富，输出质量越高

**工作量**: 2-3 周

---

### Phase 2 路线图

```
Month 1: Phase 1 上线使用，收集数据
         └─ 用户生成 PRD，系统记录修改模式

Month 2: 启动 Phase 2
         ├─ Week 1-2: 用户偏好学习系统
         ├─ Week 3-4: 知识图谱关联系统
         └─ Week 5: 集成测试和优化

Month 3: 完整系统运行
         └─ 越用越懂你的 AI 产品经理助手
```

---

### 数据准备指南（Phase 1 期间执行）

**为 Phase 2 准备数据，Phase 1 使用时注意**：

1. **PRD 输出保存**
   ```bash
   # 所有生成的 PRD 保存到固定位置
   Obsidian/04-项目层/PRD生成历史/
   ├── 2026-04-10_切片借阅_v1.md
   ├── 2026-04-12_管理后台_v1.md
   └── ...
   ```

2. **反馈记录**
   ```yaml
   # 在 PRD 文件底部添加反馈块
   ---
   ## AI反馈记录
   - 2026-04-10: 用户补充了医保对接流程（系统遗漏）
   - 2026-04-12: 用户删减了技术实现细节（过于详细）
   ```

3. **Obsidian 标签规范化**
   ```yaml
   # 统一标签格式
   tags:
     - 医疗信息化      # 行业
     - 患者服务        # 业务领域
     - 病案管理        # 功能模块
     - 已上线          # 状态
     - PRD             # 文档类型
   ```

4. **定期导出使用数据**
   ```bash
   # 每月导出一次数据供分析
   python scripts/export_usage_data.py
   ```

---

### 完整优先级矩阵（存档）

| 优化项 | 优先级 | 影响 | 工作量 | 所在阶段 |
|--------|--------|------|--------|----------|
| 流式输出+进度可视化 | P0 | 体验提升80% | 中 | Phase 1 |
| 人机协作检查点 | P0 | 质量提升50% | 中 | Phase 1 |
| 智能模板系统 | P1 | 效率提升40% | 小 | Phase 1 |
| 故障恢复 | P1 | 可靠性提升 | 小 | Phase 1 |
| **用户偏好学习** | **P2** | **长期价值** | **大** | **Phase 2** |
| **知识图谱关联** | **P2** | **深度价值** | **大** | **Phase 2** |

---

*最后更新: 2026-04-10*
*计划版本: v1.0*
