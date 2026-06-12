"""Delivery endpoints tests

Covers: generate, generate-single, list, get, update, delete, dashboard.
All agent calls are mocked — no real LLM requests in tests.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentResult
from app.models.delivery_plan import DeliveryPlan, DeliveryStatus
from app.models.project import Project, ProjectStatus


# ============== Helpers ==============

def _make_agent_result(success=True, output="", data=None, error=None):
    return AgentResult(success=success, output=output, data=data or {}, error=error)


def _fake_planner_result():
    return _make_agent_result(
        output="# Delivery Plan",
        data={
            "wbs": {"tasks": [{"id": "t1", "name": "Task 1", "effort_days": 3}], "total_tasks": 1, "total_effort_days": 3},
            "milestones": {"phases": [{"phase_id": "ph1", "name": "Phase 1"}], "total_weeks": 4},
            "resources": {"team_size": 5, "total_person_days": 30, "recommendation": "OK"},
            "gantt": {"items": [{"id": "g1", "name": "Dev"}], "total_days": 28, "start_date": "2026-06-01"},
        },
    )


def _fake_risk_result():
    return _make_agent_result(
        output="# Risk Analysis",
        data={
            "risks": [{"id": "r1", "risk": "Schedule risk", "risk_level": "高", "probability": 0.7, "impact": 0.8, "risk_score": 0.56}],
            "matrix": {"grid": {}, "summary": {}},
            "response_plan": {"top_risks": []},
        },
    )


def _fake_stakeholder_result():
    return _make_agent_result(
        output="# Stakeholder Plan",
        data={
            "stakeholders": [{"id": "s1", "role": "PM", "dept": "Engineering", "concern": "Timeline"}],
            "raci": {"activities": [], "roles": [], "assignments": {}, "total_activities": 0, "total_roles": 0},
            "communication_plan": {"meetings": [], "reports": []},
            "status_template": {"sections": [{"name": "Status", "fields": ["progress"]}]},
        },
    )


# ============== Generate ==============

@pytest.mark.integration
async def test_generate_delivery_plan(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """POST /api/v1/delivery/generate should create a delivery plan."""
    with patch(
        "app.services.delivery_service.DeliveryService._run_required_agent",
        new_callable=AsyncMock,
    ) as mock_agent:
        mock_agent.side_effect = [
            _fake_planner_result(),
            _fake_risk_result(),
            _fake_stakeholder_result(),
        ]

        response = await async_client.post("/api/v1/delivery/generate", json={
            "project_id": sample_project.id,
            "industry": "medical",
            "team_size": 5,
        })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] is not None
    assert data["data"]["title"] == f"{sample_project.name} 交付计划"
    assert data["data"]["wbs_tasks"] == 1
    assert data["data"]["risk_count"] == 1
    assert data["data"]["stakeholder_count"] == 1
    assert mock_agent.call_count == 3


@pytest.mark.integration
async def test_generate_delivery_plan_project_not_found(async_client: AsyncClient):
    """POST /api/v1/delivery/generate with invalid project should return 404."""
    response = await async_client.post("/api/v1/delivery/generate", json={
        "project_id": "nonexistent-id",
    })
    assert response.status_code == 404


@pytest.mark.integration
async def test_generate_delivery_plan_agent_failure(
    async_client: AsyncClient, sample_project: Project
):
    """Agent failure should return ExternalAPIError (502) via AppException handler."""
    from app.core.exceptions import ExternalAPIError

    with patch(
        "app.services.delivery_service.DeliveryService._run_required_agent",
        new_callable=AsyncMock,
    ) as mock_agent:
        mock_agent.side_effect = ExternalAPIError(service="delivery_planner", message="Agent not registered")

        response = await async_client.post("/api/v1/delivery/generate", json={
            "project_id": sample_project.id,
        })

    assert response.status_code == 502
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SRV_004"  # EXTERNAL_API_ERROR
    assert "Agent not registered" in body["error"]["message"]


# ============== Generate Single ==============

@pytest.mark.integration
async def test_generate_single_component(async_client: AsyncClient, sample_project: Project):
    """POST /api/v1/delivery/generate-single should run a single agent."""
    fake_result = _fake_planner_result()
    fake_result.execution_time = 1.5

    with patch(
        "app.services.delivery_service.DeliveryService._run_required_agent",
        new_callable=AsyncMock,
    ) as mock_agent:
        mock_agent.return_value = fake_result

        response = await async_client.post("/api/v1/delivery/generate-single", json={
            "project_id": sample_project.id,
            "agent_type": "delivery_planner",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["agent_type"] == "delivery_planner"
    assert data["data"]["output"] == "# Delivery Plan"
    assert data["data"]["execution_time"] == 1.5


@pytest.mark.integration
async def test_generate_single_invalid_agent_type(async_client: AsyncClient, sample_project: Project):
    """Invalid agent_type should be rejected with 400."""
    response = await async_client.post("/api/v1/delivery/generate-single", json={
        "project_id": sample_project.id,
        "agent_type": "nonexistent_agent",
    })
    assert response.status_code == 400


# ============== List ==============

@pytest.mark.integration
async def test_list_delivery_plans_empty(async_client: AsyncClient):
    """GET /api/v1/delivery/plans should return empty list."""
    response = await async_client.get("/api/v1/delivery/plans")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


@pytest.mark.integration
async def test_list_delivery_plans_with_data(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """GET /api/v1/delivery/plans should return plans with summary counts."""
    plan = DeliveryPlan(
        project_id=sample_project.id,
        title="Test Plan",
        status=DeliveryStatus.DRAFT,
        industry="medical",
        wbs={"tasks": [{"id": "t1"}, {"id": "t2"}]},
        risks=[{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        milestones={"phases": [{"phase_id": "p1"}]},
        created_by="single-user",
    )
    db_session.add(plan)
    await db_session.commit()

    response = await async_client.get("/api/v1/delivery/plans")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["title"] == "Test Plan"
    assert item["wbs_task_count"] == 2
    assert item["risk_count"] == 3
    assert item["milestone_count"] == 1


@pytest.mark.integration
async def test_list_delivery_plans_status_filter(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """Filter by status should work."""
    p1 = DeliveryPlan(project_id=sample_project.id, title="Draft Plan", status=DeliveryStatus.DRAFT, industry="medical",
                       wbs={}, risks=[], milestones={}, created_by="single-user")
    p2 = DeliveryPlan(project_id=sample_project.id, title="Active Plan", status=DeliveryStatus.IN_PROGRESS, industry="medical",
                       wbs={}, risks=[], milestones={}, created_by="single-user")
    db_session.add_all([p1, p2])
    await db_session.commit()

    response = await async_client.get("/api/v1/delivery/plans?status=in_progress")
    assert response.json()["data"]["total"] == 1

    response = await async_client.get("/api/v1/delivery/plans?status=draft")
    assert response.json()["data"]["total"] == 1


# ============== Get ==============

@pytest.mark.integration
async def test_get_delivery_plan(async_client: AsyncClient, db_session: AsyncSession, sample_project: Project):
    """GET /api/v1/delivery/plans/{id} should return full plan detail."""
    plan = DeliveryPlan(
        project_id=sample_project.id,
        title="Detail Plan",
        status=DeliveryStatus.DRAFT,
        industry="saas",
        wbs={"tasks": [], "total_tasks": 0, "total_effort_days": 0},
        milestones={"phases": [], "total_weeks": 0, "start_date": "", "end_date": ""},
        resources={"team_size": 3},
        gantt={"items": [], "total_days": 0, "start_date": ""},
        risks=[],
        risk_matrix={},
        risk_response_plan={},
        stakeholders=[],
        raci={},
        communication_plan={},
        status_template={},
        plan_markdown="# Plan",
        risk_markdown="# Risks",
        stakeholder_markdown="# Stakeholders",
        ai_generated={},
        created_by="single-user",
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    response = await async_client.get(f"/api/v1/delivery/plans/{plan.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == plan.id
    assert data["title"] == "Detail Plan"
    assert data["plan_markdown"] == "# Plan"
    assert data["wbs"] is not None
    assert data["milestones"] is not None


@pytest.mark.integration
async def test_get_delivery_plan_not_found(async_client: AsyncClient):
    """GET /api/v1/delivery/plans/{id} with invalid id should return 404."""
    response = await async_client.get("/api/v1/delivery/plans/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ============== Update ==============

@pytest.mark.integration
async def test_update_delivery_plan_status(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """PATCH /api/v1/delivery/plans/{id} should update status."""
    plan = DeliveryPlan(
        project_id=sample_project.id,
        title="To Update",
        status=DeliveryStatus.DRAFT,
        industry="medical",
        wbs={}, risks=[], milestones={},
        created_by="single-user",
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    response = await async_client.patch(
        f"/api/v1/delivery/plans/{plan.id}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify persistence
    await db_session.refresh(plan)
    assert plan.status == DeliveryStatus.IN_PROGRESS


@pytest.mark.integration
async def test_update_delivery_plan_invalid_status(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """PATCH with invalid status should return 400."""
    plan = DeliveryPlan(
        project_id=sample_project.id,
        title="Status Test",
        status=DeliveryStatus.DRAFT,
        industry="medical",
        wbs={}, risks=[], milestones={},
        created_by="single-user",
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    response = await async_client.patch(
        f"/api/v1/delivery/plans/{plan.id}",
        json={"status": "not_a_valid_status"},
    )
    assert response.status_code == 400


# ============== Delete ==============

@pytest.mark.integration
async def test_delete_delivery_plan(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """DELETE /api/v1/delivery/plans/{id} should soft-delete."""
    plan = DeliveryPlan(
        project_id=sample_project.id,
        title="To Delete",
        status=DeliveryStatus.DRAFT,
        industry="medical",
        wbs={}, risks=[], milestones={},
        created_by="single-user",
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    response = await async_client.delete(f"/api/v1/delivery/plans/{plan.id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify soft-deleted
    await db_session.refresh(plan)
    assert plan.deleted_at is not None

    # Should not appear in list
    list_resp = await async_client.get("/api/v1/delivery/plans")
    assert list_resp.json()["data"]["total"] == 0


@pytest.mark.integration
async def test_delete_delivery_plan_not_found(async_client: AsyncClient):
    """DELETE with invalid id should return 404."""
    response = await async_client.delete("/api/v1/delivery/plans/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ============== Dashboard ==============

@pytest.mark.integration
async def test_delivery_dashboard_empty(async_client: AsyncClient):
    """GET /api/v1/delivery/dashboard should return zeroed summary when no plans exist."""
    response = await async_client.get("/api/v1/delivery/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    summary = data["data"]
    assert summary["total_plans"] == 0
    assert summary["draft"] == 0
    assert summary["at_risk"] == 0
    assert summary["risk_health"] == "green"
    # Empty dashboard: task_completion=0 < 0.3 → delivery_health="red"
    # This is the expected behavior — 0 plans means 0 progress
    assert summary["delivery_health"] == "red"
    # No _debug_ts in response
    assert "_debug_ts" not in summary


@pytest.mark.integration
async def test_delivery_dashboard_with_data(
    async_client: AsyncClient, db_session: AsyncSession, sample_project: Project
):
    """Dashboard should aggregate plan health and task metrics."""
    plan = DeliveryPlan(
        project_id=sample_project.id,
        title="Dashboard Plan",
        status=DeliveryStatus.IN_PROGRESS,
        industry="medical",
        wbs={"tasks": [
            {"id": "t1", "status": "done"},
            {"id": "t2", "status": "in_progress"},
            {"id": "t3", "status": "todo"},
        ]},
        milestones={"phases": [
            {"phase_id": "ph1", "progress": 60, "end": "2026-12-31"},
        ]},
        risks=[{"risk_level": "高"}],
        created_by="single-user",
    )
    db_session.add(plan)
    await db_session.commit()

    response = await async_client.get("/api/v1/delivery/dashboard")
    assert response.status_code == 200
    summary = response.json()["data"]
    assert summary["total_plans"] == 1
    assert summary["in_progress"] == 1
    assert summary["total_risks"] == 1
    assert summary["high_risks"] == 1
    assert summary["total_tasks"] == 3
    assert summary["completed_tasks"] == 1
    assert summary["in_progress_tasks"] == 1
    assert summary["total_phases"] == 1
    assert summary["avg_phase_progress"] == 60.0


# ============== Schema Sanitize (unit tests — no HTTP needed) ==============

def test_sanitize_preserves_valid_data():
    """sanitize_delivery_payload should keep valid fields unchanged."""
    from app.schemas.delivery import sanitize_delivery_payload
    clean = {
        "wbs": {"tasks": [{"id": "1", "name": "Task"}]},
        "risks": [{"id": "r1", "risk": "Bad thing", "risk_level": "高"}],
        "stakeholders": [{"id": "s1", "role": "PM"}],
        "gantt": {"items": [{"id": "g1"}]},
        "milestones": {"phases": [{"phase_id": "p1"}]},
        "raci": {},
        "communication_plan": {},
        "status_template": {"sections": [{"name": "Status", "fields": ["progress"]}]},
    }
    result = sanitize_delivery_payload(clean)
    assert len(result["wbs"]["tasks"]) == 1
    assert len(result["risks"]) == 1
    # No warnings for clean data
    assert result["ai_generated"]["validation_warnings"] == []


def test_sanitize_drops_garbage():
    """sanitize_delivery_payload should drop non-dict items in lists and record warnings."""
    from app.schemas.delivery import sanitize_delivery_payload
    dirty = {
        "risks": [{"id": "good"}, "bad_string", 123, None],
        "stakeholders": None,
    }
    result = sanitize_delivery_payload(dirty)
    assert len(result["risks"]) == 1
    assert result["stakeholders"] == []
    # Warnings recorded
    warnings = result["ai_generated"]["validation_warnings"]
    assert any("stakeholders" in w for w in warnings), f"Expected stakeholders warning, got: {warnings}"
    assert any("risks" in w for w in warnings), f"Expected risks warning, got: {warnings}"


def test_sanitize_records_validation_warnings():
    """sanitize_delivery_payload should write warnings into ai_generated.validation_warnings."""
    from app.schemas.delivery import sanitize_delivery_payload
    data = {
        "risks": [{"bad_key": True}],
        "raci": "not_a_dict",
        "communication_plan": None,
    }
    result = sanitize_delivery_payload(data)
    warnings = result["ai_generated"]["validation_warnings"]
    assert len(warnings) >= 2, f"Expected at least 2 warnings, got: {warnings}"


def test_sanitize_wbs_task_defaults():
    """WbsTask should fill sensible defaults for missing fields."""
    from app.schemas.delivery import _try_validate_list, WbsTask
    raw = [{"id": "t1"}, {"name": "Only name"}]
    cleaned, warnings = _try_validate_list(raw, WbsTask, "test")
    assert len(cleaned) == 2
    assert warnings == []
    for c in cleaned:
        assert c["priority"] == "medium"
        assert c["effort_days"] == 0.0


def test_sanitize_risk_item_defaults():
    """RiskItem should fill defaults for missing risk levels."""
    from app.schemas.delivery import _try_validate_list, RiskItem
    raw = [{"id": "r1", "risk": "Unknown"}]
    cleaned, _ = _try_validate_list(raw, RiskItem, "test")
    assert cleaned[0]["risk_level"] == "低"
    assert cleaned[0]["risk_score"] == 0.0
    assert cleaned[0]["probability"] == 0.0
