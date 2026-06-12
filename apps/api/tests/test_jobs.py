"""Job query endpoint tests"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobType, JobStatus

SINGLE_USER_ID = "single-user"


@pytest.mark.integration
async def test_list_jobs_empty(async_client: AsyncClient):
    """GET /jobs returns empty list when no jobs exist."""
    response = await async_client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


@pytest.mark.integration
async def test_list_jobs_with_data(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_project,
):
    """GET /jobs returns jobs filtered by project_id."""
    job = Job(
        job_type=JobType.GENERAL,
        status=JobStatus.SUCCEEDED,
        project_id=sample_project.id,
        triggered_by=SINGLE_USER_ID,
        duration_ms=150,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/jobs?project_id={sample_project.id}")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 1
    assert any(j["id"] == job.id for j in items)


@pytest.mark.integration
async def test_get_job_detail(async_client: AsyncClient, db_session: AsyncSession):
    """GET /jobs/{id} returns full job detail."""
    job = Job(
        job_type=JobType.COMPLIANCE_CHECK,
        status=JobStatus.FAILED,
        triggered_by=SINGLE_USER_ID,
        error_message="LLM timeout",
        duration_ms=3000,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == job.id
    assert data["status"] == "failed"
    assert data["error_message"] == "LLM timeout"
    assert data["duration_ms"] == 3000


@pytest.mark.integration
async def test_get_job_not_found(async_client: AsyncClient):
    """GET /jobs/{id} for nonexistent job returns 404."""
    response = await async_client.get("/api/v1/jobs/nonexistent")
    assert response.status_code == 404


@pytest.mark.integration
async def test_job_failure_type_in_response(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Job detail should include failure_type and retryable flag."""
    from app.models.job import FailureType
    job = Job(
        job_type=JobType.COMPLIANCE_CHECK,
        status=JobStatus.FAILED,
        failure_type=FailureType.SYSTEM,
        error_code="LLM_TIMEOUT",
        error_message="Request timed out after 30s",
        triggered_by=SINGLE_USER_ID,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["failure_type"] == "system"
    assert data["error_code"] == "LLM_TIMEOUT"
    assert data["retryable"] is True


@pytest.mark.integration
async def test_retry_system_failure_job(
    async_client: AsyncClient, db_session: AsyncSession
):
    """POST /jobs/{id}/retry should reset system-failed job to queued."""
    from app.models.job import FailureType
    job = Job(
        job_type=JobType.COMPLIANCE_CHECK,
        status=JobStatus.FAILED,
        failure_type=FailureType.SYSTEM,
        attempt=1,
        max_attempts=3,
        triggered_by=SINGLE_USER_ID,
        error_message="Timeout",
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.post(f"/api/v1/jobs/{job.id}/retry")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["attempt"] == 2
    assert data["backoff_seconds"] in (1, 5, 30)


@pytest.mark.integration
async def test_retry_business_failure_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """POST /jobs/{id}/retry should reject business failures."""
    from app.models.job import FailureType
    job = Job(
        job_type=JobType.COMPLIANCE_CHECK,
        status=JobStatus.FAILED,
        failure_type=FailureType.BUSINESS,
        attempt=1,
        max_attempts=3,
        triggered_by=SINGLE_USER_ID,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.post(f"/api/v1/jobs/{job.id}/retry")
    assert response.status_code == 400
    assert "NOT_RETRYABLE" in response.text


@pytest.mark.integration
async def test_retry_exceeded_max_attempts(
    async_client: AsyncClient, db_session: AsyncSession
):
    """POST /jobs/{id}/retry should reject when max attempts reached."""
    from app.models.job import FailureType
    job = Job(
        job_type=JobType.COMPLIANCE_CHECK,
        status=JobStatus.FAILED,
        failure_type=FailureType.SYSTEM,
        attempt=3,
        max_attempts=3,
        triggered_by=SINGLE_USER_ID,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.post(f"/api/v1/jobs/{job.id}/retry")
    assert response.status_code == 400


# ============== Cross-User Isolation ==========

OTHER_USER_ID = "other-user"


@pytest.mark.integration
async def test_cannot_get_other_user_job(
    async_client: AsyncClient, db_session: AsyncSession
):
    """GET /jobs/{id} should return 404 for another user's job."""
    job = Job(
        job_type=JobType.GENERAL,
        status=JobStatus.SUCCEEDED,
        triggered_by=OTHER_USER_ID,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_cannot_retry_other_user_job(
    async_client: AsyncClient, db_session: AsyncSession
):
    """POST /jobs/{id}/retry should return 404 for another user's job."""
    from app.models.job import FailureType
    job = Job(
        job_type=JobType.COMPLIANCE_CHECK,
        status=JobStatus.FAILED,
        failure_type=FailureType.SYSTEM,
        attempt=1,
        max_attempts=3,
        triggered_by=OTHER_USER_ID,
    )
    db_session.add(job)
    await db_session.commit()

    response = await async_client.post(f"/api/v1/jobs/{job.id}/retry")
    assert response.status_code == 404


@pytest.mark.integration
async def test_list_jobs_excludes_other_users(
    async_client: AsyncClient, db_session: AsyncSession
):
    """GET /jobs should not include other users' jobs."""
    own = Job(
        job_type=JobType.GENERAL,
        status=JobStatus.SUCCEEDED,
        triggered_by=SINGLE_USER_ID,
    )
    other = Job(
        job_type=JobType.GENERAL,
        status=JobStatus.SUCCEEDED,
        triggered_by=OTHER_USER_ID,
    )
    db_session.add_all([own, other])
    await db_session.commit()

    response = await async_client.get("/api/v1/jobs")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    own_ids = {j["id"] for j in items}
    assert own.id in own_ids
    assert other.id not in own_ids
