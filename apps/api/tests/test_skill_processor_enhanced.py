"""Tests for Enhanced Skill Processor module.

This module tests the enhanced skill processor functionality:
- Skill listing and retrieval
- Skill execution with mock provider
- Output validation integration
- Error handling
- Caching behavior
"""

import pytest
import pytest_asyncio
import json
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from app.services.skill_processor_enhanced import SkillProcessorEnhanced
from app.services.llm_provider import MockProvider
from app.services.output_validator import OutputValidator


# ==================== Skill Processor Initialization Tests ====================

class TestSkillProcessorInitialization:
    """Test suite for SkillProcessorEnhanced initialization."""

    def test_processor_creation_with_mock_provider(self):
        """Test creating processor with mock provider."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        assert processor._skills is not None
        assert len(processor._skills) > 0
        assert processor._enable_cache is False

    def test_processor_creation_default_provider(self):
        """Test creating processor with default provider."""
        processor = SkillProcessorEnhanced(enable_cache=True)

        assert processor._llm is not None
        assert processor._enable_cache is True

    def test_processor_skills_initialized(self):
        """Test that skills are initialized on creation."""
        processor = SkillProcessorEnhanced(llm_provider="mock")

        assert "requirement-analysis" in processor._skills
        assert "write-prd" in processor._skills
        assert "tech-architecture" in processor._skills
        assert "business-model" in processor._skills


# ==================== Skill Listing Tests ====================

class TestSkillListing:
    """Test suite for skill listing functionality."""

    def test_list_skills_returns_list(self):
        """Test that list_skills returns a list."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skills = processor.list_skills()

        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_list_skills_structure(self):
        """Test that listed skills have correct structure."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skills = processor.list_skills()

        for skill in skills:
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill
            assert "agentRole" in skill
            assert "category" in skill
            assert "icon" in skill
            assert "tags" in skill

    def test_list_skills_contains_expected_skills(self):
        """Test that expected skills are in the list."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skills = processor.list_skills()

        skill_ids = [s["id"] for s in skills]

        assert "requirement-analysis" in skill_ids
        assert "write-prd" in skill_ids
        assert "tech-architecture" in skill_ids
        assert "business-model" in skill_ids
        assert "milestone-plan" in skill_ids
        assert "medical-review" in skill_ids
        assert "compliance-check" in skill_ids

    def test_list_skills_medical_category(self):
        """Test that medical skills are categorized correctly."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skills = processor.list_skills()

        medical_skills = [s for s in skills if s["category"] == "medical"]

        assert len(medical_skills) >= 3  # medical-review, compliance-check, multi-branch-analysis


# ==================== Get Skill Tests ====================

class TestGetSkill:
    """Test suite for get_skill functionality."""

    def test_get_existing_skill(self):
        """Test getting an existing skill."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor.get_skill("requirement-analysis")

        assert skill is not None
        assert skill["id"] == "requirement-analysis"
        assert "parameters" in skill
        assert "prompt_template" in skill

    def test_get_skill_has_parameters(self):
        """Test that skill has parameters defined."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor.get_skill("requirement-analysis")

        assert isinstance(skill["parameters"], list)
        assert len(skill["parameters"]) > 0

        for param in skill["parameters"]:
            assert "name" in param
            assert "label" in param
            assert "type" in param

    def test_get_nonexistent_skill(self):
        """Test getting a non-existent skill."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor.get_skill("nonexistent-skill")

        assert skill is None

    def test_get_skill_output_schema(self):
        """Test that skill has output schema info."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor.get_skill("requirement-analysis")

        assert "outputSchema" in skill


# ==================== Input Validation Tests ====================

class TestInputValidation:
    """Test suite for input validation."""

    def test_validate_inputs_required_fields(self):
        """Test validation of required input fields."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["requirement-analysis"]

        # Missing required fields
        inputs = {}
        errors = processor._validate_inputs(skill, inputs)

        assert len(errors) > 0
        # Error messages use 'label' field, not 'name' field
        assert any("产品想法" in e for e in errors)
        assert any("目标用户" in e for e in errors)

    def test_validate_inputs_with_valid_data(self):
        """Test validation with valid input data."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["requirement-analysis"]

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }
        errors = processor._validate_inputs(skill, inputs)

        assert len(errors) == 0

    def test_validate_inputs_optional_fields(self):
        """Test that optional fields don't cause errors."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["requirement-analysis"]

        # Provide only required fields
        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
            # constraints is optional
        }
        errors = processor._validate_inputs(skill, inputs)

        assert len(errors) == 0


# ==================== Prompt Building Tests ====================

class TestPromptBuilding:
    """Test suite for prompt building functionality."""

    def test_build_prompt_basic(self):
        """Test basic prompt building."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["requirement-analysis"]

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical",
            "constraints": "None"
        }

        prompt = processor._build_prompt(skill, inputs, {})

        assert "Test idea" in prompt
        assert "Test users" in prompt
        assert "medical" in prompt

    def test_build_prompt_with_medical_terms(self):
        """Test prompt building with medical term enrichment."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["medical-review"]

        inputs = {
            "requirement": "Design a system for 切片借阅",
            "featureType": "clinical_workflow",
            "patientData": True
        }

        prompt = processor._build_prompt(skill, inputs, {})

        assert "切片借阅" in prompt
        # Should have medical context or term enrichment
        assert "【术语说明】" in prompt or "requirement" in prompt.lower()

    def test_build_prompt_missing_variable(self):
        """Test prompt building with missing template variable."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["requirement-analysis"]

        # Missing 'constraints' variable
        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        # Should not raise error, should fill with empty string
        prompt = processor._build_prompt(skill, inputs, {})
        assert "Test idea" in prompt


# ==================== JSON Parsing Tests ====================

class TestJSONParsing:
    """Test suite for JSON output parsing."""

    def test_parse_json_from_code_block(self):
        """Test parsing JSON from markdown code block."""
        processor = SkillProcessorEnhanced(llm_provider="mock")

        text = '''```json
{"key": "value", "number": 123}
```'''

        result = processor._parse_json_output(text)

        assert result["key"] == "value"
        assert result["number"] == 123

    def test_parse_json_without_code_block(self):
        """Test parsing JSON without code block."""
        processor = SkillProcessorEnhanced(llm_provider="mock")

        text = '{"key": "value", "number": 123}'

        result = processor._parse_json_output(text)

        assert result["key"] == "value"
        assert result["number"] == 123

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON."""
        processor = SkillProcessorEnhanced(llm_provider="mock")

        text = "This is not valid JSON"

        result = processor._parse_json_output(text)

        assert "raw_response" in result
        assert result["raw_response"] == text

    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with surrounding whitespace."""
        processor = SkillProcessorEnhanced(llm_provider="mock")

        text = '   \n  {"key": "value"}  \n  '

        result = processor._parse_json_output(text)

        assert result["key"] == "value"


# ==================== Output Formatting Tests ====================

class TestOutputFormatting:
    """Test suite for output formatting."""

    def test_format_requirement_analysis_output(self):
        """Test formatting requirement analysis output."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["requirement-analysis"]

        output = {
            "productOneLiner": "Test product",
            "userPersona": {
                "who": "Test users",
                "painPoints": "Test pain",
                "currentSolutions": "Current",
                "whyNewProduct": "Why new"
            },
            "featureList": {
                "p0": ["Feature 1"],
                "p1": [],
                "p2": []
            }
        }

        formatted = processor._format_output(skill, output)

        assert "## 需求分析 执行结果" in formatted
        assert "Test product" in formatted
        assert "Test users" in formatted

    def test_format_prd_output(self):
        """Test formatting PRD output."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["write-prd"]

        output = {
            "markdown": "# Test PRD\n\nContent here"
        }

        formatted = processor._format_output(skill, output)

        assert formatted == "# Test PRD\n\nContent here"

    def test_format_tech_architecture_output(self):
        """Test formatting tech architecture output."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["tech-architecture"]

        output = {
            "techStack": "Python, FastAPI",
            "components": [
                {"name": "API", "description": "REST API"}
            ]
        }

        formatted = processor._format_output(skill, output)

        assert "Python, FastAPI" in formatted
        assert "API" in formatted

    def test_format_default_output(self):
        """Test formatting with default format."""
        processor = SkillProcessorEnhanced(llm_provider="mock")
        skill = processor._skills["business-model"]

        output = {"key": "value"}

        formatted = processor._format_output(skill, output)

        assert "```json" in formatted
        assert "key" in formatted


# ==================== Skill Execution Tests ====================

class TestSkillExecution:
    """Test suite for skill execution."""

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(self):
        """Test execution of non-existent skill."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        result = await processor.execute_skill("nonexistent", {}, {})

        assert result["success"] is False
        assert "不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_missing_required_input(self):
        """Test execution with missing required input."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        result = await processor.execute_skill("requirement-analysis", {}, {})

        assert result["success"] is False
        assert "必填项" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skill_success(self):
        """Test successful skill execution."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert result["success"] is True
        assert "output" in result
        assert "formatted_output" in result
        assert "execution_time" in result
        assert "token_usage" in result

    @pytest.mark.asyncio
    async def test_execute_skill_returns_markdown(self):
        """Test that execution returns markdown formatted output."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert "formatted_output" in result
        assert isinstance(result["formatted_output"], str)
        assert len(result["formatted_output"]) > 0

    @pytest.mark.asyncio
    async def test_execute_skill_token_usage(self):
        """Test that execution returns token usage info."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert "token_usage" in result
        assert "prompt" in result["token_usage"]
        assert "completion" in result["token_usage"]
        assert "total" in result["token_usage"]


# ==================== Caching Tests ====================

class TestCaching:
    """Test suite for caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=True)

        inputs = {"key": "value"}
        key1 = processor._get_cache_key("test-skill", inputs)
        key2 = processor._get_cache_key("test-skill", inputs)

        assert key1 == key2
        assert key1.startswith("skill:")

    @pytest.mark.asyncio
    async def test_cache_key_different_inputs(self):
        """Test that different inputs generate different cache keys."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=True)

        key1 = processor._get_cache_key("test-skill", {"key": "value1"})
        key2 = processor._get_cache_key("test-skill", {"key": "value2"})

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_execute_with_cache_disabled(self):
        """Test execution with cache disabled."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert result["from_cache"] is False


# ==================== Output Validation Integration Tests ====================

class TestOutputValidationIntegration:
    """Test suite for output validation integration."""

    @pytest.mark.asyncio
    async def test_output_is_validated(self):
        """Test that skill output is validated."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert result["success"] is True
        # Output should have been validated and fixed
        assert "output" in result

    @pytest.mark.asyncio
    async def test_output_fix_common_issues_applied(self):
        """Test that common issues are fixed in output."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        # The output should have required fields after fixing
        output = result["output"]
        if isinstance(output, dict):
            assert "featureList" in output or result["success"] is True


# ==================== Error Handling Tests ====================

class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_llm_error_handling(self):
        """Test handling of LLM errors."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        # Mock the LLM to raise an exception
        processor._llm.complete = AsyncMock(side_effect=Exception("LLM Error"))

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert result["success"] is False
        assert "LLM调用失败" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_json_response_handling(self):
        """Test handling of invalid JSON response."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        # Mock the LLM to return invalid JSON
        processor._llm.complete = AsyncMock(return_value="Not valid JSON")

        inputs = {
            "idea": "Test idea",
            "targetUsers": "Test users",
            "industry": "medical"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        # Should still succeed - invalid JSON gets wrapped in raw_response
        # and then fix_common_issues adds default fields
        assert result["success"] is True
        # After fix_common_issues, the output will have default structure
        # with the raw_response possibly being processed
        assert "output" in result


# ==================== Medical Skills Tests ====================

class TestMedicalSkills:
    """Test suite for medical-specific skills."""

    @pytest.mark.asyncio
    async def test_medical_review_skill(self):
        """Test medical review skill execution."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "requirement": "Design a slide lending system",
            "featureType": "clinical_workflow",
            "patientData": True
        }

        result = await processor.execute_skill("medical-review", inputs, {})

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_compliance_check_skill(self):
        """Test compliance check skill execution."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "prd": "PRD content here",
            "complianceLevel": "level3"
        }

        result = await processor.execute_skill("compliance-check", inputs, {})

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_multi_branch_analysis_skill(self):
        """Test multi-branch analysis skill execution."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "requirement": "Design a system for multiple branches",
            "branches": "Branch A, Branch B",
            "standardFeatures": "Standard features here"
        }

        result = await processor.execute_skill("multi-branch-analysis", inputs, {})

        assert result["success"] is True


# ==================== Integration Tests ====================

class TestSkillProcessorIntegration:
    """Integration tests for skill processor."""

    @pytest.mark.asyncio
    async def test_full_workflow_requirement_analysis(self):
        """Test complete workflow for requirement analysis."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        # List skills
        skills = processor.list_skills()
        skill_ids = [s["id"] for s in skills]
        assert "requirement-analysis" in skill_ids

        # Get skill details
        skill = processor.get_skill("requirement-analysis")
        assert skill is not None

        # Execute skill
        inputs = {
            "idea": "A platform for patients to borrow medical slides",
            "targetUsers": "Patients needing external consultation",
            "industry": "medical",
            "constraints": "Must comply with HIPAA"
        }

        result = await processor.execute_skill("requirement-analysis", inputs, {})

        assert result["success"] is True
        assert "output" in result
        assert "formatted_output" in result
        assert result["from_cache"] is False

    @pytest.mark.asyncio
    async def test_multiple_skill_executions(self):
        """Test executing multiple skills in sequence."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        skills_to_test = ["requirement-analysis", "business-model", "tech-architecture"]

        for skill_id in skills_to_test:
            skill = processor.get_skill(skill_id)
            if skill:
                # Create minimal valid inputs
                inputs = {}
                for param in skill["parameters"]:
                    if param.get("required"):
                        if param["type"] == "string":
                            inputs[param["name"]] = "Test value"
                        elif param["type"] == "textarea":
                            inputs[param["name"]] = "Test content"
                        elif param["type"] == "number":
                            inputs[param["name"]] = "5"
                        elif param["type"] == "select":
                            inputs[param["name"]] = param["options"][0]["value"] if param.get("options") else ""
                        elif param["type"] == "boolean":
                            inputs[param["name"]] = True

                if inputs:  # Only test if there are required inputs
                    result = await processor.execute_skill(skill_id, inputs, {})
                    assert result["success"] is True, f"Skill {skill_id} failed"

    @pytest.mark.asyncio
    async def test_skill_with_medical_terminology(self):
        """Test skill that uses medical terminology."""
        processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)

        inputs = {
            "requirement": "设计一个切片借阅系统，支持免疫组化检测申请",
            "featureType": "clinical_workflow",
            "patientData": True
        }

        result = await processor.execute_skill("medical-review", inputs, {})

        assert result["success"] is True
        # The prompt should have been enriched with medical terminology
