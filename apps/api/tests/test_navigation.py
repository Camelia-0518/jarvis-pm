"""契约测试：API 级跨资源导航（内联创建）"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.prd_revision_task import PRDRevisionTask, TaskStatus

SINGLE_USER_ID = "single-user"


@pytest.mark.integration
async def test_prd_annotations_navigation(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd
):
    """从 PRD 查询关联批注"""
    ann = PRDAnnotation(
        prd_id=sample_prd.id, content="Nav test",
        annotation_type=AnnotationType.COMMENT, status=AnnotationStatus.OPEN,
        created_by=SINGLE_USER_ID,
    )
    db_session.add(ann)
    await db_session.commit()

    r = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations")
    assert r.status_code == 200
    assert any(a["id"] == ann.id for a in r.json()["data"]["items"])


@pytest.mark.integration
async def test_prd_tasks_navigation(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd
):
    """从 PRD 查询关联任务"""
    task = PRDRevisionTask(
        id=f"ntask-{uuid.uuid4().hex[:8]}", prd_id=sample_prd.id,
        title="Nav Task", status=TaskStatus.TODO, created_by=SINGLE_USER_ID,
    )
    db_session.add(task)
    await db_session.commit()

    r = await async_client.get(f"/api/v1/prds/{sample_prd.id}/revision-tasks")
    assert r.status_code == 200
    assert any(t["id"] == task.id for t in r.json()["data"])
