"""契约测试：跨用户资源隔离

核心验证：用户不能访问/操作属于其他用户的资源。
使用内联创建确保 DB 隔离可靠性。
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prd import PRD
from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.template import Template
from app.models.prd_revision_task import PRDRevisionTask, TaskStatus
from app.models.prd_comment import PRDComment

SINGLE_USER_ID = "single-user"
OTHER_USER_ID = "other-user"


@pytest.mark.integration
async def test_cannot_access_nonexistent_prd(async_client: AsyncClient):
    """不存在的 PRD 应返回 404"""
    response = await async_client.get(f"/prds/nonexistent-{uuid.uuid4().hex}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_cannot_delete_others_annotation(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd: PRD
):
    """他人的批注不可删除（404）"""
    ann = PRDAnnotation(
        prd_id=sample_prd.id, content="Other's", annotation_type=AnnotationType.COMMENT,
        status=AnnotationStatus.OPEN, created_by=OTHER_USER_ID,
    )
    db_session.add(ann)
    await db_session.commit()
    response = await async_client.delete(f"/api/v1/prds/{sample_prd.id}/annotations/{ann.id}")
    assert response.status_code in (403, 404)


@pytest.mark.integration
async def test_cannot_update_others_template(
    async_client: AsyncClient, db_session: AsyncSession
):
    """非内置模板只能由创建者编辑 → 403"""
    tmpl = Template(
        id=f"otmpl-{uuid.uuid4().hex[:8]}", name="Other's",
        industry="saas", is_builtin=False, created_by=OTHER_USER_ID,
    )
    db_session.add(tmpl)
    await db_session.commit()
    response = await async_client.put(f"/api/v1/templates/{tmpl.id}", json={"name": "Hacked"})
    assert response.status_code == 403


@pytest.mark.integration
async def test_cannot_delete_others_task(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd: PRD
):
    """他人的任务不可删除 → 404"""
    task = PRDRevisionTask(
        id=f"ot-{uuid.uuid4().hex[:8]}", prd_id=sample_prd.id,
        title="Other's Task", status=TaskStatus.TODO, created_by=OTHER_USER_ID,
    )
    db_session.add(task)
    await db_session.commit()
    response = await async_client.delete(f"/prds/{sample_prd.id}/revision-tasks/{task.id}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_cannot_delete_others_comment(
    async_client: AsyncClient, db_session: AsyncSession, sample_prd: PRD
):
    """他人的评论不可删除 → 404"""
    comment = PRDComment(
        id=f"oc-{uuid.uuid4().hex[:8]}", prd_id=sample_prd.id,
        chapter_id="1", content="Other's", created_by=OTHER_USER_ID,
    )
    db_session.add(comment)
    await db_session.commit()
    response = await async_client.delete(f"/prds/{sample_prd.id}/comments/{comment.id}")
    assert response.status_code == 404
