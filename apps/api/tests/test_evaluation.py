"""Evaluation system endpoints tests"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


# ============== /evaluate-prd ==============

@pytest.mark.integration
async def test_evaluate_prd(async_client: AsyncClient):
    """POST /api/v1/evaluation/evaluation/evaluate-prd should return quality scores."""
    with patch("app.api.v1.endpoints.evaluation.evaluator.evaluate") as mock_eval:
        mock_score = MagicMock()
        mock_score.prd_id = "prd-123"
        mock_score.overall_score = 85.5
        mock_score.grade = "B+"
        mock_score.completeness.score = 90.0
        mock_score.accuracy.score = 80.0
        mock_score.usability.score = 85.0
        mock_score.compliance.score = 88.0
        mock_score.get_improvement_suggestions.return_value = ["补充用户故事", "细化验收标准"]
        mock_eval.return_value = mock_score

        response = await async_client.post("/api/v1/evaluation/evaluation/evaluate-prd", json={
            "prd_content": "A" * 100,
            "prd_id": "prd-123",
        })
        assert response.status_code == 200

        data = response.json()
        assert data["prd_id"] == "prd-123"
        assert data["overall_score"] == 85.5
        assert data["grade"] == "B+"
        assert data["completeness_score"] == 90.0
        assert len(data["suggestions"]) == 2


@pytest.mark.integration
async def test_evaluate_prd_too_short(async_client: AsyncClient):
    """POST with short PRD should return 400."""
    response = await async_client.post("/api/v1/evaluation/evaluation/evaluate-prd", json={
        "prd_content": "short",
        "prd_id": "test",
    })
    assert response.status_code == 400


# ============== A/B Tests ==============

@pytest.mark.integration
async def test_create_ab_test(async_client: AsyncClient):
    """POST /api/v1/evaluation/evaluation/ab-tests should create a test."""
    with patch("app.api.v1.endpoints.evaluation.ab_framework.create_test") as mock_create:
        mock_test = MagicMock()
        mock_test.id = "test-123"
        mock_test.name = "Prompt优化测试"
        mock_test.status.value = "draft"
        mock_test.control.id = "ctrl-1"
        mock_test.treatment.id = "treat-1"
        mock_create.return_value = "test-123"

        response = await async_client.post("/api/v1/evaluation/evaluation/ab-tests", json={
            "name": "Prompt优化测试",
            "hypothesis": "优化后的Prompt能提升PRD质量",
            "control_prompt": "原始Prompt",
            "treatment_prompt": "优化Prompt",
            "traffic_split": 0.5,
        })
        assert response.status_code == 200

        data = response.json()
        assert data["test_id"] == "test-123"
        assert data["name"] == "Prompt优化测试"
        assert data["status"] == "draft"


@pytest.mark.integration
async def test_start_ab_test(async_client: AsyncClient):
    """POST /api/v1/evaluation/evaluation/ab-tests/{id}/start should start test."""
    with patch("app.api.v1.endpoints.evaluation.ab_framework.start_test") as mock_start:
        response = await async_client.post("/api/v1/evaluation/evaluation/ab-tests/test-123/start")
        assert response.status_code == 200
        assert "测试已启动" in response.json()["message"]
        mock_start.assert_called_once_with("test-123")


@pytest.mark.integration
async def test_get_ab_test_results(async_client: AsyncClient):
    """GET /api/v1/evaluation/evaluation/ab-tests/{id}/results should return results."""
    with patch("app.api.v1.endpoints.evaluation.ab_framework.get_results") as mock_results:
        mock_results.return_value = {"test_id": "test-123", "winner": "treatment"}

        response = await async_client.get("/api/v1/evaluation/evaluation/ab-tests/test-123/results")
        assert response.status_code == 200
        assert response.json()["winner"] == "treatment"


@pytest.mark.integration
async def test_list_ab_tests(async_client: AsyncClient):
    """GET /api/v1/evaluation/evaluation/ab-tests should list tests."""
    with patch("app.api.v1.endpoints.evaluation.ab_framework.list_tests") as mock_list:
        mock_test = MagicMock()
        mock_test.id = "t1"
        mock_test.name = "测试1"
        mock_test.status.value = "running"
        mock_test.hypothesis = "假设"
        mock_test.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_list.return_value = [mock_test]

        response = await async_client.get("/api/v1/evaluation/evaluation/ab-tests")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["test_id"] == "t1"


# ============== Feedback ==============

@pytest.mark.integration
async def test_submit_feedback(async_client: AsyncClient):
    """POST /api/v1/evaluation/evaluation/feedback should collect feedback."""
    with patch("app.api.v1.endpoints.evaluation.feedback_collector.collect") as mock_collect:
        mock_collect.return_value = "fb-123"

        response = await async_client.post("/api/v1/evaluation/evaluation/feedback", json={
            "prd_id": "prd-123",
            "user_id": "user-1",
            "overall_rating": 4,
            "accuracy_rating": 5,
            "usefulness_rating": 3,
            "what_worked": "结构清晰",
            "what_failed": "细节不足",
            "suggestions": "增加用例",
            "feedback_type": "suggestion",
        })
        assert response.status_code == 200
        assert response.json()["feedback_id"] == "fb-123"


@pytest.mark.integration
async def test_get_feedback_statistics(async_client: AsyncClient):
    """GET /api/v1/evaluation/evaluation/feedback/statistics should return stats."""
    with patch("app.api.v1.endpoints.evaluation.feedback_collector.get_statistics") as mock_stats:
        mock_stats_obj = MagicMock()
        mock_stats_obj.total_count = 10
        mock_stats_obj.avg_overall_rating = 4.2
        mock_stats_obj.avg_accuracy_rating = 4.5
        mock_stats_obj.avg_usefulness_rating = 3.8
        mock_stats_obj.rating_distribution = {"5": 3, "4": 5, "3": 2}
        mock_stats_obj.recent_trend = "stable"
        mock_stats.return_value = mock_stats_obj

        response = await async_client.get("/api/v1/evaluation/evaluation/feedback/statistics")
        assert response.status_code == 200
        assert response.json()["total_feedbacks"] == 10
        assert response.json()["avg_overall_rating"] == 4.2


# ============== Templates ==============

@pytest.mark.integration
async def test_get_ab_test_templates(async_client: AsyncClient):
    """GET /api/v1/evaluation/evaluation/templates/ab-tests should return templates."""
    response = await async_client.get("/api/v1/evaluation/evaluation/templates/ab-tests")
    assert response.status_code == 200
    assert len(response.json()) >= 2
    assert any(t["template_id"] == "prd_prompt_enhancement" for t in response.json())


@pytest.mark.integration
async def test_create_from_template(async_client: AsyncClient):
    """POST /api/v1/evaluation/evaluation/templates/ab-tests/{id}/create should create from template."""
    with patch("app.api.v1.endpoints.evaluation.ab_framework.create_test") as mock_create:
        mock_test = MagicMock()
        mock_test.name = "PRD Prompt优化测试"
        mock_create.return_value = "from-template-123"

        response = await async_client.post("/api/v1/evaluation/evaluation/templates/ab-tests/prd_prompt_enhancement/create")
        assert response.status_code == 200
        assert response.json()["test_id"] == "from-template-123"


@pytest.mark.integration
async def test_create_from_invalid_template(async_client: AsyncClient):
    """POST with invalid template_id should return 404."""
    response = await async_client.post("/api/v1/evaluation/evaluation/templates/ab-tests/invalid/create")
    assert response.status_code == 500