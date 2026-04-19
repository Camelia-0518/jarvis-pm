#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recovery Manager - 故障恢复管理器

提供工作流故障恢复和断点续传功能
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .persistence import WorkflowPersistence, WorkflowState, get_persistence

logger = logging.getLogger(__name__)


class RecoveryInfo:
    """
    恢复信息数据类

    包含工作流恢复所需的所有信息
    """

    def __init__(self, workflow_state: WorkflowState):
        self.workflow_id = workflow_state.workflow_id
        self.status = workflow_state.status
        self.current_step = workflow_state.current_step
        self.completed_steps = workflow_state.get_completed_steps()
        self.failed_steps = workflow_state.get_failed_steps()
        self.step_results = workflow_state.step_results
        self.user_input = workflow_state.user_input
        self.plan = workflow_state.plan
        self.error = workflow_state.error
        self.created_at = workflow_state.created_at
        self.updated_at = workflow_state.updated_at

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "step_count": len(self.step_results),
            "completed_count": len(self.completed_steps),
            "failed_count": len(self.failed_steps),
            "can_resume": self.status in {"failed", "running", "executing"},
            "user_input": self.user_input,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class RecoveryManager:
    """
    故障恢复管理器

    负责:
    1. 启动并监控工作流
    2. 恢复失败/中断的工作流
    3. 管理断点续传
    4. 提供恢复信息查询
    """

    def __init__(
        self,
        persistence: Optional[WorkflowPersistence] = None,
        strategy_layer = None
    ):
        """
        初始化恢复管理器

        Args:
            persistence: 持久化实例，默认使用全局实例
            strategy_layer: 策略层实例，用于执行工作流
        """
        self.persistence = persistence or get_persistence()
        self.strategy_layer = strategy_layer
        self._active_recoveries: Dict[str, Dict] = {}

    async def start_workflow(
        self,
        workflow_id: str,
        user_input: str,
        context: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        启动并监控工作流

        Args:
            workflow_id: 工作流ID
            user_input: 用户输入
            context: 上下文信息

        Returns:
            (是否成功, 消息)
        """
        try:
            # 检查是否已存在
            existing = self.persistence.load(workflow_id)
            if existing and existing.status in {"running", "executing"}:
                return False, f"Workflow {workflow_id} is already running"

            # 创建新的工作流状态
            workflow = WorkflowState(
                workflow_id=workflow_id,
                status="running",
                user_input=user_input
            )
            self.persistence.save(workflow)

            logger.info(f"Started workflow {workflow_id}")
            return True, f"Workflow {workflow_id} started successfully"

        except Exception as e:
            error_msg = f"Failed to start workflow {workflow_id}: {e}"
            logger.error(error_msg)
            return False, error_msg

    async def recover_workflow(self, workflow_id: str) -> Tuple[bool, str]:
        """
        恢复失败/中断的工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            (是否成功, 消息)
        """
        workflow = self.persistence.load(workflow_id)
        if not workflow:
            return False, f"Workflow {workflow_id} not found"

        # 检查是否可以恢复
        if workflow.status not in {"failed", "running", "executing"}:
            return False, f"Workflow {workflow_id} cannot be recovered (status: {workflow.status})"

        try:
            # 获取恢复信息
            recovery_info = self.get_recovery_info(workflow_id)

            # 标记为恢复中
            self.persistence.update_workflow_status(workflow_id, "recovering")

            logger.info(f"Recovering workflow {workflow_id}")

            # 如果有策略层，尝试从断点恢复执行
            if self.strategy_layer:
                # 找到需要恢复执行的步骤索引
                plan_steps = workflow.plan.get("plan", {}).get("steps", []) if workflow.plan else []
                resume_index = self._get_resume_index(workflow, plan_steps)

                if resume_index >= 0:
                    logger.info(f"Resuming workflow {workflow_id} from step {resume_index}")
                    # 这里会调用策略层的恢复方法
                    # 实际恢复逻辑在策略层中实现
                    return True, f"Workflow {workflow_id} recovery initiated from step {resume_index}"

            return True, f"Workflow {workflow_id} recovery info prepared"

        except Exception as e:
            error_msg = f"Failed to recover workflow {workflow_id}: {e}"
            logger.error(error_msg)
            self.persistence.update_workflow_status(workflow_id, "failed", error_msg)
            return False, error_msg

    def get_recovery_info(self, workflow_id: str) -> Optional[RecoveryInfo]:
        """
        获取恢复信息

        Args:
            workflow_id: 工作流ID

        Returns:
            恢复信息对象
        """
        workflow = self.persistence.load(workflow_id)
        if not workflow:
            return None

        return RecoveryInfo(workflow)

    def _can_skip_step(self, step_id: str, step_result: Any) -> bool:
        """
        判断步骤是否可以跳过

        已完成的步骤可以跳过，避免重复执行

        Args:
            step_id: 步骤ID
            step_result: 步骤结果

        Returns:
            是否可以跳过
        """
        if not isinstance(step_result, dict):
            return False

        # 如果步骤标记为已完成，可以跳过
        if step_result.get("status") == "completed":
            return True

        # 如果步骤有结果且没有错误，可以跳过
        if "result" in step_result and "error" not in step_result:
            return True

        # 如果步骤有明确的 completed_at 时间戳，可以跳过
        if step_result.get("completed_at"):
            return True

        return False

    def _get_resume_index(self, workflow: WorkflowState, plan_steps: List[Dict]) -> int:
        """
        获取恢复执行的步骤索引

        Args:
            workflow: 工作流状态
            plan_steps: 计划步骤列表

        Returns:
            恢复执行的步骤索引，-1表示不需要恢复
        """
        if not plan_steps:
            return -1

        # 找到第一个未完成的步骤
        for i, step in enumerate(plan_steps):
            step_id = step.get("id", f"step_{i}")

            if step_id in workflow.step_results:
                step_result = workflow.step_results[step_id]
                if self._can_skip_step(step_id, step_result):
                    continue

            return i

        # 所有步骤都已完成
        return -1

    def get_skippable_steps(self, workflow_id: str) -> List[str]:
        """
        获取可以跳过的步骤列表

        Args:
            workflow_id: 工作流ID

        Returns:
            可跳过的步骤ID列表
        """
        workflow = self.persistence.load(workflow_id)
        if not workflow:
            return []

        skippable = []
        for step_id, result in workflow.step_results.items():
            if self._can_skip_step(step_id, result):
                skippable.append(step_id)

        return skippable

    async def mark_step_completed(
        self,
        workflow_id: str,
        step_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        标记步骤为已完成

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            result: 步骤结果

        Returns:
            是否成功
        """
        result_with_status = result.copy()
        result_with_status["status"] = "completed"
        result_with_status["completed_at"] = datetime.now().isoformat()

        return self.persistence.update_step(workflow_id, step_id, result_with_status)

    async def mark_step_failed(
        self,
        workflow_id: str,
        step_id: str,
        error: str
    ) -> bool:
        """
        标记步骤为失败

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            error: 错误信息

        Returns:
            是否成功
        """
        result = {
            "status": "failed",
            "error": error,
            "failed_at": datetime.now().isoformat()
        }

        return self.persistence.update_step(workflow_id, step_id, result)

    def list_recoverable_workflows(self) -> List[Dict[str, Any]]:
        """
        列出所有可恢复的工作流

        Returns:
            可恢复工作流列表
        """
        recoverable_statuses = {"failed", "running", "executing"}
        recoverable = []

        for workflow in self.persistence.list_all():
            if workflow.status in recoverable_statuses:
                info = RecoveryInfo(workflow)
                recoverable.append(info.to_dict())

        return recoverable

    def get_workflow_summary(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流摘要

        Args:
            workflow_id: 工作流ID

        Returns:
            工作流摘要
        """
        workflow = self.persistence.load(workflow_id)
        if not workflow:
            return None

        return {
            "workflow_id": workflow.workflow_id,
            "status": workflow.status,
            "current_step": workflow.current_step,
            "total_steps": len(workflow.step_results),
            "completed_steps": len(workflow.get_completed_steps()),
            "failed_steps": len(workflow.get_failed_steps()),
            "progress_percentage": self._calculate_progress(workflow),
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
            "error": workflow.error
        }

    def _calculate_progress(self, workflow: WorkflowState) -> int:
        """
        计算工作流进度百分比

        Args:
            workflow: 工作流状态

        Returns:
            进度百分比 (0-100)
        """
        plan_steps = workflow.plan.get("plan", {}).get("steps", []) if workflow.plan else []
        if not plan_steps:
            return 0

        completed = len(workflow.get_completed_steps())
        total = len(plan_steps)

        return int((completed / total) * 100) if total > 0 else 0


# 全局恢复管理器实例
_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager(
    persistence: Optional[WorkflowPersistence] = None,
    strategy_layer = None
) -> RecoveryManager:
    """
    获取全局恢复管理器实例

    Args:
        persistence: 持久化实例
        strategy_layer: 策略层实例

    Returns:
        RecoveryManager 实例
    """
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager(persistence, strategy_layer)
    return _recovery_manager


def reset_recovery_manager():
    """重置全局恢复管理器实例（主要用于测试）"""
    global _recovery_manager
    _recovery_manager = None
