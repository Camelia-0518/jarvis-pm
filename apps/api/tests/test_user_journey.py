"""End-to-end user journey tests

Covers the critical user flow:
  Create Project -> Enter Workspace -> Generate PRD -> Add Competitor Analysis -> Export PRD
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project import Project
from app.models.prd import PRD, PRDStatus
from app.models.competitor import Competitor


@pytest.mark.integration
async def test_user_journey_create_project_to_export(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Full journey: create project -> create PRD -> generate chapter -> competitor analysis -> export."""

    # Step 1: Create a project
    project_payload = {
        "name": "Journey Test Project",
        "description": "A project for E2E journey testing",
        "industry": "saas",
    }
    response = await async_client.post("/api/v1/projects", json=project_payload)
    assert response.status_code == 201
    project_data = response.json()["data"]
    project_id = project_data["id"]
    assert project_data["name"] == "Journey Test Project"

    # Step 2: Create a PRD for the project
    prd_payload = {
        "project_id": project_id,
        "title": "Journey Test PRD",
        "template": "standard",
    }
    response = await async_client.post("/api/v1/prds", json=prd_payload)
    assert response.status_code == 200
    prd_data = response.json()["data"]
    prd_id = prd_data["id"]
    assert prd_data["title"] == "Journey Test PRD"
    assert prd_data["status"] == "draft"

    # Step 3: Update PRD content (simulate user editing)
    update_payload = {
        "content": {
            "chapters": {"1": {"title": "Introduction", "content": ""}},
            "template": "standard",
            "industry": "saas",
        },
        "markdown": "# Journey Test PRD\n\n## Introduction",
    }
    response = await async_client.put(f"/api/v1/prds/{prd_id}", json=update_payload)
    assert response.status_code == 200

    # Step 4: Create competitor analysis for the project
    competitor_payload = {
        "project_id": project_id,
        "name": "Competitor A",
        "description": "Main competitor",
        "strengths": "Strong brand",
        "weaknesses": "Slow innovation",
    }
    response = await async_client.post(f"/api/v1/projects/{project_id}/competitors", json=competitor_payload)
    assert response.status_code == 200
    competitor_data = response.json()["data"]
    assert competitor_data["name"] == "Competitor A"

    # Step 5: Export PRD in markdown format
    response = await async_client.get(f"/api/v1/prds/{prd_id}/export?format=markdown")
    assert response.status_code == 200
    export_data = response.json()["data"]
    assert export_data["format"] == "markdown"
    assert "Journey Test PRD" in export_data["content"]
    assert export_data["filename"].endswith(".md")

    # Step 6: Export PRD in JSON format
    response = await async_client.get(f"/api/v1/prds/{prd_id}/export?format=json")
    assert response.status_code == 200
    export_data = response.json()["data"]
    assert export_data["format"] == "json"
    assert export_data["filename"].endswith(".json")

    # Step 7: Verify project data in database
    result = await db_session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one()
    assert project.name == "Journey Test Project"

    # Step 8: Verify PRD data in database
    result = await db_session.execute(select(PRD).where(PRD.id == prd_id))
    prd = result.scalar_one()
    assert prd.title == "Journey Test PRD"
    assert prd.status == PRDStatus.DRAFT

    # Step 9: Verify competitor in database
    result = await db_session.execute(select(Competitor).where(Competitor.project_id == project_id))
    competitors = result.scalars().all()
    assert len(competitors) == 1
    assert competitors[0].name == "Competitor A"


@pytest.mark.integration
async def test_user_journey_project_prd_version_workflow(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Journey with version history: create PRD -> update -> create version -> restore version."""

    # Step 1: Create project
    response = await async_client.post(
        "/api/v1/projects",
        json={"name": "Version Journey Project", "description": "Test", "industry": "saas"},
    )
    project_id = response.json()["data"]["id"]

    # Step 2: Create PRD
    response = await async_client.post(
        "/api/v1/prds",
        json={"project_id": project_id, "title": "Version PRD", "template": "standard"},
    )
    prd_id = response.json()["data"]["id"]

    # Step 3: Update PRD
    response = await async_client.put(
        f"/api/v1/prds/{prd_id}",
        json={"markdown": "# Version 1", "title": "Version PRD Updated"},
    )
    assert response.status_code == 200

    # Step 4: List versions (update above auto-created a snapshot, so 1 version exists)
    response = await async_client.get(f"/api/v1/prds/{prd_id}/versions")
    assert response.status_code == 200
    versions_data = response.json()["data"]
    assert versions_data["total"] == 1
    first_version_id = versions_data["items"][0]["id"]

    # Step 5: Create a manual version snapshot via DB
    from app.models.prd_version import PRDVersion
    version = PRDVersion(
        prd_id=prd_id,
        version_number=2,
        title="Snapshot Title",
        content='{"template": "standard"}',
        markdown="# Snapshot Content",
        created_by="single-user",
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)

    # Step 6: List versions again
    response = await async_client.get(f"/api/v1/prds/{prd_id}/versions")
    assert response.status_code == 200
    versions_data = response.json()["data"]
    assert versions_data["total"] == 2

    # Step 7: Restore the manually created version
    response = await async_client.post(f"/api/v1/prds/{prd_id}/versions/{version.id}/restore")
    assert response.status_code == 200
    restore_data = response.json()["data"]
    assert restore_data["restored_version"] == 2

    # Step 8: Verify PRD was restored
    result = await db_session.execute(select(PRD).where(PRD.id == prd_id))
    prd = result.scalar_one()
    assert prd.title == "Snapshot Title"
    assert prd.markdown == "# Snapshot Content"


@pytest.mark.integration
async def test_user_journey_workspace_tools(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Journey: create project -> create persona -> create requirement -> view project summary."""

    # Step 1: Create project
    response = await async_client.post(
        "/api/v1/projects",
        json={"name": "Workspace Journey", "description": "Test workspace tools", "industry": "medical"},
    )
    project_id = response.json()["data"]["id"]

    # Step 2: Create persona
    persona_payload = {
        "project_id": project_id,
        "name": "Doctor Persona",
        "role": "医生",
        "description": "三甲医院医生",
        "pain_points": "系统复杂",
        "goals": "提高效率",
        "scenarios": "门诊接诊",
    }
    response = await async_client.post(f"/api/v1/projects/{project_id}/personas", json=persona_payload)
    assert response.status_code == 200
    persona = response.json()["data"]
    assert persona["name"] == "Doctor Persona"

    # Step 3: Create requirement
    req_payload = {
        "title": "登录功能",
        "description": "支持验证码登录",
        "status": "backlog",
        "priority": "p1",
    }
    response = await async_client.post(f"/api/v1/projects/{project_id}/requirements", json=req_payload)
    assert response.status_code == 200
    req = response.json()["data"]
    assert req["title"] == "登录功能"

    # Step 4: Fetch project details
    response = await async_client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    project = response.json()["data"]
    assert project["name"] == "Workspace Journey"

    # Step 5: List personas for project
    response = await async_client.get(f"/api/v1/projects/{project_id}/personas")
    assert response.status_code == 200
    personas = response.json()["data"]
    assert len(personas) >= 1

    # Step 6: List requirements for project
    response = await async_client.get(f"/api/v1/projects/{project_id}/requirements")
    assert response.status_code == 200
    requirements = response.json()["data"]
    assert len(requirements) >= 1
