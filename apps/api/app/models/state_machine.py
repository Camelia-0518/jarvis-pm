"""统一状态机层

消除散落在各 endpoint 中的裸 .status = "string" 赋值，将所有状态流转规则集中定义。

用法:
    from app.models.state_machine import project_sm, prd_sm, annotation_sm, task_sm

    # 验证 + 执行流转
    project_sm.transition(project, "archived")

    # 仅验证（不修改）
    if project_sm.can_transition(project.status, "archived"):
        ...

    # 获取合法下一态列表
    next_states = prd_sm.allowed_transitions(prd.status)

设计原则:
    - 每个状态机定义完整的流转图（from -> {to}）
    - transition() 验证失败时抛出 AppException(400)
    - 状态机不拥有副作用（副作用留在 endpoint 中处理）
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Set

from app.core.exceptions import AppException


class StateMachine:
    """通用状态机基类。

    transitions: {from_status: {valid_to_statuses}}
    """

    transitions: Dict[str, FrozenSet[str]] = {}
    status_attr: str = "status"

    @classmethod
    def can_transition(cls, from_status: str | None, to_status: str) -> bool:
        """检查是否可以从 from_status 转换到 to_status。"""
        if from_status is None:
            from_status = cls._default_state()
        # 同状态视为合法（幂等）
        if from_status == to_status:
            return True
        allowed = cls.transitions.get(from_status, frozenset())
        return to_status in allowed

    @classmethod
    def allowed_transitions(cls, from_status: str | None) -> Set[str]:
        """返回从 from_status 出发的所有合法下一态。"""
        if from_status is None:
            from_status = cls._default_state()
        return set(cls.transitions.get(from_status, frozenset()))

    @classmethod
    def transition(cls, entity: Any, to_status: str) -> None:
        """验证并执行状态流转。

        验证失败时抛出 AppException(400)；成功时设置 entity.<status_attr> = to_status。

        Args:
            entity: 模型实例（必须有 status 属性或 status_attr 指定的属性）
            to_status: 目标状态

        Raises:
            AppException: 非法状态流转
        """
        from_status = getattr(entity, cls.status_attr, None)
        if from_status is None:
            from_status = cls._default_state()

        if not cls.can_transition(from_status, to_status):
            entity_name = getattr(entity, "__class__", type(entity)).__name__
            raise AppException(
                f"无效的状态流转: {entity_name} 不能从 '{from_status}' 转换为 '{to_status}'",
                code="INVALID_STATE_TRANSITION",
                status_code=400,
            )

        setattr(entity, cls.status_attr, to_status)

    @classmethod
    def _default_state(cls) -> str:
        """默认初始状态，子类可覆盖。"""
        return ""


# =============================================================================
# Project 状态机
# =============================================================================

class ProjectStateMachine(StateMachine):
    """Project 状态流转:

    active ──→ archived ──→ deleted
      ↑__________|       ↑________|

    - active ↔ archived（可双向）
    - active/archived → deleted（任意非终态可直接删除）
    - deleted 为终态，不可再转换
    """

    transitions = {
        "active": frozenset({"active", "archived", "deleted"}),
        "archived": frozenset({"active", "archived", "deleted"}),
        "deleted": frozenset(),  # 终态
    }

    @classmethod
    def _default_state(cls) -> str:
        return "active"


# =============================================================================
# PRD 状态机
# =============================================================================

class PRDStateMachine(StateMachine):
    """PRD 状态流转:

    draft → review → approved → published → implemented
      ↑        ↓         ↓            ↓
      └────────┴─────────┴────────────┘  （任意态可回退到 draft）

    - 正向流转必须按序（draft→review→approved→published→implemented）
    - 任意状态可回到 draft（重新编辑）
    - implemented 为终态
    """

    transitions = {
        "draft": frozenset({"draft", "review"}),
        "review": frozenset({"review", "approved", "draft"}),
        "approved": frozenset({"approved", "published", "draft"}),
        "published": frozenset({"published", "implemented", "draft"}),
        "implemented": frozenset({"implemented"}),  # 终态
    }

    @classmethod
    def _default_state(cls) -> str:
        return "draft"


# =============================================================================
# Annotation 状态机
# =============================================================================

class AnnotationStateMachine(StateMachine):
    """Annotation 状态流转:

    open → resolved / dismissed
      ↑___________|              （resolved/dismissed 可重新打开）

    - open → resolved: 问题已解决
    - open → dismissed: 问题已驳回
    - resolved → open: 重新打开
    - dismissed → open: 重新打开
    """

    transitions = {
        "open": frozenset({"open", "resolved", "dismissed"}),
        "resolved": frozenset({"resolved", "open"}),
        "dismissed": frozenset({"dismissed", "open"}),
    }

    @classmethod
    def _default_state(cls) -> str:
        return "open"


# =============================================================================
# RevisionTask 状态机
# =============================================================================

class RevisionTaskStateMachine(StateMachine):
    """RevisionTask 状态流转:

    todo → in_progress → done
      ↓                    ↓
      └──→ cancelled ←────┘

    - todo → in_progress: 开始执行
    - in_progress → done: 完成
    - todo / in_progress → cancelled: 取消
    - done 为终态（不可逆，已完成的任务不能回到进行中）
    - cancelled 允许重新激活为 todo
    """

    transitions = {
        "todo": frozenset({"todo", "in_progress", "cancelled"}),
        "in_progress": frozenset({"in_progress", "done", "cancelled"}),
        "done": frozenset({"done"}),  # 终态
        "cancelled": frozenset({"cancelled", "todo"}),  # 可重新激活
    }

    @classmethod
    def _default_state(cls) -> str:
        return "todo"


# =============================================================================
# 模块级便捷实例
# =============================================================================

project_sm = ProjectStateMachine
prd_sm = PRDStateMachine
annotation_sm = AnnotationStateMachine
task_sm = RevisionTaskStateMachine
