"""PRD annotation endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.prd_annotation import PRDAnnotation, AnnotationStatus, AnnotationType
from app.models.prd import PRD


# ============== Create ==============

@pytest.mark.integration
async def test_create_annotation_success(async_client: AsyncClient, sample_prd: PRD):
    """POST /api/v1/prds/{id}/annotations should create a new annotation."""
    payload = {
        "chapter_num": "2",
        "chapter_title": "Requirements",
        "line_index": 10,
        "selected_text": "user login",
        "content": "Need to clarify login method",
        "annotation_type": "question",
    }
    response = await async_client.post(f"/api/v1/prds/{sample_prd.id}/annotations", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "id" in data["data"]


@pytest.mark.integration
async def test_create_annotation_minimal(async_client: AsyncClient, sample_prd: PRD):
    """POST should work with minimal required fields."""
    payload = {"content": "Simple comment"}
    response = await async_client.post(f"/api/v1/prds/{sample_prd.id}/annotations", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


@pytest.mark.integration
async def test_create_annotation_empty_content(async_client: AsyncClient, sample_prd: PRD):
    """POST should reject empty content."""
    payload = {"content": ""}
    response = await async_client.post(f"/api/v1/prds/{sample_prd.id}/annotations", json=payload)
    assert response.status_code == 422


# ============== List ==============

@pytest.mark.integration
async def test_list_annotations_empty(async_client: AsyncClient, sample_prd: PRD):
    """GET /api/v1/prds/{id}/annotations should return empty list."""
    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_list_annotations_with_data(async_client: AsyncClient, sample_annotation: PRDAnnotation):
    """GET should return created annotations."""
    response = await async_client.get(f"/api/v1/prds/{sample_annotation.prd_id}/annotations")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["id"] == sample_annotation.id
    assert data["data"]["items"][0]["content"] == sample_annotation.content


@pytest.mark.integration
async def test_list_annotations_filter_by_status(async_client: AsyncClient, db_session: AsyncSession, sample_prd: PRD):
    """GET should filter by status."""
    # Create resolved annotation
    ann = PRDAnnotation(
        prd_id=sample_prd.id,
        content="Resolved issue",
        annotation_type=AnnotationType.ISSUE,
        status=AnnotationStatus.RESOLVED,
        created_by="single-user",
    )
    db_session.add(ann)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations?status=resolved")
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1
    assert data["data"]["items"][0]["status"] == "resolved"


@pytest.mark.integration
async def test_list_annotations_filter_by_chapter(async_client: AsyncClient, sample_annotation: PRDAnnotation):
    """GET should filter by chapter_num."""
    response = await async_client.get(
        f"/api/v1/prds/{sample_annotation.prd_id}/annotations?chapter_num=1"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["data"]["total"] == 1

    response = await async_client.get(
        f"/api/v1/prds/{sample_annotation.prd_id}/annotations?chapter_num=99"
    )
    data = response.json()
    assert data["data"]["total"] == 0


@pytest.mark.integration
async def test_list_annotations_pagination(async_client: AsyncClient, db_session: AsyncSession, sample_prd: PRD):
    """GET should respect limit and offset."""
    for i in range(3):
        ann = PRDAnnotation(
            prd_id=sample_prd.id,
            content=f"Annotation {i + 1}",
            annotation_type=AnnotationType.COMMENT,
            status=AnnotationStatus.OPEN,
            created_by="single-user",
        )
        db_session.add(ann)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total"] == 3
    assert len(data["data"]["items"]) == 2


# ============== Update ==============

@pytest.mark.integration
async def test_update_annotation_content(async_client: AsyncClient, sample_annotation: PRDAnnotation):
    """PUT should update annotation content."""
    payload = {"content": "Updated comment text"}
    response = await async_client.put(
        f"/api/v1/prds/{sample_annotation.prd_id}/annotations/{sample_annotation.id}",
        json=payload,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


@pytest.mark.integration
async def test_update_annotation_status_resolved(async_client: AsyncClient, sample_annotation: PRDAnnotation):
    """PUT should update status to resolved."""
    payload = {"status": "resolved"}
    response = await async_client.put(
        f"/api/v1/prds/{sample_annotation.prd_id}/annotations/{sample_annotation.id}",
        json=payload,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


@pytest.mark.integration
async def test_update_annotation_not_found(async_client: AsyncClient, sample_prd: PRD):
    """PUT should return error for non-existent annotation."""
    payload = {"content": "Updated"}
    response = await async_client.put(
        f"/api/v1/prds/{sample_prd.id}/annotations/non-existent-id",
        json=payload,
    )
    assert response.status_code == 404  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


# ============== Delete ==============

@pytest.mark.integration
async def test_delete_annotation_success(async_client: AsyncClient, sample_annotation: PRDAnnotation, db_session: AsyncSession):
    """DELETE should remove the annotation."""
    response = await async_client.delete(
        f"/api/v1/prds/{sample_annotation.prd_id}/annotations/{sample_annotation.id}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    # Verify soft deletion — record still exists but deleted_at is set
    result = await db_session.execute(
        select(PRDAnnotation).where(PRDAnnotation.id == sample_annotation.id)
    )
    annotation = result.scalar_one_or_none()
    assert annotation is not None
    assert annotation.deleted_at is not None


@pytest.mark.integration
async def test_delete_annotation_not_found(async_client: AsyncClient, sample_prd: PRD):
    """DELETE should return error for non-existent annotation."""
    response = await async_client.delete(
        f"/api/v1/prds/{sample_prd.id}/annotations/non-existent-id"
    )
    assert response.status_code in (400, 404)  # Returns proper HTTP error status

    data = response.json()
    assert data["success"] is False


# ============== Stats ==============

@pytest.mark.integration
async def test_get_annotation_stats(async_client: AsyncClient, db_session: AsyncSession, sample_prd: PRD):
    """GET /stats should return annotation counts by status."""
    # Create annotations with different statuses
    for status in [AnnotationStatus.OPEN, AnnotationStatus.RESOLVED, AnnotationStatus.DISMISSED]:
        ann = PRDAnnotation(
            prd_id=sample_prd.id,
            content=f"{status.value} annotation",
            annotation_type=AnnotationType.COMMENT,
            status=status,
            created_by="single-user",
        )
        db_session.add(ann)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/prds/{sample_prd.id}/annotations/stats")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["open"] == 1
    assert data["data"]["resolved"] == 1
    assert data["data"]["dismissed"] == 1
    assert data["data"]["total"] == 3