# -*- coding: utf-8 -*-
"""
检查点控制器模块

提供人机协作检查点机制，支持暂停、继续、修改、跳过、重试等操作。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio


class CheckpointAction(Enum):
    """检查点操作类型"""
    RESUME = "resume"      # 继续执行
    MODIFY = "modify"      # 修改后继续
    SKIP = "skip"          # 跳过此步骤
    RETRY = "retry"        # 重试当前步骤


@dataclass
class Checkpoint:
    """检查点数据类"""
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
        self._workflow_checkpoints: Dict[str, List[str]] = {}
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
        config = self.CHECKPOINTS_CONFIG.get(checkpoint_id, {}).copy()
        if config_override:
            config.update(config_override)

        checkpoint = Checkpoint(
            id=f"{workflow_id}_{checkpoint_id}_{datetime.now().strftime('%H%M%S')}",
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

    async def resume(self, workflow_id: str, checkpoint_id: str) -> bool:
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
    ) -> bool:
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

    async def skip(self, workflow_id: str, checkpoint_id: str) -> bool:
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

    async def retry(self, workflow_id: str, checkpoint_id: str) -> bool:
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

    def get_workflow_checkpoints(self, workflow_id: str) -> List[Checkpoint]:
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
            "editable_fields": self.CHECKPOINTS_CONFIG.get(checkpoint.id.split("_")[1], {}).get("editable_fields", [])
        }


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


# 全局检查点控制器实例
checkpoint_controller = CheckpointController()
