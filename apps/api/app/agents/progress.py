# -*- coding: utf-8 -*-
"""
进度追踪器模块

提供工作流执行进度的实时追踪和状态管理功能。
支持步骤级别的状态监控、进度计算和回调通知机制。
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from threading import Lock
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "pending"          # 待执行
    RUNNING = "running"          # 执行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 执行失败
    WAITING = "waiting"          # 等待检查点


@dataclass
class StepInfo:
    """步骤信息数据类

    Attributes:
        id: 步骤唯一标识
        name: 步骤名称
        agent_name: 执行该步骤的智能体名称
        status: 步骤当前状态
        progress: 进度百分比 (0-100)
        start_time: 开始时间
        end_time: 结束时间
        duration_ms: 执行耗时（毫秒）
        detail: 详细描述
        result_summary: 结果摘要
    """
    id: str
    name: str
    agent_name: str
    status: StepStatus = StepStatus.PENDING
    progress: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    detail: str = ""
    result_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "progress": self.progress,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "detail": self.detail,
            "result_summary": self.result_summary
        }


@dataclass
class WorkflowProgress:
    """工作流进度数据类

    Attributes:
        workflow_id: 工作流唯一标识
        user_input: 用户原始输入
        steps: 步骤列表
        current_step_index: 当前步骤索引
        overall_progress: 整体进度百分比
        status: 工作流状态
        created_at: 创建时间
        completed_at: 完成时间
    """
    workflow_id: str
    user_input: str
    steps: List[StepInfo] = field(default_factory=list)
    current_step_index: int = -1
    overall_progress: int = 0
    status: StepStatus = StepStatus.PENDING
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "workflow_id": self.workflow_id,
            "user_input": self.user_input,
            "steps": [step.to_dict() for step in self.steps],
            "current_step_index": self.current_step_index,
            "overall_progress": self.overall_progress,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class ProgressTracker:
    """进度追踪器类

    提供工作流执行进度的完整追踪功能，包括：
    - 工作流初始化和模板管理
    - 步骤状态管理和进度更新
    - 回调通知机制
    - 实时进度查询
    """

    # 预定义工作流模板
    WORKFLOW_TEMPLATES: Dict[str, List[Dict[str, str]]] = {
        "full_workflow": [
            {"name": "需求分析", "agent_name": "product-analyst", "detail": "分析用户需求，提取关键信息"},
            {"name": "竞品对标", "agent_name": "product-analyst", "detail": "分析竞品功能和市场定位"},
            {"name": "流程梳理", "agent_name": "product-analyst", "detail": "梳理业务流程和用户旅程"},
            {"name": "PRD生成", "agent_name": "product-analyst", "detail": "生成产品需求文档"},
            {"name": "合规检查", "agent_name": "compliance-checker", "detail": "检查医疗行业合规要求"},
            {"name": "架构设计", "agent_name": "tech-architect", "detail": "设计技术架构方案"},
            {"name": "里程碑规划", "agent_name": "milestone-planner", "detail": "制定开发里程碑计划"}
        ],
        "prd_only": [
            {"name": "需求分析", "agent_name": "product-analyst", "detail": "分析用户需求，提取关键信息"},
            {"name": "竞品对标", "agent_name": "product-analyst", "detail": "分析竞品功能和市场定位"},
            {"name": "流程梳理", "agent_name": "product-analyst", "detail": "梳理业务流程和用户旅程"},
            {"name": "PRD生成", "agent_name": "product-analyst", "detail": "生成产品需求文档"}
        ],
        "compliance_only": [
            {"name": "需求分析", "agent_name": "product-analyst", "detail": "分析用户需求，提取关键信息"},
            {"name": "合规检查", "agent_name": "compliance-checker", "detail": "检查医疗行业合规要求"},
            {"name": "风险评估", "agent_name": "compliance-checker", "detail": "评估合规风险等级"}
        ]
    }

    def __init__(self):
        """初始化进度追踪器"""
        self._workflows: Dict[str, WorkflowProgress] = {}
        self._callbacks: List[Callable[[str, WorkflowProgress], None]] = []
        self._lock = Lock()

    def register_callback(self, callback: Callable[[str, WorkflowProgress], None]) -> None:
        """注册进度回调函数

        Args:
            callback: 回调函数，接收事件类型和工作流进度对象
        """
        self._callbacks.append(callback)

    def initialize_workflow(
        self,
        user_input: str,
        template_name: Optional[str] = None,
        custom_steps: Optional[List[Dict[str, str]]] = None,
        workflow_id: Optional[str] = None
    ) -> str:
        """初始化工作流

        Args:
            user_input: 用户原始输入
            template_name: 模板名称（使用预定义模板）
            custom_steps: 自定义步骤列表（与template_name互斥）
            workflow_id: 可选的工作流ID，不指定则自动生成

        Returns:
            工作流ID

        Raises:
            ValueError: 模板名称无效或步骤配置错误
        """
        with self._lock:
            wf_id = workflow_id or str(uuid.uuid4())

            # 确定步骤配置
            if template_name and custom_steps:
                raise ValueError("不能同时指定模板名称和自定义步骤")

            if template_name:
                if template_name not in self.WORKFLOW_TEMPLATES:
                    raise ValueError(f"未知模板: {template_name}，可用模板: {list(self.WORKFLOW_TEMPLATES.keys())}")
                step_configs = self.WORKFLOW_TEMPLATES[template_name]
            elif custom_steps:
                step_configs = custom_steps
            else:
                # 默认使用完整工作流模板
                step_configs = self.WORKFLOW_TEMPLATES["full_workflow"]

            # 创建步骤列表
            steps = []
            for idx, config in enumerate(step_configs):
                step = StepInfo(
                    id=f"{wf_id}_step_{idx}",
                    name=config["name"],
                    agent_name=config["agent_name"],
                    detail=config.get("detail", ""),
                    status=StepStatus.PENDING
                )
                steps.append(step)

            # 创建工作流进度对象
            workflow = WorkflowProgress(
                workflow_id=wf_id,
                user_input=user_input,
                steps=steps,
                status=StepStatus.PENDING,
                created_at=datetime.now()
            )

            self._workflows[wf_id] = workflow
            self._notify("workflow_initialized", workflow)

            return wf_id

    def start_step(self, workflow_id: str, step_id: Optional[str] = None) -> StepInfo:
        """开始执行步骤

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID，不指定则开始当前待执行的步骤

        Returns:
            步骤信息对象

        Raises:
            KeyError: 工作流不存在
            ValueError: 步骤状态不正确
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]

            # 确定要开始的步骤
            if step_id:
                step = self._get_step_by_id(workflow, step_id)
                if not step:
                    raise ValueError(f"步骤不存在: {step_id}")
            else:
                # 查找第一个待执行或等待中的步骤
                step = None
                for idx, s in enumerate(workflow.steps):
                    if s.status in [StepStatus.PENDING, StepStatus.WAITING]:
                        step = s
                        workflow.current_step_index = idx
                        break

                if not step:
                    raise ValueError("没有可执行的步骤")

            # 更新步骤状态
            step.status = StepStatus.RUNNING
            step.start_time = datetime.now()
            step.progress = 0

            # 更新工作流状态
            if workflow.status == StepStatus.PENDING:
                workflow.status = StepStatus.RUNNING

            self._calculate_overall_progress(workflow)
            self._notify("step_started", workflow)

            return step

    def update_step_progress(self, workflow_id: str, step_id: str, progress: int, detail: str = "") -> None:
        """更新步骤进度

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            progress: 进度百分比 (0-100)
            detail: 进度详情

        Raises:
            KeyError: 工作流不存在
            ValueError: 进度值无效
        """
        if not 0 <= progress <= 100:
            raise ValueError("进度值必须在 0-100 之间")

        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            step = self._get_step_by_id(workflow, step_id)

            if not step:
                raise ValueError(f"步骤不存在: {step_id}")

            step.progress = progress
            if detail:
                step.detail = detail

            self._calculate_overall_progress(workflow)
            self._notify("step_progress_updated", workflow)

    def complete_step(self, workflow_id: str, step_id: str, result_summary: str = "") -> None:
        """完成步骤执行

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            result_summary: 结果摘要

        Raises:
            KeyError: 工作流不存在
            ValueError: 步骤状态不正确
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            step = self._get_step_by_id(workflow, step_id)

            if not step:
                raise ValueError(f"步骤不存在: {step_id}")

            if step.status != StepStatus.RUNNING:
                raise ValueError(f"步骤状态必须为运行中，当前状态: {step.status.value}")

            # 更新步骤状态
            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()
            step.progress = 100
            step.result_summary = result_summary

            # 计算执行耗时
            if step.start_time:
                duration = step.end_time - step.start_time
                step.duration_ms = int(duration.total_seconds() * 1000)

            self._calculate_overall_progress(workflow)
            self._notify("step_completed", workflow)

    def fail_step(self, workflow_id: str, step_id: str, error_message: str) -> None:
        """标记步骤执行失败

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            error_message: 错误信息

        Raises:
            KeyError: 工作流不存在
            ValueError: 步骤不存在
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            step = self._get_step_by_id(workflow, step_id)

            if not step:
                raise ValueError(f"步骤不存在: {step_id}")

            # 更新步骤状态
            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            step.result_summary = f"执行失败: {error_message}"

            # 计算执行耗时
            if step.start_time:
                duration = step.end_time - step.start_time
                step.duration_ms = int(duration.total_seconds() * 1000)

            # 更新工作流状态
            workflow.status = StepStatus.FAILED

            self._notify("step_failed", workflow)

    def wait_for_checkpoint(self, workflow_id: str, step_id: str, checkpoint_message: str = "") -> None:
        """设置步骤等待检查点

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            checkpoint_message: 检查点提示信息

        Raises:
            KeyError: 工作流不存在
            ValueError: 步骤不存在
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            step = self._get_step_by_id(workflow, step_id)

            if not step:
                raise ValueError(f"步骤不存在: {step_id}")

            step.status = StepStatus.WAITING
            if checkpoint_message:
                step.detail = checkpoint_message

            self._notify("step_waiting", workflow)

    def complete_workflow(self, workflow_id: str, final_summary: str = "") -> None:
        """完成工作流执行

        Args:
            workflow_id: 工作流ID
            final_summary: 最终摘要

        Raises:
            KeyError: 工作流不存在
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            workflow.status = StepStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.overall_progress = 100

            self._notify("workflow_completed", workflow)

    def get_current_step(self, workflow_id: str) -> Optional[StepInfo]:
        """获取当前执行的步骤

        Args:
            workflow_id: 工作流ID

        Returns:
            当前步骤信息，如果没有则返回None

        Raises:
            KeyError: 工作流不存在
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            if 0 <= workflow.current_step_index < len(workflow.steps):
                return workflow.steps[workflow.current_step_index]
            return None

    def get_step(self, workflow_id: str, step_id: str) -> Optional[StepInfo]:
        """获取指定步骤信息

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID

        Returns:
            步骤信息，如果不存在则返回None

        Raises:
            KeyError: 工作流不存在
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            workflow = self._workflows[workflow_id]
            return self._get_step_by_id(workflow, step_id)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowProgress]:
        """获取工作流进度信息

        Args:
            workflow_id: 工作流ID

        Returns:
            工作流进度对象，如果不存在则返回None
        """
        with self._lock:
            return self._workflows.get(workflow_id)

    def _notify(self, event_type: str, workflow: WorkflowProgress) -> None:
        """通知所有注册的回调函数

        Args:
            event_type: 事件类型
            workflow: 工作流进度对象
        """
        for callback in self._callbacks:
            try:
                callback(event_type, workflow)
            except Exception as e:
                # 回调执行失败不应影响主流程
                logger.error(f"回调执行失败: {e}")

    def _calculate_overall_progress(self, workflow: WorkflowProgress) -> None:
        """计算整体进度

        Args:
            workflow: 工作流进度对象
        """
        if not workflow.steps:
            workflow.overall_progress = 0
            return

        total_progress = sum(step.progress for step in workflow.steps)
        workflow.overall_progress = total_progress // len(workflow.steps)

    def _get_step_by_id(self, workflow: WorkflowProgress, step_id: str) -> Optional[StepInfo]:
        """根据ID查找步骤

        Args:
            workflow: 工作流进度对象
            step_id: 步骤ID

        Returns:
            步骤信息，如果不存在则返回None
        """
        for step in workflow.steps:
            if step.id == step_id:
                return step
        return None

    def to_dict(self, workflow_id: str) -> Dict[str, Any]:
        """将工作流进度转换为字典格式

        Args:
            workflow_id: 工作流ID

        Returns:
            工作流进度的字典表示

        Raises:
            KeyError: 工作流不存在
        """
        with self._lock:
            if workflow_id not in self._workflows:
                raise KeyError(f"工作流不存在: {workflow_id}")

            return self._workflows[workflow_id].to_dict()


# 全局进度追踪器实例
progress_tracker = ProgressTracker()
