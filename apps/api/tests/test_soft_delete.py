"""契约测试：软删除语义（内联创建，避免 fixture 隔离问题）"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.prd_revision_task import PRDRevisionTask, TaskStatus

SINGLE_USER_ID = "single-user"


@pytest.mark.integration
async def test_deleted_annotation_not_in_list(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd
):
    """删除批注后列表不再包含"""
    ann = PRDAnnotation(
        prd_id=sample_prd.id, content="To Delete",
        annotation_type=AnnotationType.COMMENT, status=AnnotationStatus.OPEN,
        created_by=SINGLE_USER_ID,
    )
    db_session.add(ann)
    await db_session.commit()

    r = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations")
    total_before = r.json()["data"]["total"]

    await async_client.delete(f"/api/v1/prds/{sample_prd.id}/annotations/{ann.id}")

    r = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations")
    assert r.json()["data"]["total"] == total_before - 1


@pytest.mark.integration
async def test_deleted_annotation_exists_in_db(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd
):
    """软删除后记录仍在 DB"""
    ann = PRDAnnotation(
        prd_id=sample_prd.id, content="Soft Delete Test",
        annotation_type=AnnotationType.COMMENT, status=AnnotationStatus.OPEN,
        created_by=SINGLE_USER_ID,
    )
    db_session.add(ann)
    await db_session.commit()

    await async_client.delete(f"/api/v1/prds/{sample_prd.id}/annotations/{ann.id}")

    result = await db_session.execute(select(PRDAnnotation).where(PRDAnnotation.id == ann.id))
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.deleted_at is not None


@pytest.mark.integration
async def test_deleted_task_not_redeleteable(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd
):
    """删除后不可再删"""
    task = PRDRevisionTask(
        id=f"tdel-{uuid.uuid4().hex[:8]}", prd_id=sample_prd.id,
        title="To Delete", status=TaskStatus.TODO, created_by=SINGLE_USER_ID,
    )
    db_session.add(task)
    await db_session.commit()

    assert (await async_client.delete(f"/api/v1/prds/{sample_prd.id}/revision-tasks/{task.id}")).status_code == 200
    assert (await async_client.delete(f"/api/v1/prds/{sample_prd.id}/revision-tasks/{task.id}")).status_code == 404
