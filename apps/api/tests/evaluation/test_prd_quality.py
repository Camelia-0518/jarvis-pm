"""Tests for PRD quality evaluation system."""

import pytest
from unittest.mock import AsyncMock, patch

from app.evaluation.metrics.prd_quality import (
    PRDQualityEvaluator,
    LLMQualityEvaluator,
    PRDQualityScore,
)


SAMPLE_PRD = """
# 产品需求文档

## 1. 背景与目标
为医院开发一个病案复印申请系统，方便患者线上申请病历复印并邮寄到家。

## 2. 用户故事
- 作为患者，我想要在线申请病案复印，以便不用跑医院就能拿到病历。
- 作为病案室管理员，我想要审核患者的复印申请，以便确保病案安全。

## 3. 业务流程
1. 患者填写申请单
2. 管理员审核
3. 复印并邮寄

## 4. 功能规格
- 在线填写申请（患者姓名、身份证号、住院号、复印用途）
- 上传身份证照片
- 在线支付复印费和快递费
- 管理员审核通过/拒绝

## 5. 合规要求
- 患者隐私保护：身份证照片需加密存储，仅病案室管理员可查看。
- 等保三级：系统需通过等保三级认证。
- 审计追溯：所有操作需记录日志，保留 5 年。
"""


class TestHeuristicEvaluator:
    def test_evaluate_returns_valid_score(self):
        evaluator = PRDQualityEvaluator()
        score = evaluator.evaluate(SAMPLE_PRD, prd_id="test-001")

        assert isinstance(score, PRDQualityScore)
        assert score.prd_id == "test-001"
        assert 0 <= score.overall_score <= 100
        assert score.grade in ["A", "B", "C", "D", "F"]
        assert score.used_llm is False

    def test_completeness_detects_user_stories(self):
        evaluator = PRDQualityEvaluator()
        score = evaluator.evaluate(SAMPLE_PRD)
        assert score.completeness.has_user_stories is True
        assert score.completeness.has_compliance_section is True

    def test_compliance_detects_privacy(self):
        evaluator = PRDQualityEvaluator()
        score = evaluator.evaluate(SAMPLE_PRD)
        assert score.compliance.privacy_protection is True
        assert score.compliance.data_security is True
        assert score.compliance.audit_trail is True

    def test_improvement_suggestions_not_empty_for_low_score(self):
        evaluator = PRDQualityEvaluator()
        score = evaluator.evaluate("这是一个很短的PRD。")
        suggestions = score.get_improvement_suggestions()
        assert len(suggestions) > 0


class TestLLMEvaluatorFallback:
    @pytest.mark.asyncio
    async def test_fallback_when_llm_fails(self):
        evaluator = LLMQualityEvaluator()
        # Force LLM to fail
        with patch.object(evaluator.llm_client, "chat", side_effect=Exception("LLM timeout")):
            score = await evaluator.evaluate(SAMPLE_PRD, prd_id="test-002")

        assert isinstance(score, PRDQualityScore)
        assert score.prd_id == "test-002"
        assert 0 <= score.overall_score <= 100
        # Fallback should not have LLM reasoning
        assert score.used_llm is False

    @pytest.mark.asyncio
    async def test_llm_path_when_success(self):
        evaluator = LLMQualityEvaluator()
        mock_response = '{\n  "completeness": 85,\n  "accuracy": 80,\n  "usability": 75,\n  "compliance": 90,\n  "reasoning": "文档结构完整，合规性描述清晰"\n}'

        with patch.object(evaluator.llm_client, "chat", return_value=mock_response):
            score = await evaluator.evaluate(SAMPLE_PRD, prd_id="test-003")

        assert score.used_llm is True
        assert score.llm_reasoning is not None
        assert score.overall_score > 0
        assert score.completeness.score == 85
        assert score.accuracy.score == 80
        assert score.usability.score == 75
        assert score.compliance.score == 90

    @pytest.mark.asyncio
    async def test_llm_path_with_markdown_code_block(self):
        evaluator = LLMQualityEvaluator()
        mock_response = '```json\n{\n  "completeness": 70,\n  "accuracy": 75,\n  "usability": 80,\n  "compliance": 65,\n  "reasoning": "整体良好"\n}\n```'

        with patch.object(evaluator.llm_client, "chat", return_value=mock_response):
            score = await evaluator.evaluate(SAMPLE_PRD, prd_id="test-004")

        assert score.used_llm is True
        assert score.completeness.score == 70

    @pytest.mark.asyncio
    async def test_forces_fallback_when_use_llm_false(self):
        evaluator = LLMQualityEvaluator()
        # Even with a working LLM, use_llm=False should skip it
        with patch.object(evaluator.llm_client, "chat") as mock_chat:
            score = await evaluator.evaluate(SAMPLE_PRD, prd_id="test-005", use_llm=False)
            mock_chat.assert_not_called()

        assert score.used_llm is False
        assert 0 <= score.overall_score <= 100
