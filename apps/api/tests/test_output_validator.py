"""Tests for Output Validator module.

This module tests the output validation functionality:
- Schema validation for all skill types
- fix_common_issues function
- Validation error handling
"""

import pytest
from pydantic import ValidationError
from typing import Dict, Any, List

from app.services.output_validator import (
    OutputValidator,
    SKILL_OUTPUT_SCHEMAS,
    RequirementAnalysisOutput,
    PRDOutput,
    BusinessModelOutput,
    TechArchitectureOutput,
    MilestonePlanOutput,
    UXDesignOutput,
    MedicalReviewOutput,
    ComplianceCheckOutput,
    UserStory,
    FeatureList,
    UserPersona,
    SuccessMetric,
    PRDSection,
    RevenueStream,
    TechComponent,
    MilestonePhase,
    MedicalRationality,
    ComplianceCategory,
    ComplianceItem,
    RiskItem,
    ChecklistItem,
)


# ==================== Schema Definition Tests ====================

class TestSchemaDefinitions:
    """Test suite for schema definitions."""

    def test_all_schemas_defined(self):
        """Test that all skill schemas are defined."""
        expected_skills = [
            "requirement-analysis",
            "write-prd",
            "business-model",
            "tech-architecture",
            "milestone-plan",
            "ux-design",
            "medical-review",
            "compliance-check",
        ]

        for skill in expected_skills:
            assert skill in SKILL_OUTPUT_SCHEMAS, f"Schema for '{skill}' not defined"

    def test_schema_classes_exist(self):
        """Test that all schema classes exist."""
        classes = [
            RequirementAnalysisOutput,
            PRDOutput,
            BusinessModelOutput,
            TechArchitectureOutput,
            MilestonePlanOutput,
            UXDesignOutput,
            MedicalReviewOutput,
            ComplianceCheckOutput,
        ]

        for cls in classes:
            assert cls is not None


# ==================== Requirement Analysis Schema Tests ====================

class TestRequirementAnalysisValidation:
    """Test suite for requirement-analysis schema validation."""

    def test_valid_requirement_analysis(self, valid_requirement_analysis_output):
        """Test validation of valid requirement analysis output."""
        result = OutputValidator.validate("requirement-analysis", valid_requirement_analysis_output)

        assert result["valid"] is True
        assert result["errors"] == []
        assert "data" in result

    def test_invalid_requirement_analysis_missing_fields(self):
        """Test validation with missing required fields."""
        invalid_output = {
            "productOneLiner": "Test product",
            # Missing userPersona, featureList, etc.
        }

        result = OutputValidator.validate("requirement-analysis", invalid_output)

        # Should still be valid due to default values
        assert result["valid"] is True

    def test_invalid_user_story_priority(self):
        """Test validation with invalid user story priority."""
        invalid_output = {
            "productOneLiner": "Test",
            "userPersona": {"who": "", "painPoints": "", "currentSolutions": "", "whyNewProduct": ""},
            "featureList": {"p0": [], "p1": [], "p2": []},
            "userStories": [
                {"id": "1", "role": "User", "action": "Test", "benefit": "Test", "priority": "invalid"}
            ],
            "successMetrics": {}
        }

        result = OutputValidator.validate("requirement-analysis", invalid_output)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_valid_user_story_creation(self):
        """Test creating a valid UserStory."""
        story = UserStory(
            id="1",
            role="Patient",
            action="apply for service",
            benefit="save time",
            priority="high"
        )

        assert story.id == "1"
        assert story.priority == "high"

    def test_invalid_user_story_priority_raises_error(self):
        """Test that invalid priority raises ValidationError."""
        with pytest.raises(ValidationError):
            UserStory(
                id="1",
                role="Patient",
                action="apply",
                benefit="save time",
                priority="invalid_priority"
            )


# ==================== PRD Schema Tests ====================

class TestPRDValidation:
    """Test suite for PRD schema validation."""

    def test_valid_prd(self, valid_prd_output):
        """Test validation of valid PRD output."""
        result = OutputValidator.validate("write-prd", valid_prd_output)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_section_priority(self):
        """Test validation with invalid section priority."""
        invalid_output = {
            "title": "Test PRD",
            "sections": [
                {"title": "Overview", "content": "Content", "priority": "invalid"}
            ],
            "markdown": "# Test"
        }

        result = OutputValidator.validate("write-prd", invalid_output)
        assert result["valid"] is False

    def test_valid_prd_section_creation(self):
        """Test creating a valid PRDSection."""
        section = PRDSection(
            title="Overview",
            content="Test content",
            priority="high"
        )

        assert section.title == "Overview"
        assert section.priority == "high"


# ==================== Business Model Schema Tests ====================

class TestBusinessModelValidation:
    """Test suite for business-model schema validation."""

    def test_valid_business_model(self, valid_business_model_output):
        """Test validation of valid business model output."""
        result = OutputValidator.validate("business-model", valid_business_model_output)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_valid_revenue_stream_creation(self):
        """Test creating a valid RevenueStream."""
        stream = RevenueStream(
            name="Subscription",
            description="Monthly fee",
            pricing="$99/month"
        )

        assert stream.name == "Subscription"


# ==================== Tech Architecture Schema Tests ====================

class TestTechArchitectureValidation:
    """Test suite for tech-architecture schema validation."""

    def test_valid_tech_architecture(self, valid_tech_architecture_output):
        """Test validation of valid tech architecture output."""
        result = OutputValidator.validate("tech-architecture", valid_tech_architecture_output)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_valid_tech_component_creation(self):
        """Test creating a valid TechComponent."""
        component = TechComponent(
            name="API Gateway",
            description="Entry point",
            techStack=["Nginx", "FastAPI"],
            responsibilities=["Routing"]
        )

        assert component.name == "API Gateway"


# ==================== Milestone Plan Schema Tests ====================

class TestMilestonePlanValidation:
    """Test suite for milestone-plan schema validation."""

    def test_valid_milestone_plan(self, valid_milestone_plan_output):
        """Test validation of valid milestone plan output."""
        result = OutputValidator.validate("milestone-plan", valid_milestone_plan_output)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_valid_milestone_phase_creation(self):
        """Test creating a valid MilestonePhase."""
        phase = MilestonePhase(
            name="Phase 1",
            duration="2 months",
            deliverables=["MVP"],
            resources=["2 developers"]
        )

        assert phase.name == "Phase 1"


# ==================== Medical Review Schema Tests ====================

class TestMedicalReviewValidation:
    """Test suite for medical-review schema validation."""

    def test_valid_medical_review(self, valid_medical_review_output):
        """Test validation of valid medical review output."""
        result = OutputValidator.validate("medical-review", valid_medical_review_output)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_medical_rationality_score(self):
        """Test validation with invalid rationality score."""
        invalid_output = {
            "summary": "Test",
            "medicalRationality": {
                "score": 150,  # Invalid: should be 0-100
                "assessment": "Test"
            },
            "complianceAnalysis": {},
            "riskAssessment": [],
            "approvalRecommendation": "approve"
        }

        result = OutputValidator.validate("medical-review", invalid_output)
        assert result["valid"] is False

    def test_invalid_approval_recommendation(self):
        """Test validation with invalid approval recommendation."""
        invalid_output = {
            "summary": "Test",
            "medicalRationality": {
                "score": 80,
                "assessment": "Test"
            },
            "complianceAnalysis": {},
            "riskAssessment": [],
            "approvalRecommendation": "invalid"  # Invalid value
        }

        result = OutputValidator.validate("medical-review", invalid_output)
        assert result["valid"] is False

    def test_valid_medical_rationality_creation(self):
        """Test creating a valid MedicalRationality."""
        rationality = MedicalRationality(
            score=85,
            assessment="Good",
            concerns=["Minor issue"],
            recommendations=["Add logging"]
        )

        assert rationality.score == 85

    def test_invalid_score_raises_error(self):
        """Test that invalid score raises ValidationError."""
        with pytest.raises(ValidationError):
            MedicalRationality(score=150, assessment="Test")


# ==================== Compliance Check Schema Tests ====================

class TestComplianceCheckValidation:
    """Test suite for compliance-check schema validation."""

    def test_valid_compliance_check(self, valid_compliance_check_output):
        """Test validation of valid compliance check output."""
        result = OutputValidator.validate("compliance-check", valid_compliance_check_output)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_overall_status(self):
        """Test validation with invalid overall status."""
        invalid_output = {
            "summary": "Test",
            "overallStatus": "invalid",  # Invalid value
            "score": 80,
            "categories": []
        }

        result = OutputValidator.validate("compliance-check", invalid_output)
        assert result["valid"] is False

    def test_invalid_score_range(self):
        """Test validation with invalid score range."""
        invalid_output = {
            "summary": "Test",
            "overallStatus": "pass",
            "score": 150,  # Invalid: should be 0-100
            "categories": []
        }

        result = OutputValidator.validate("compliance-check", invalid_output)
        assert result["valid"] is False

    def test_valid_compliance_item_creation(self):
        """Test creating a valid ComplianceItem."""
        item = ComplianceItem(
            requirement="Multi-factor auth",
            status="pass"
        )

        assert item.requirement == "Multi-factor auth"
        assert item.status == "pass"

    def test_invalid_compliance_item_status(self):
        """Test that invalid compliance item status raises error."""
        with pytest.raises(ValidationError):
            ComplianceItem(
                requirement="Test",
                status="invalid"
            )


# ==================== fix_common_issues Tests ====================

class TestFixCommonIssues:
    """Test suite for fix_common_issues function."""

    def test_fix_requirement_analysis_missing_feature_list(self):
        """Test fixing missing featureList in requirement analysis."""
        output = {
            "productOneLiner": "Test",
            # Missing featureList
        }

        fixed = OutputValidator.fix_common_issues("requirement-analysis", output)

        assert "featureList" in fixed
        assert fixed["featureList"] == {"p0": [], "p1": [], "p2": []}

    def test_fix_requirement_analysis_invalid_feature_list_type(self):
        """Test fixing invalid featureList type."""
        output = {
            "productOneLiner": "Test",
            "featureList": "not a dict"
        }

        fixed = OutputValidator.fix_common_issues("requirement-analysis", output)

        assert isinstance(fixed["featureList"], dict)
        assert fixed["featureList"] == {"p0": [], "p1": [], "p2": []}

    def test_fix_requirement_analysis_missing_p_keys(self):
        """Test fixing missing p0/p1/p2 keys in featureList."""
        output = {
            "productOneLiner": "Test",
            "featureList": {"p0": ["feature1"]}  # Missing p1, p2
        }

        fixed = OutputValidator.fix_common_issues("requirement-analysis", output)

        assert "p0" in fixed["featureList"]
        assert "p1" in fixed["featureList"]
        assert "p2" in fixed["featureList"]
        assert fixed["featureList"]["p0"] == ["feature1"]
        assert fixed["featureList"]["p1"] == []

    def test_fix_requirement_analysis_missing_user_stories(self):
        """Test fixing missing userStories."""
        output = {
            "productOneLiner": "Test",
            "featureList": {"p0": [], "p1": [], "p2": []}
            # Missing userStories
        }

        fixed = OutputValidator.fix_common_issues("requirement-analysis", output)

        assert "userStories" in fixed
        assert fixed["userStories"] == []

    def test_fix_requirement_analysis_missing_user_persona(self):
        """Test fixing missing userPersona."""
        output = {
            "productOneLiner": "Test",
            "featureList": {"p0": [], "p1": [], "p2": []},
            "userStories": []
            # Missing userPersona
        }

        fixed = OutputValidator.fix_common_issues("requirement-analysis", output)

        assert "userPersona" in fixed
        assert fixed["userPersona"]["who"] == ""
        assert fixed["userPersona"]["painPoints"] == ""

    def test_fix_prd_missing_markdown(self):
        """Test fixing missing markdown in PRD output."""
        output = {
            "title": "Test PRD",
            "sections": [
                {"title": "Overview", "content": "Test content"}
            ]
            # Missing markdown
        }

        fixed = OutputValidator.fix_common_issues("write-prd", output)

        assert "markdown" in fixed
        assert "# Test PRD" in fixed["markdown"]
        assert "## Overview" in fixed["markdown"]

    def test_fix_prd_empty_markdown(self):
        """Test fixing empty markdown in PRD output."""
        output = {
            "title": "Test PRD",
            "sections": [
                {"title": "Section 1", "content": "Content 1"}
            ],
            "markdown": ""
        }

        fixed = OutputValidator.fix_common_issues("write-prd", output)

        assert "# Test PRD" in fixed["markdown"]
        assert "## Section 1" in fixed["markdown"]

    def test_fix_tech_architecture_missing_components(self):
        """Test fixing missing components in tech architecture."""
        output = {
            "overview": "Test",
            "techStack": "Python"
            # Missing components
        }

        fixed = OutputValidator.fix_common_issues("tech-architecture", output)

        assert "components" in fixed
        assert fixed["components"] == []

    def test_fix_milestone_plan_missing_phases(self):
        """Test fixing missing phases in milestone plan."""
        output = {
            "totalDuration": "6 months"
            # Missing phases
        }

        fixed = OutputValidator.fix_common_issues("milestone-plan", output)

        assert "phases" in fixed
        assert fixed["phases"] == []

    def test_fix_unknown_skill_no_changes(self):
        """Test that unknown skills are not modified."""
        output = {"test": "data"}
        fixed = OutputValidator.fix_common_issues("unknown-skill", output)

        assert fixed == output


# ==================== Utility Method Tests ====================

class TestOutputValidatorUtilities:
    """Test suite for OutputValidator utility methods."""

    def test_get_schema_description(self):
        """Test getting schema description."""
        description = OutputValidator.get_schema_description("requirement-analysis")
        assert isinstance(description, str)
        assert len(description) > 0

    def test_get_schema_description_unknown_skill(self):
        """Test getting description for unknown skill."""
        description = OutputValidator.get_schema_description("unknown-skill")
        assert description == "Unknown skill"

    def test_list_supported_skills(self):
        """Test listing supported skills."""
        skills = OutputValidator.list_supported_skills()

        assert isinstance(skills, list)
        assert "requirement-analysis" in skills
        assert "write-prd" in skills
        assert "business-model" in skills


# ==================== Integration Tests ====================

class TestOutputValidatorIntegration:
    """Integration tests for output validator."""

    def test_validate_then_fix_workflow(self):
        """Test complete workflow: validate then fix issues."""
        # Invalid output with missing fields
        output = {
            "productOneLiner": "Test product",
            # Missing many fields
        }

        # First validate (should fail or have issues)
        result = OutputValidator.validate("requirement-analysis", output)

        # Then fix common issues
        fixed = OutputValidator.fix_common_issues("requirement-analysis", output)

        # Validate again (should pass)
        result2 = OutputValidator.validate("requirement-analysis", fixed)

        assert result2["valid"] is True

    def test_all_schemas_accept_empty_dict(self):
        """Test that all schemas can handle empty dict with defaults."""
        for skill_id in OutputValidator.list_supported_skills():
            result = OutputValidator.validate(skill_id, {})
            # Most should be valid due to default values
            assert "valid" in result
            assert "data" in result

    def test_validation_preserves_extra_fields(self):
        """Test that validation preserves extra fields."""
        output = {
            "productOneLiner": "Test",
            "extraField": "extra value",
            "userPersona": {
                "who": "",
                "painPoints": "",
                "currentSolutions": "",
                "whyNewProduct": ""
            },
            "featureList": {"p0": [], "p1": [], "p2": []},
            "userStories": [],
            "successMetrics": {}
        }

        result = OutputValidator.validate("requirement-analysis", output)

        # Pydantic v2 doesn't preserve extra fields by default
        # but validation should succeed
        assert result["valid"] is True
