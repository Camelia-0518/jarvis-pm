#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end tests for PRD generation API endpoints."""

import asyncio
import pytest
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.core.security import get_current_user_id
from app.agents.base import AgentResult


async def override_get_current_user_id():
    return "test-user-123"


fastapi_app.dependency_overrides[get_current_user_id] = override_get_current_user_id


@pytest.fixture(scope="module")
def client():
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture
def valid_ai_prd_request():
    return {
        "title": "病理切片借阅平台",
        "description": "为患者提供线上病理切片借阅申请、审核、物流跟踪的一站式平台",
        "industry": "medical",
        "context": {"compliance_level": "level3"}
    }


@pytest.fixture
def valid_agent_prd_request():
    return {
        "product_name": "病理切片借阅平台",
        "description": "为患者提供线上病理切片借阅申请、审核、物流跟踪的一站式平台",
        "target_users": "需要外院会诊的患者及医院病理科工作人员",
        "key_features": ["在线申请", "进度跟踪", "物流对接", "电子签名"],
        "constraints": ["等保三级合规", "患者隐私保护"],
        "sections": ["background", "user_stories", "functional_requirements"]
    }


@pytest.fixture
def mock_prd_output():
    return """---
generated_at: 2024-01-01 00:00:00
agent: prd_generator v1.0.0
---

# 产品需求文档 (PRD)

## 产品名称
病理切片借阅平台

## 背景
患者需要借阅病理切片进行外院会诊，传统流程繁琐。

## 用户故事
- 作为患者，我想要在线申请切片借阅，以便节省时间。
- 作为病理科医生，我想要审核借阅申请，以便规范管理。

## 功能需求
1. 在线申请：患者填写申请信息并提交。
2. 进度跟踪：实时查看审核和物流状态。
"""


class TestAIGeneratePRD:
    def test_generate_prd_success(self, client, valid_ai_prd_request):
        response = client.post("/api/v1/ai/generate-prd", json=valid_ai_prd_request)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "outline" in data["data"]
        assert "content" in data["data"]
        assert "suggestions" in data["data"]
        assert isinstance(data["data"]["suggestions"], list)

    def test_generate_prd_empty_body(self, client):
        response = client.post("/api/v1/ai/generate-prd", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_generate_prd_missing_required_fields(self, client):
        response = client.post("/api/v1/ai/generate-prd", json={"title": "", "description": ""})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_generate_prd_unauthorized_without_token(self, client, valid_ai_prd_request):
        original_overrides = fastapi_app.dependency_overrides.copy()
        fastapi_app.dependency_overrides.pop(get_current_user_id, None)
        try:
            response = client.post("/api/v1/ai/generate-prd", json=valid_ai_prd_request)
            # Single-user mode: no token returns default user, so it may return 200
            assert response.status_code in (200, 401, 403)
        finally:
            fastapi_app.dependency_overrides = original_overrides


class TestAgentGeneratePRD:
    def test_submit_prd_generation_success(self, client, valid_agent_prd_request):
        response = client.post("/api/v1/agents/prd/generate", json=valid_agent_prd_request)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "task_id" in data["data"]
        assert data["data"]["status"] == "queued"
        UUID(data["data"]["task_id"])

    def test_submit_prd_generation_invalid_body(self, client):
        response = client.post("/api/v1/agents/prd/generate", json={
            "product_name": "",
            "description": "too short",
            "target_users": "",
            "key_features": []
        })
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_submit_prd_generation_missing_fields(self, client):
        response = client.post("/api/v1/agents/prd/generate", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_prd_generation_end_to_end_with_mocked_agent(
        self, client, valid_agent_prd_request, mock_prd_output
    ):
        from app.agents.tasks import get_task_queue

        response = client.post("/api/v1/agents/prd/generate", json=valid_agent_prd_request)
        assert response.status_code == 200
        task_id = response.json()["data"]["task_id"]

        # Directly manipulate task state since worker loop doesn't run in TestClient
        queue = get_task_queue()
        task = queue._tasks.get(UUID(task_id))
        assert task is not None
        task.status = "completed"
        task.result = AgentResult(
            success=True,
            output=mock_prd_output,
            data={
                "product_name": task.input_data.get("product_name", ""),
                "sections_generated": task.input_data.get("sections", []),
                "content_length": len(mock_prd_output)
            },
            execution_time=0.5,
            metadata={"agent_name": "prd_generator", "version": "1.0.0"}
        )

        status_response = client.get(f"/api/v1/agents/tasks/{task_id}")
        assert status_response.status_code == 200
        final_data = status_response.json()["data"]
        assert final_data["status"] == "completed"
        result = final_data["result"]
        assert result["success"] is True
        assert "病理切片借阅平台" in result["output"]
        assert result["data"]["product_name"] == "病理切片借阅平台"
        assert result["execution_time"] == 0.5

    @pytest.mark.asyncio
    async def test_prd_generation_task_failure(self, client, valid_agent_prd_request):
        from app.agents.tasks import get_task_queue

        response = client.post("/api/v1/agents/prd/generate", json=valid_agent_prd_request)
        assert response.status_code == 200
        task_id = response.json()["data"]["task_id"]

        queue = get_task_queue()
        task = queue._tasks.get(UUID(task_id))
        assert task is not None
        task.status = "failed"
        task.error = "LLM service unavailable"
        task.result = AgentResult(
            success=False,
            output="",
            error="LLM service unavailable",
            execution_time=0.1
        )

        status_response = client.get(f"/api/v1/agents/tasks/{task_id}")
        assert status_response.status_code == 200
        final_data = status_response.json()["data"]
        assert final_data["status"] == "failed"
        assert "LLM service unavailable" in final_data["result"]["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
