"""Tools endpoints tests"""

import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.prd import PRD, PRDStatus


# ============== /user-research ==============

@pytest.mark.integration
async def test_user_research(async_client: AsyncClient):
    """POST /api/v1/tools/user-research should generate research report."""
    with patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "## 用户研究报告\n\n- 发现1\n- 发现2"

        response = await async_client.post("/api/v1/tools/user-research", json={
            "project_id": "proj-1",
            "research_type": "interview",
            "target_audience": "产品经理",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["research_type"] == "interview"
        assert "findings" in data["data"]
        assert "insights" in data["data"]


@pytest.mark.integration
async def test_user_research_validation_error(async_client: AsyncClient):
    """POST /user-research should validate research_type."""
    response = await async_client.post("/api/v1/tools/user-research", json={
        "project_id": "proj-1",
        "research_type": "invalid_type",
        "target_audience": "test",
    })
    assert response.status_code == 422


# ============== /competitors ==============

@pytest.mark.integration
async def test_competitor_analysis_with_crawler(async_client: AsyncClient):
    """POST /competitors should return analysis when crawler succeeds."""
    with patch("app.api.v1.endpoints.tools.web_crawler_service.search_competitor_info", new_callable=AsyncMock) as mock_crawler, \
         patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_crawler.return_value = {
            "results": [
                {
                    "success": True,
                    "name": "竞品A",
                    "url": "https://a.com",
                    "title": "A",
                    "description": "Desc",
                    "content": "Content",
                }
            ]
        }
        mock_chat.return_value = "## 竞品分析\n\n- 差异点1"

        response = await async_client.post("/api/v1/tools/competitors", json={
            "project_id": "proj-1",
            "competitors": ["竞品A"],
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["needs_confirmation"] is False
        assert "comparison_matrix" in data["data"]


@pytest.mark.integration
async def test_competitor_analysis_candidate_mode(async_client: AsyncClient):
    """POST /competitors should enter candidate mode when crawler fails."""
    with patch("app.api.v1.endpoints.tools.web_crawler_service.search_competitor_info", new_callable=AsyncMock) as mock_crawler, \
         patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_crawler.return_value = {"results": [{"success": False, "name": "竞品A", "error": "Timeout"}]}
        mock_chat.return_value = '[{"name": "候选竞品", "description": "候选", "source_detail": "AI推断"}]'

        response = await async_client.post("/api/v1/tools/competitors", json={
            "project_id": "proj-1",
            "competitors": ["竞品A"],
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["needs_confirmation"] is True
        assert len(data["data"]["candidates"]) >= 1


@pytest.mark.integration
async def test_competitor_analysis_no_data(async_client: AsyncClient):
    """POST /competitors should return error when both crawler and LLM fail."""
    with patch("app.api.v1.endpoints.tools.web_crawler_service.search_competitor_info", new_callable=AsyncMock) as mock_crawler, \
         patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_crawler.return_value = {"results": []}
        mock_chat.return_value = "invalid json"

        response = await async_client.post("/api/v1/tools/competitors", json={
            "project_id": "proj-1",
            "competitors": ["竞品A"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


# ============== /competitors/confirm ==============

@pytest.mark.integration
async def test_confirm_competitor_analysis(async_client: AsyncClient):
    """POST /competitors/confirm should generate report for confirmed candidates."""
    with patch("app.api.v1.endpoints.tools.web_crawler_service.search_competitor_info", new_callable=AsyncMock) as mock_crawler, \
         patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_crawler.return_value = {"results": []}
        mock_chat.return_value = "## 正式竞品分析"

        response = await async_client.post("/api/v1/tools/competitors/confirm", json={
            "project_id": "proj-1",
            "competitors": ["竞品A"],
            "confirmed_candidates": [{"name": "竞品A", "description": "已确认"}],
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["confirmed"] is True
        assert data["data"]["needs_confirmation"] is False


@pytest.mark.integration
async def test_confirm_competitor_analysis_no_candidates(async_client: AsyncClient):
    """POST /competitors/confirm should error with no candidates."""
    response = await async_client.post("/api/v1/tools/competitors/confirm", json={
        "project_id": "proj-1",
        "competitors": ["竞品A"],
        "confirmed_candidates": [],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False


# ============== /data-analysis ==============

@pytest.mark.integration
async def test_data_analysis(async_client: AsyncClient):
    """POST /data-analysis should generate analysis framework."""
    with patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "## 数据分析框架"

        response = await async_client.post("/api/v1/tools/data-analysis", json={
            "project_id": "proj-1",
            "data_source": "日志数据",
            "metrics": ["DAU", "留存率"],
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "summary" in data["data"]
        assert len(data["data"]["trends"]) == 2
        assert len(data["data"]["anomalies"]) == 0


# ============== /stakeholders ==============

@pytest.mark.integration
async def test_stakeholder_analysis_medical(async_client: AsyncClient, db_session: AsyncSession):
    """POST /stakeholders should include medical roles for medical industry."""
    project = Project(
        id="med-proj",
        name="Medical System",
        description="HIS system",
        industry="medical",
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    with patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "## 干系人分析\n| 角色 | 影响力 | 利益度 |\n| 医务科 | 高 | 高 |"

        response = await async_client.post("/api/v1/tools/stakeholders", json={
            "project_id": "med-proj",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "influence_matrix" in data["data"]
        assert "communication_plan" in data["data"]


@pytest.mark.integration
async def test_stakeholder_analysis_general(async_client: AsyncClient, db_session: AsyncSession):
    """POST /stakeholders should work for general industry."""
    project = Project(
        id="gen-proj",
        name="General Project",
        description="A general project",
        industry="saas",
        created_by="single-user",
    )
    db_session.add(project)
    await db_session.commit()

    with patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "## 干系人分析"

        response = await async_client.post("/api/v1/tools/stakeholders", json={
            "project_id": "gen-proj",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True


# ============== /review-materials ==============

@pytest.mark.integration
async def test_review_materials_with_prd(async_client: AsyncClient, sample_prd: PRD):
    """POST /review-materials should generate materials when PRD exists."""
    with patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "## 评审材料"

        response = await async_client.post("/api/v1/tools/review-materials", json={
            "project_id": sample_prd.project_id,
            "material_type": "tech_review",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["material_type"] == "tech_review"
        assert "content" in data["data"]


@pytest.mark.integration
async def test_review_materials_no_prd(async_client: AsyncClient):
    """POST /review-materials should handle missing PRD gracefully."""
    response = await async_client.post("/api/v1/tools/review-materials", json={
        "project_id": "no-prd-project",
        "material_type": "tech_review",
    })
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "未找到 PRD" in data["data"]["content"]["raw"]


# ============== /review-materials-stream ==============

@pytest.mark.integration
async def test_review_materials_stream(async_client: AsyncClient, sample_prd: PRD):
    """POST /review-materials-stream should return SSE stream."""
    with patch("app.api.v1.endpoints.tools.ai_service.generate_review_material_stream") as mock_stream:
        async def fake_generator():
            yield "chunk1"
            yield "chunk2"

        mock_stream.return_value = fake_generator()

        response = await async_client.post("/api/v1/tools/review-materials-stream", json={
            "project_id": sample_prd.project_id,
            "material_type": "tech_review",
        })
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        body = response.text
        assert "chunk1" in body
        assert "done" in body


@pytest.mark.integration
async def test_review_materials_stream_no_prd(async_client: AsyncClient):
    """POST /review-materials-stream should handle missing PRD."""
    with patch("app.api.v1.endpoints.tools.ai_service.generate_review_material_stream") as mock_stream:
        async def fake_generator():
            yield "fallback"

        mock_stream.return_value = fake_generator()

        response = await async_client.post("/api/v1/tools/review-materials-stream", json={
            "project_id": "no-prd-project",
            "material_type": "tech_review",
        })
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


# ============== /prototype ==============

@pytest.mark.integration
async def test_prototype(async_client: AsyncClient):
    """POST /prototype should generate prototype guidance."""
    with patch("app.api.v1.endpoints.tools.ai_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "## 原型设计"

        response = await async_client.post("/api/v1/tools/prototype", json={
            "project_id": "proj-1",
            "feature_description": "用户登录功能",
            "prototype_type": "wireframe",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "pages" in data["data"]
        assert len(data["data"]["pages"]) == 3
        assert "user_flows" in data["data"]


# ============== /stats ==============

@pytest.mark.integration
async def test_get_stats(async_client: AsyncClient):
    """GET /stats/{project_id} should return usage stats."""
    response = await async_client.get("/api/v1/tools/stats/proj-1")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["project_id"] == "proj-1"
    assert "usage" in data["data"]


# ============== /data-analysis-upload ==============

@pytest.mark.integration
async def test_data_analysis_upload(async_client: AsyncClient):
    """POST /data-analysis-upload should process uploaded file."""
    with patch("app.api.v1.endpoints.tools.analyze_uploaded_data", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = {
            "summary": "文件分析结果",
            "rows": 100,
            "columns": 5,
        }

        file_content = b"col1,col2\n1,2\n3,4"
        response = await async_client.post(
            "/api/v1/tools/data-analysis-upload",
            data={"project_id": "proj-1"},
            files={"file": ("test.csv", file_content, "text/csv")},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "summary" in data["data"]


@pytest.mark.integration
async def test_data_analysis_upload_validation_error(async_client: AsyncClient):
    """POST /data-analysis-upload should 400 on bad input."""
    with patch("app.api.v1.endpoints.tools.analyze_uploaded_data") as mock_analyze:
        mock_analyze.side_effect = ValueError("Invalid file format")

        file_content = b"not,a,csv"
        response = await async_client.post(
            "/api/v1/tools/data-analysis-upload",
            data={"project_id": "proj-1"},
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        assert response.status_code == 400


@pytest.mark.integration
async def test_data_analysis_upload_unsupported(async_client: AsyncClient):
    """POST /data-analysis-upload should 422 on unsupported format."""
    with patch("app.api.v1.endpoints.tools.analyze_uploaded_data") as mock_analyze:
        mock_analyze.side_effect = NotImplementedError("Format not supported")

        file_content = b"some binary"
        response = await async_client.post(
            "/api/v1/tools/data-analysis-upload",
            data={"project_id": "proj-1"},
            files={"file": ("test.xyz", file_content, "application/octet-stream")},
        )
        assert response.status_code == 422
