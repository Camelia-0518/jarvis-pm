# -*- coding: utf-8 -*-
"""
ProgressTracker 测试模块

测试进度追踪器的基本功能、状态流转、回调机制和进度计算
"""

import pytest
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable, Any


# ============== 模拟 ProgressTracker 实现（用于测试）=============

class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class StepInfo:
    """步骤信息"""
    id: str
    name: str
    agent_name: str
    status: StepStatus = StepStatus.PENDING
    progress: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    detail: str = ""
    result_summary: str = ""
    weight: float = 1.0


@dataclass
class WorkflowProgress:
    """工作流进度"""
    workflow_id: str
    user_input: str = ""
    steps: List[StepInfo] = field(default_factory=list)
    overall_progress: int = 0
    current_step_index: int = -1
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ProgressTracker:
    """进度追踪器 - 跟踪 Agent 执行进度"""

    WORKFLOW_TEMPLATES = {
        "full_workflow": [
            {"id": "intent", "name": "意图识别", "agent_name": "IntentClassifier", "weight": 0.1},
            {"id": "plan", "name": "任务规划", "agent_name": "TaskPlanner", "weight": 0.1},
            {"id": "clarify", "name": "需求澄清", "agent_name": "RequirementClarifier", "weight": 0.15},
            {"id": "analyze", "name": "竞品分析", "agent_name": "CompetitorAnalyzer", "weight": 0.15},
            {"id": "design", "name": "流程设计", "agent_name": "ProcessDesigner", "weight": 0.2},
            {"id": "generate", "name": "PRD生成", "agent_name": "PRDGenerator", "weight": 0.2},
            {"id": "review", "name": "质量检查", "agent_name": "QualityReviewer", "weight": 0.1},
        ],
        "prd_only": [
            {"id": "intent", "name": "意图识别", "agent_name": "IntentClassifier", "weight": 0.2},
            {"id": "plan", "name": "任务规划", "agent_name": "TaskPlanner", "weight": 0.2},
            {"id": "generate", "name": "PRD生成", "agent_name": "PRDGenerator", "weight": 0.4},
            {"id": "review", "name": "质量检查", "agent_name": "QualityReviewer", "weight": 0.2},
        ],
        "compliance_only": [
            {"id": "intent", "name": "意图识别", "agent_name": "IntentClassifier", "weight": 0.3},
            {"id": "plan", "name": "任务规划", "agent_name": "TaskPlanner", "weight": 0.3},
            {"id": "review", "name": "合规检查", "agent_name": "ComplianceReviewer", "weight": 0.4},
        ],
    }

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.progress = WorkflowProgress(workflow_id=workflow_id)
        self._step_map: Dict[str, StepInfo] = {}
        self._callbacks: List[Callable[[str, Dict], Any]] = []

    def register_callback(self, callback: Callable[[str, Dict], Any]):
        """注册进度回调函数"""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str, Dict], Any]):
        """注销回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self, event_type: str, data: dict):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event_type, data))
                else:
                    callback(event_type, data)
            except Exception as e:
                print(f"[ProgressTracker] Callback error: {e}")

    def initialize_workflow(self, workflow_type: str, user_input: str):
        """初始化工作流"""
        self.progress.user_input = user_input
        template = self.WORKFLOW_TEMPLATES.get(workflow_type, self.WORKFLOW_TEMPLATES["full_workflow"])

        self.progress.steps = []
        self._step_map = {}

        for step_config in template:
            step = StepInfo(
                id=step_config["id"],
                name=step_config["name"],
                agent_name=step_config["agent_name"],
                weight=step_config.get("weight", 1.0)
            )
            self.progress.steps.append(step)
            self._step_map[step.id] = step

        self.progress.status = "running"
        self._notify("workflow_started", {
            "workflow_id": self.workflow_id,
            "steps": [{"id": s.id, "name": s.name} for s in self.progress.steps]
        })

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

        self._calculate_overall_progress()

        self._notify("step_progress", {
            "step_id": step_id,
            "step_name": step.name,
            "progress": progress,
            "detail": detail,
            "overall_progress": self.progress.overall_progress
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
            "result_summary": result_summary,
            "duration_ms": step.duration_ms,
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

    def wait_for_user(self, step_id: str, checkpoint_title: str, checkpoint_description: str):
        """步骤等待用户确认"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.status = StepStatus.WAITING
        step.detail = f"等待用户确认: {checkpoint_title}"

        self._notify("step_waiting", {
            "step_id": step_id,
            "step_name": step.name,
            "checkpoint_title": checkpoint_title,
            "checkpoint_description": checkpoint_description
        })

    def resume_step(self, step_id: str):
        """恢复步骤执行"""
        step = self._step_map.get(step_id)
        if not step:
            return

        step.status = StepStatus.RUNNING
        step.detail = "继续执行..."

        self._notify("step_resumed", {
            "step_id": step_id,
            "step_name": step.name
        })

    def complete_workflow(self):
        """完成工作流"""
        self.progress.status = "completed"
        self.progress.completed_at = datetime.now()
        self.progress.overall_progress = 100

        self._notify("workflow_completed", {
            "workflow_id": self.workflow_id,
            "total_steps": len(self.progress.steps),
            "completed_at": self.progress.completed_at.isoformat()
        })

    def get_step(self, step_id: str) -> Optional[StepInfo]:
        """获取步骤信息"""
        return self._step_map.get(step_id)

    def get_current_step(self) -> Optional[StepInfo]:
        """获取当前步骤"""
        if 0 <= self.progress.current_step_index < len(self.progress.steps):
            return self.progress.steps[self.progress.current_step_index]
        return None

    def _calculate_overall_progress(self):
        """计算总体进度（加权平均）"""
        if not self.progress.steps:
            return

        total_weight = sum(step.weight for step in self.progress.steps)
        weighted_progress = sum(
            step.progress * step.weight for step in self.progress.steps
        )

        self.progress.overall_progress = int(weighted_progress / total_weight)


# ============== Fixtures ==============

@pytest.fixture
def tracker():
    """创建基础 ProgressTracker 实例"""
    return ProgressTracker("test-workflow-001")


@pytest.fixture
def initialized_tracker(tracker):
    """创建已初始化工作流的 ProgressTracker 实例"""
    tracker.initialize_workflow("full_workflow", "测试用户输入")
    return tracker


@pytest.fixture
def event_collector():
    """创建事件收集器用于测试回调"""
    events = []

    def sync_callback(event_type: str, data: dict):
        events.append((event_type, data))

    async def async_callback(event_type: str, data: dict):
        events.append((event_type, data))

    return {
        "events": events,
        "sync_callback": sync_callback,
        "async_callback": async_callback
    }


# ============== 测试类 ==============

class TestProgressTrackerBasic:
    """测试 ProgressTracker 基本功能"""

    def test_initialization(self, tracker):
        """测试基本初始化"""
        assert tracker.workflow_id == "test-workflow-001"
        assert tracker.progress.workflow_id == "test-workflow-001"
        assert tracker.progress.status == "pending"
        assert len(tracker.progress.steps) == 0
        assert tracker.progress.overall_progress == 0

    def test_workflow_templates_exist(self, tracker):
        """测试工作流模板存在"""
        assert "full_workflow" in tracker.WORKFLOW_TEMPLATES
        assert "prd_only" in tracker.WORKFLOW_TEMPLATES
        assert "compliance_only" in tracker.WORKFLOW_TEMPLATES

    def test_initialize_workflow_full(self, tracker):
        """测试初始化完整工作流"""
        tracker.initialize_workflow("full_workflow", "创建一个PRD")

        assert tracker.progress.user_input == "创建一个PRD"
        assert tracker.progress.status == "running"
        assert len(tracker.progress.steps) == 7

        # 验证步骤顺序和内容
        expected_steps = ["intent", "plan", "clarify", "analyze", "design", "generate", "review"]
        actual_steps = [step.id for step in tracker.progress.steps]
        assert actual_steps == expected_steps

        # 验证所有步骤初始状态为 PENDING
        for step in tracker.progress.steps:
            assert step.status == StepStatus.PENDING
            assert step.progress == 0

    def test_initialize_workflow_prd_only(self, tracker):
        """测试初始化 PRD Only 工作流"""
        tracker.initialize_workflow("prd_only", "快速生成PRD")

        assert len(tracker.progress.steps) == 4
        expected_steps = ["intent", "plan", "generate", "review"]
        actual_steps = [step.id for step in tracker.progress.steps]
        assert actual_steps == expected_steps

    def test_initialize_workflow_compliance_only(self, tracker):
        """测试初始化合规检查工作流"""
        tracker.initialize_workflow("compliance_only", "合规检查")

        assert len(tracker.progress.steps) == 3
        expected_steps = ["intent", "plan", "review"]
        actual_steps = [step.id for step in tracker.progress.steps]
        assert actual_steps == expected_steps

    def test_get_step(self, initialized_tracker):
        """测试获取步骤信息"""
        step = initialized_tracker.get_step("intent")
        assert step is not None
        assert step.id == "intent"
        assert step.name == "意图识别"
        assert step.agent_name == "IntentClassifier"

    def test_get_step_not_found(self, initialized_tracker):
        """测试获取不存在的步骤"""
        step = initialized_tracker.get_step("nonexistent")
        assert step is None

    def test_get_current_step_initial(self, initialized_tracker):
        """测试获取初始当前步骤"""
        # 初始状态下 current_step_index 为 -1
        current = initialized_tracker.get_current_step()
        assert current is None


class TestProgressTrackerWorkflow:
    """测试完整工作流状态流转"""

    def test_step_status_transition_pending_to_running(self, initialized_tracker):
        """测试步骤状态从 PENDING 转为 RUNNING"""
        initialized_tracker.start_step("intent", "开始分析意图...")

        step = initialized_tracker.get_step("intent")
        assert step.status == StepStatus.RUNNING
        assert step.start_time is not None
        assert step.detail == "开始分析意图..."

    def test_step_status_transition_running_to_completed(self, initialized_tracker):
        """测试步骤状态从 RUNNING 转为 COMPLETED"""
        initialized_tracker.start_step("intent", "分析中...")
        initialized_tracker.complete_step("intent", "意图识别完成")

        step = initialized_tracker.get_step("intent")
        assert step.status == StepStatus.COMPLETED
        assert step.progress == 100
        assert step.end_time is not None
        assert step.result_summary == "意图识别完成"
        assert step.duration_ms >= 0

    def test_step_status_transition_running_to_failed(self, initialized_tracker):
        """测试步骤状态从 RUNNING 转为 FAILED"""
        initialized_tracker.start_step("intent", "分析中...")
        initialized_tracker.fail_step("intent", "网络连接失败")

        step = initialized_tracker.get_step("intent")
        assert step.status == StepStatus.FAILED
        assert step.end_time is not None
        assert "网络连接失败" in step.result_summary
        assert initialized_tracker.progress.status == "failed"

    def test_step_status_transition_to_waiting(self, initialized_tracker):
        """测试步骤状态转为 WAITING"""
        initialized_tracker.start_step("clarify", "澄清需求...")
        initialized_tracker.wait_for_user(
            "clarify",
            "确认需求范围",
            "请确认是否包含导出功能"
        )

        step = initialized_tracker.get_step("clarify")
        assert step.status == StepStatus.WAITING
        assert "确认需求范围" in step.detail

    def test_step_status_transition_waiting_to_running(self, initialized_tracker):
        """测试步骤状态从 WAITING 恢复为 RUNNING"""
        initialized_tracker.start_step("clarify", "澄清需求...")
        initialized_tracker.wait_for_user("clarify", "确认需求", "请确认")
        initialized_tracker.resume_step("clarify")

        step = initialized_tracker.get_step("clarify")
        assert step.status == StepStatus.RUNNING
        assert step.detail == "继续执行..."

    def test_complete_workflow(self, initialized_tracker):
        """测试完成整个工作流"""
        # 顺序执行所有步骤
        for step in initialized_tracker.progress.steps:
            initialized_tracker.start_step(step.id, f"执行 {step.name}...")
            initialized_tracker.complete_step(step.id, f"{step.name} 完成")

        initialized_tracker.complete_workflow()

        assert initialized_tracker.progress.status == "completed"
        assert initialized_tracker.progress.overall_progress == 100
        assert initialized_tracker.progress.completed_at is not None

        # 验证所有步骤都已完成
        for step in initialized_tracker.progress.steps:
            assert step.status == StepStatus.COMPLETED
            assert step.progress == 100

    def test_workflow_failure_handling(self, initialized_tracker):
        """测试工作流失败处理"""
        # 开始第一个步骤
        initialized_tracker.start_step("intent", "分析中...")
        initialized_tracker.complete_step("intent", "完成")

        # 第二个步骤失败
        initialized_tracker.start_step("plan", "规划中...")
        initialized_tracker.fail_step("plan", "规划失败")

        assert initialized_tracker.progress.status == "failed"

        # 验证第一个步骤仍保持完成状态
        intent_step = initialized_tracker.get_step("intent")
        assert intent_step.status == StepStatus.COMPLETED

        # 验证失败步骤状态
        plan_step = initialized_tracker.get_step("plan")
        assert plan_step.status == StepStatus.FAILED

    def test_update_step_progress(self, initialized_tracker):
        """测试更新步骤进度"""
        initialized_tracker.start_step("intent", "开始分析...")

        # 更新进度到 25%
        initialized_tracker.update_step_progress("intent", 25, "初步分析中...")
        assert initialized_tracker.get_step("intent").progress == 25

        # 更新进度到 50%
        initialized_tracker.update_step_progress("intent", 50, "深入分析中...")
        assert initialized_tracker.get_step("intent").progress == 50

        # 更新进度到 75%
        initialized_tracker.update_step_progress("intent", 75, "分析即将完成...")
        assert initialized_tracker.get_step("intent").progress == 75

    def test_invalid_step_operations(self, initialized_tracker):
        """测试对不存在步骤的操作"""
        # 这些操作不应该抛出异常
        initialized_tracker.start_step("nonexistent", "...")
        initialized_tracker.complete_step("nonexistent", "...")
        initialized_tracker.fail_step("nonexistent", "...")
        initialized_tracker.update_step_progress("nonexistent", 50)
        initialized_tracker.wait_for_user("nonexistent", "", "")
        initialized_tracker.resume_step("nonexistent")

        # 验证没有影响现有步骤
        assert len(initialized_tracker.progress.steps) == 7


class TestProgressTrackerCallbacks:
    """测试回调机制"""

    def test_register_callback(self, initialized_tracker, event_collector):
        """测试注册回调函数"""
        initialized_tracker.register_callback(event_collector["sync_callback"])

        # 触发事件
        initialized_tracker.start_step("intent", "开始...")

        assert len(event_collector["events"]) == 1
        assert event_collector["events"][0][0] == "step_started"

    def test_unregister_callback(self, initialized_tracker, event_collector):
        """测试注销回调函数"""
        callback = event_collector["sync_callback"]
        initialized_tracker.register_callback(callback)
        initialized_tracker.unregister_callback(callback)

        # 触发事件
        initialized_tracker.start_step("intent", "开始...")

        # 事件不应该被记录
        assert len(event_collector["events"]) == 0

    def test_multiple_callbacks(self, initialized_tracker):
        """测试多个回调函数"""
        events1 = []
        events2 = []

        def callback1(event_type, data):
            events1.append(event_type)

        def callback2(event_type, data):
            events2.append(event_type)

        initialized_tracker.register_callback(callback1)
        initialized_tracker.register_callback(callback2)

        initialized_tracker.start_step("intent", "开始...")

        assert len(events1) == 1
        assert len(events2) == 1
        assert events1[0] == events2[0] == "step_started"

    @pytest.mark.asyncio
    async def test_async_callback(self, initialized_tracker, event_collector):
        """测试异步回调函数"""
        initialized_tracker.register_callback(event_collector["async_callback"])

        initialized_tracker.start_step("intent", "开始...")

        # 给异步任务执行时间
        await asyncio.sleep(0.1)

        assert len(event_collector["events"]) == 1
        assert event_collector["events"][0][0] == "step_started"

    def test_callback_event_types(self, initialized_tracker, event_collector):
        """测试不同类型的事件回调"""
        initialized_tracker.register_callback(event_collector["sync_callback"])

        # 工作流开始
        # 注意: initialize_workflow 会触发 workflow_started 事件
        # 但我们在 fixture 中已经调用了 initialize_workflow
        # 所以这里直接测试其他事件

        # 步骤开始
        initialized_tracker.start_step("intent", "开始...")
        # 进度更新
        initialized_tracker.update_step_progress("intent", 50, "进行中...")
        # 步骤完成
        initialized_tracker.complete_step("intent", "完成")
        # 工作流完成
        initialized_tracker.complete_workflow()

        event_types = [e[0] for e in event_collector["events"]]
        assert "step_started" in event_types
        assert "step_progress" in event_types
        assert "step_completed" in event_types
        assert "workflow_completed" in event_types

    def test_callback_error_handling(self, initialized_tracker):
        """测试回调错误处理"""
        def bad_callback(event_type, data):
            raise ValueError("回调错误")

        initialized_tracker.register_callback(bad_callback)

        # 不应该抛出异常
        initialized_tracker.start_step("intent", "开始...")

        # 步骤应该正常开始
        assert initialized_tracker.get_step("intent").status == StepStatus.RUNNING

    def test_callback_data_content(self, initialized_tracker, event_collector):
        """测试回调数据内容"""
        initialized_tracker.register_callback(event_collector["sync_callback"])

        initialized_tracker.start_step("intent", "分析用户意图中...")

        event_type, data = event_collector["events"][0]
        assert event_type == "step_started"
        assert data["step_id"] == "intent"
        assert data["step_name"] == "意图识别"
        assert data["detail"] == "分析用户意图中..."


class TestProgressCalculation:
    """测试进度计算准确性"""

    def test_initial_progress(self, initialized_tracker):
        """测试初始进度"""
        assert initialized_tracker.progress.overall_progress == 0

    def test_single_step_progress_calculation(self, initialized_tracker):
        """测试单步骤进度计算"""
        initialized_tracker.start_step("intent", "开始...")

        # intent 步骤权重为 0.1
        initialized_tracker.update_step_progress("intent", 50, "50% 完成")

        # 加权进度: 50 * 0.1 = 5
        # 总权重: 1.0
        # 总体进度: 5 / 1.0 = 5
        assert initialized_tracker.progress.overall_progress == 5

    def test_multiple_steps_progress_calculation(self, initialized_tracker):
        """测试多步骤进度计算"""
        # intent (0.1) 完成 100%
        initialized_tracker.start_step("intent", "开始...")
        initialized_tracker.update_step_progress("intent", 100, "完成")

        # plan (0.1) 完成 50%
        initialized_tracker.start_step("plan", "开始...")
        initialized_tracker.update_step_progress("plan", 50, "50%")

        # 加权进度: 100*0.1 + 50*0.1 = 10 + 5 = 15
        # 总权重: 1.0
        # 总体进度: 15 / 1.0 = 15
        assert initialized_tracker.progress.overall_progress == 15

    def test_complete_all_steps_progress(self, initialized_tracker):
        """测试完成所有步骤后的进度"""
        for step in initialized_tracker.progress.steps:
            initialized_tracker.start_step(step.id, "...")
            initialized_tracker.complete_step(step.id, "完成")

        assert initialized_tracker.progress.overall_progress == 100

    def test_progress_after_complete_workflow(self, initialized_tracker):
        """测试完成工作流后的进度"""
        # 完成所有步骤
        for step in initialized_tracker.progress.steps:
            initialized_tracker.start_step(step.id, "...")
            initialized_tracker.complete_step(step.id, "完成")

        initialized_tracker.complete_workflow()

        # complete_workflow 应该设置进度为 100
        assert initialized_tracker.progress.overall_progress == 100

    def test_weighted_progress_accuracy(self, tracker):
        """测试加权进度计算精度"""
        # 使用 prd_only 模板测试不同的权重
        tracker.initialize_workflow("prd_only", "测试")

        # prd_only 权重: intent(0.2), plan(0.2), generate(0.4), review(0.2)

        # intent 完成 100%
        tracker.start_step("intent", "...")
        tracker.complete_step("intent", "完成")

        # 进度: 100*0.2 = 20
        assert tracker.progress.overall_progress == 20

        # plan 完成 100%
        tracker.start_step("plan", "...")
        tracker.complete_step("plan", "完成")

        # 进度: 100*0.2 + 100*0.2 = 40
        assert tracker.progress.overall_progress == 40

        # generate 完成 50%
        tracker.start_step("generate", "...")
        tracker.update_step_progress("generate", 50, "50%")

        # 进度: 20 + 20 + 50*0.4 = 60
        assert tracker.progress.overall_progress == 60


class TestWorkflowTemplates:
    """测试工作流模板初始化"""

    def test_full_workflow_template_structure(self):
        """测试完整工作流模板结构"""
        template = ProgressTracker.WORKFLOW_TEMPLATES["full_workflow"]

        assert len(template) == 7

        # 验证每个步骤都有必要的字段
        for step in template:
            assert "id" in step
            assert "name" in step
            assert "agent_name" in step
            assert "weight" in step
            assert isinstance(step["weight"], (int, float))
            assert step["weight"] > 0

    def test_prd_only_template_structure(self):
        """测试 PRD Only 模板结构"""
        template = ProgressTracker.WORKFLOW_TEMPLATES["prd_only"]

        assert len(template) == 4

        expected_ids = ["intent", "plan", "generate", "review"]
        actual_ids = [step["id"] for step in template]
        assert actual_ids == expected_ids

    def test_compliance_template_structure(self):
        """测试合规检查模板结构"""
        template = ProgressTracker.WORKFLOW_TEMPLATES["compliance_only"]

        assert len(template) == 3

        expected_ids = ["intent", "plan", "review"]
        actual_ids = [step["id"] for step in template]
        assert actual_ids == expected_ids

    def test_template_weights_sum_to_one(self):
        """测试模板权重总和为 1"""
        for template_name, template in ProgressTracker.WORKFLOW_TEMPLATES.items():
            total_weight = sum(step["weight"] for step in template)
            assert abs(total_weight - 1.0) < 0.001, f"{template_name} 权重总和不为 1"

    def test_unknown_workflow_type_fallback(self, tracker):
        """测试未知工作流类型回退"""
        tracker.initialize_workflow("unknown_type", "测试")

        # 应该回退到 full_workflow
        assert len(tracker.progress.steps) == 7


# ============== 集成测试 ==============

class TestProgressTrackerIntegration:
    """集成测试 - 模拟完整工作流场景"""

    def test_full_prd_workflow_simulation(self, tracker, event_collector):
        """模拟完整的 PRD 生成工作流"""
        tracker.register_callback(event_collector["sync_callback"])

        # 1. 初始化工作流
        tracker.initialize_workflow("full_workflow", "创建一个病案复印功能的PRD")

        # 2. 意图识别
        tracker.start_step("intent", "分析用户意图...")
        tracker.update_step_progress("intent", 50, "识别中...")
        tracker.complete_step("intent", "识别为: PRD生成任务")

        # 3. 任务规划
        tracker.start_step("plan", "规划执行步骤...")
        tracker.complete_step("plan", "规划完成: 7个步骤")

        # 4. 需求澄清
        tracker.start_step("clarify", "澄清功能需求...")
        tracker.wait_for_user("clarify", "确认需求范围", "是否包含导出功能？")
        tracker.resume_step("clarify")
        tracker.complete_step("clarify", "需求已确认")

        # 5. 竞品分析
        tracker.start_step("analyze", "分析竞品方案...")
        tracker.complete_step("analyze", "分析了3个竞品")

        # 6. 流程设计
        tracker.start_step("design", "设计业务流程...")
        tracker.complete_step("design", "流程设计完成")

        # 7. PRD生成
        tracker.start_step("generate", "生成PRD文档...")
        tracker.update_step_progress("generate", 30, "生成概述...")
        tracker.update_step_progress("generate", 60, "生成详细需求...")
        tracker.update_step_progress("generate", 90, "生成验收标准...")
        tracker.complete_step("generate", "PRD生成完成")

        # 8. 质量检查
        tracker.start_step("review", "检查PRD质量...")
        tracker.complete_step("review", "检查通过")

        # 9. 完成工作流
        tracker.complete_workflow()

        # 验证结果
        assert tracker.progress.status == "completed"
        assert tracker.progress.overall_progress == 100

        # 验证事件记录
        event_types = [e[0] for e in event_collector["events"]]
        assert event_types.count("step_started") == 7
        assert event_types.count("step_completed") == 7
        assert event_types.count("step_waiting") == 1
        assert event_types.count("step_resumed") == 1
        assert "workflow_started" in event_types
        assert "workflow_completed" in event_types

    def test_failed_workflow_simulation(self, tracker, event_collector):
        """模拟失败的工作流"""
        tracker.register_callback(event_collector["sync_callback"])

        tracker.initialize_workflow("prd_only", "生成PRD")

        # 前两个步骤成功
        tracker.start_step("intent", "...")
        tracker.complete_step("intent", "完成")

        tracker.start_step("plan", "...")
        tracker.complete_step("plan", "完成")

        # 生成步骤失败
        tracker.start_step("generate", "...")
        tracker.fail_step("generate", "LLM API 调用失败")

        # 验证状态
        assert tracker.progress.status == "failed"
        assert tracker.get_step("intent").status == StepStatus.COMPLETED
        assert tracker.get_step("plan").status == StepStatus.COMPLETED
        assert tracker.get_step("generate").status == StepStatus.FAILED
        assert tracker.get_step("review").status == StepStatus.PENDING  # 未执行


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
