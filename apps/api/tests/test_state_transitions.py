"""契约测试：状态流转规则

验证所有状态机的合法/非法转换，确保:
  - 合法流转被接受（200）
  - 非法流转被拒绝（400）
  - 终态不可再转出
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.models.prd import PRD, PRDStatus
from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.prd_revision_task import PRDRevisionTask, TaskStatus
from app.models.state_machine import (
    project_sm, prd_sm, annotation_sm, task_sm,
)

SINGLE_USER_ID = "single-user"


# ============== Project 状态机 ==============

class TestProjectStateMachine:
    """active ↔ archived → deleted (terminal)"""

    def test_legal_transitions(self):
        """合法转换"""
        assert project_sm.can_transition("active", "archived") is True
        assert project_sm.can_transition("archived", "active") is True
        assert project_sm.can_transition("archived", "deleted") is True

    def test_idempotent(self):
        """同状态转换合法"""
        assert project_sm.can_transition("active", "active") is True
        assert project_sm.can_transition("archived", "archived") is True

    def test_terminal_state(self):
        """deleted 是终态"""
        assert project_sm.can_transition("deleted", "active") is False
        assert project_sm.can_transition("deleted", "archived") is False

    def test_delete_from_active(self):
        """active 可以直接删除"""
        assert project_sm.can_transition("active", "deleted") is True

    def test_allowed_transitions(self):
        """allowed_transitions 返回正确的下一态集合"""
        assert project_sm.allowed_transitions("active") == {"active", "archived", "deleted"}
        assert project_sm.allowed_transitions("archived") == {"active", "archived", "deleted"}
        assert project_sm.allowed_transitions("deleted") == set()


# ============== PRD 状态机 ==============

class TestPRDStateMachine:
    """draft → review → approved → published → implemented (可回退到 draft)"""

    def test_forward_flow(self):
        """正向流转"""
        assert prd_sm.can_transition("draft", "review") is True
        assert prd_sm.can_transition("review", "approved") is True
        assert prd_sm.can_transition("approved", "published") is True
        assert prd_sm.can_transition("published", "implemented") is True

    def test_fallback_to_draft(self):
        """任意状态可回退到 draft"""
        assert prd_sm.can_transition("review", "draft") is True
        assert prd_sm.can_transition("approved", "draft") is True
        assert prd_sm.can_transition("published", "draft") is True

    def test_terminal_state(self):
        """implemented 是终态"""
        assert prd_sm.can_transition("implemented", "draft") is False
        assert prd_sm.can_transition("implemented", "review") is False

    def test_illegal_skip(self):
        """不能跳步"""
        assert prd_sm.can_transition("draft", "approved") is False
        assert prd_sm.can_transition("draft", "published") is False
        assert prd_sm.can_transition("review", "published") is False


# ============== Annotation 状态机 ==============

class TestAnnotationStateMachine:
    """open → resolved / dismissed (可重新打开)"""

    def test_legal_transitions(self):
        assert annotation_sm.can_transition("open", "resolved") is True
        assert annotation_sm.can_transition("open", "dismissed") is True
        assert annotation_sm.can_transition("resolved", "open") is True
        assert annotation_sm.can_transition("dismissed", "open") is True

    def test_illegal_transitions(self):
        """resolved 不能直接变 dismissed"""
        assert annotation_sm.can_transition("resolved", "dismissed") is False
        assert annotation_sm.can_transition("dismissed", "resolved") is False


# ============== RevisionTask 状态机 ==============

class TestRevisionTaskStateMachine:
    """todo → in_progress → done (terminal) / cancelled → todo"""

    def test_forward_flow(self):
        assert task_sm.can_transition("todo", "in_progress") is True
        assert task_sm.can_transition("in_progress", "done") is True

    def test_cancel_and_reactivate(self):
        assert task_sm.can_transition("todo", "cancelled") is True
        assert task_sm.can_transition("in_progress", "cancelled") is True
        assert task_sm.can_transition("cancelled", "todo") is True

    def test_terminal_state(self):
        """done 是终态"""
        assert task_sm.can_transition("done", "todo") is False
        assert task_sm.can_transition("done", "in_progress") is False
        assert task_sm.can_transition("done", "cancelled") is False

    def test_illegal_skip(self):
        """不能从 todo 直接跳到 done"""
        assert task_sm.can_transition("todo", "done") is False


# ============== API 级别验证 ==============

@pytest.mark.integration
async def test_annotation_illegal_transition_rejected(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_prd: PRD,
):
    """尝试 resolved → dismissed 应被拒绝"""
    ann = PRDAnnotation(
        prd_id=sample_prd.id,
        content="Test",
        annotation_type=AnnotationType.ISSUE,
        status=AnnotationStatus.RESOLVED,
        created_by=SINGLE_USER_ID,
    )
    db_session.add(ann)
    await db_session.commit()

    response = await async_client.put(
        f"/api/v1/prds/{sample_prd.id}/annotations/{ann.id}",
        json={"status": "dismissed"},
    )
    assert response.status_code == 400
