#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Persistence - 工作流持久化模块

提供工作流状态的持久化存储，支持故障恢复和断点续传
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """
    工作流状态数据类

    Attributes:
        workflow_id: 工作流唯一标识
        status: 工作流状态 (pending/running/completed/failed)
        current_step: 当前执行的步骤ID
        step_results: 各步骤的执行结果
        user_input: 用户原始输入
        intent_result: 意图识别结果
        plan: 执行计划
        created_at: 创建时间
        updated_at: 更新时间
        error: 错误信息（如果有）
    """
    workflow_id: str
    status: str = "pending"
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = field(default_factory=dict)
    user_input: str = ""
    intent_result: Optional[Dict] = None
    plan: Optional[Dict] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowState":
        """从字典创建实例"""
        return cls(**data)

    def get_completed_steps(self) -> List[str]:
        """获取已完成的步骤列表"""
        completed = []
        for step_id, result in self.step_results.items():
            if isinstance(result, dict) and result.get("status") == "completed":
                completed.append(step_id)
            elif isinstance(result, dict) and "error" not in result:
                completed.append(step_id)
        return completed

    def get_failed_steps(self) -> List[str]:
        """获取失败的步骤列表"""
        failed = []
        for step_id, result in self.step_results.items():
            if isinstance(result, dict) and result.get("status") == "failed":
                failed.append(step_id)
            elif isinstance(result, dict) and result.get("error"):
                failed.append(step_id)
        return failed

    def is_step_completed(self, step_id: str) -> bool:
        """检查步骤是否已完成"""
        if step_id not in self.step_results:
            return False
        result = self.step_results[step_id]
        if isinstance(result, dict):
            return result.get("status") == "completed" or "error" not in result
        return True


class WorkflowPersistence:
    """
    工作流持久化管理器

    负责工作流状态的保存、加载和管理
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化持久化管理器

        Args:
            storage_dir: 存储目录路径，默认为 ~/.jarvis/workflows
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            home_dir = Path.home()
            self.storage_dir = home_dir / ".jarvis" / "workflows"

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._workflows: Dict[str, WorkflowState] = {}
        self._load_all_workflows()

    def _get_file_path(self, workflow_id: str) -> Path:
        """
        获取工作流状态文件路径

        Args:
            workflow_id: 工作流ID

        Returns:
            文件路径
        """
        return self.storage_dir / f"{workflow_id}.json"

    def save(self, workflow: WorkflowState) -> bool:
        """
        保存工作流状态到JSON文件

        Args:
            workflow: 工作流状态对象

        Returns:
            是否保存成功
        """
        try:
            workflow.updated_at = datetime.now().isoformat()
            file_path = self._get_file_path(workflow.workflow_id)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workflow.to_dict(), f, ensure_ascii=False, indent=2)

            self._workflows[workflow.workflow_id] = workflow
            logger.info(f"Workflow {workflow.workflow_id} saved to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save workflow {workflow.workflow_id}: {e}")
            return False

    def load(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        加载工作流状态

        Args:
            workflow_id: 工作流ID

        Returns:
            工作流状态对象，如果不存在则返回None
        """
        # 先检查内存缓存
        if workflow_id in self._workflows:
            return self._workflows[workflow_id]

        # 从文件加载
        file_path = self._get_file_path(workflow_id)
        if not file_path.exists():
            logger.warning(f"Workflow file not found: {file_path}")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            workflow = WorkflowState.from_dict(data)
            self._workflows[workflow_id] = workflow
            logger.info(f"Workflow {workflow_id} loaded from {file_path}")
            return workflow

        except Exception as e:
            logger.error(f"Failed to load workflow {workflow_id}: {e}")
            return None

    def update_step(
        self,
        workflow_id: str,
        step_id: str,
        result: Dict[str, Any],
        status: Optional[str] = None
    ) -> bool:
        """
        更新步骤结果

        Args:
            workflow_id: 工作流ID
            step_id: 步骤ID
            result: 步骤执行结果
            status: 步骤状态 (可选)

        Returns:
            是否更新成功
        """
        workflow = self.load(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found for step update")
            return False

        try:
            # 更新步骤结果
            workflow.step_results[step_id] = result
            workflow.current_step = step_id

            if status:
                workflow.status = status

            # 自动保存
            return self.save(workflow)

        except Exception as e:
            logger.error(f"Failed to update step {step_id} for workflow {workflow_id}: {e}")
            return False

    def update_workflow_status(
        self,
        workflow_id: str,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """
        更新工作流状态

        Args:
            workflow_id: 工作流ID
            status: 新状态
            error: 错误信息（可选）

        Returns:
            是否更新成功
        """
        workflow = self.load(workflow_id)
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found for status update")
            return False

        try:
            workflow.status = status
            if error:
                workflow.error = error

            return self.save(workflow)

        except Exception as e:
            logger.error(f"Failed to update status for workflow {workflow_id}: {e}")
            return False

    def list_active(self) -> List[WorkflowState]:
        """
        列出所有活跃工作流

        Returns:
            活跃工作流列表（状态为 pending 或 running）
        """
        active_statuses = {"pending", "running", "intent_classification", "planning", "executing"}
        active_workflows = []

        for workflow in self._workflows.values():
            if workflow.status in active_statuses:
                active_workflows.append(workflow)

        return active_workflows

    def list_all(self) -> List[WorkflowState]:
        """
        列出所有工作流

        Returns:
            所有工作流列表
        """
        return list(self._workflows.values())

    def cleanup_old(self, max_age_hours: int = 24) -> int:
        """
        清理过期工作流

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            清理的工作流数量
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0

        for workflow_id, workflow in list(self._workflows.items()):
            try:
                updated_at = datetime.fromisoformat(workflow.updated_at)
                if updated_at < cutoff_time and workflow.status in {"completed", "failed"}:
                    file_path = self._get_file_path(workflow_id)
                    if file_path.exists():
                        file_path.unlink()
                    del self._workflows[workflow_id]
                    cleaned_count += 1
                    logger.info(f"Cleaned up old workflow: {workflow_id}")
            except Exception as e:
                logger.error(f"Error cleaning up workflow {workflow_id}: {e}")

        return cleaned_count

    def delete(self, workflow_id: str) -> bool:
        """
        删除工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            是否删除成功
        """
        try:
            file_path = self._get_file_path(workflow_id)
            if file_path.exists():
                file_path.unlink()

            if workflow_id in self._workflows:
                del self._workflows[workflow_id]

            logger.info(f"Workflow {workflow_id} deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False

    def _load_all_workflows(self):
        """加载所有工作流状态到内存"""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    workflow = WorkflowState.from_dict(data)
                    self._workflows[workflow.workflow_id] = workflow

                except Exception as e:
                    logger.error(f"Error loading workflow from {file_path}: {e}")

            logger.info(f"Loaded {len(self._workflows)} workflows from {self.storage_dir}")

        except Exception as e:
            logger.error(f"Error loading workflows: {e}")


# 全局持久化实例
_persistence: Optional[WorkflowPersistence] = None


def get_persistence(storage_dir: Optional[str] = None) -> WorkflowPersistence:
    """
    获取全局持久化实例

    Args:
        storage_dir: 存储目录（可选）

    Returns:
        WorkflowPersistence 实例
    """
    global _persistence
    if _persistence is None:
        _persistence = WorkflowPersistence(storage_dir)
    return _persistence


def reset_persistence():
    """重置全局持久化实例（主要用于测试）"""
    global _persistence
    _persistence = None
