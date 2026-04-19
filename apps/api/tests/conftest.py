"""Pytest fixtures and configuration for Jarvis PM Skill system tests.

This module provides shared fixtures and test data for all test modules.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock


# ==================== LLM Provider Fixtures ====================

@pytest.fixture
def mock_kimi_api_key():
    """Fixture providing a mock Kimi API key."""
    return "test-kimi-api-key-12345"


@pytest.fixture
def mock_openai_api_key():
    """Fixture providing a mock OpenAI API key."""
    return "test-openai-api-key-67890"


@pytest.fixture
def sample_prompt():
    """Fixture providing a sample prompt for testing."""
    return "Analyze the requirements for a medical slide lending platform."


@pytest.fixture
def sample_medical_prompt():
    """Fixture providing a sample medical-related prompt."""
    return """
    Design a system for patients to borrow pathology slides from the hospital
    for external consultation. The system should handle slice lending requests,
    track immunohistochemistry test results, and integrate with the existing HIS.
    """


# ==================== Medical Terminology Fixtures ====================

@pytest.fixture
def medical_terms_sample():
    """Fixture providing sample medical terms for testing."""
    return {
        "切片借阅": {
            "definition": "患者或第三方机构申请借阅医院病理科保存的组织切片进行会诊或检测",
            "synonyms": ["玻片借阅", "病理切片外借", "切片外送"],
            "related_terms": ["病理科", "会诊", "免疫组化", "HE染色", "蜡块"],
            "context": "病理科业务流程",
            "examples": ["患者需要借阅切片去外院会诊"]
        },
        "免疫组化": {
            "definition": "免疫组织化学检测，利用抗原抗体反应检测组织中特定蛋白的表达",
            "synonyms": ["IHC", "免疫染色", "免疫组织化学"],
            "related_terms": ["病理诊断", "肿瘤标志物", "切片", "抗体"],
            "context": "病理检测技术",
            "examples": ["通过免疫组化检测HER2表达"]
        }
    }


@pytest.fixture
def sample_text_with_medical_terms():
    """Fixture providing sample text containing medical terms."""
    return """
    患者申请借阅病理切片用于外院会诊，需要进行免疫组化检测。
    病理科负责处理切片借阅申请，并出具HE染色报告。
    """


@pytest.fixture
def sample_text_without_medical_terms():
    """Fixture providing sample text without medical terms."""
    return "This is a regular text about general software development."


# ==================== Output Validator Fixtures ====================

@pytest.fixture
def valid_requirement_analysis_output():
    """Fixture providing a valid requirement analysis output."""
    return {
        "productOneLiner": "A platform for patients to borrow medical slides",
        "userPersona": {
            "who": "Patients needing external consultation",
            "painPoints": "Difficult to access their medical slides",
            "currentSolutions": "Manual application at hospital",
            "whyNewProduct": "Streamlined digital process"
        },
        "featureList": {
            "p0": ["Online application", "Status tracking"],
            "p1": ["Digital payment", "SMS notifications"],
            "p2": ["Multi-language support"]
        },
        "userStories": [
            {
                "id": "1",
                "role": "Patient",
                "action": "apply for slide lending online",
                "benefit": "save time and avoid hospital visits",
                "priority": "high"
            },
            {
                "id": "2",
                "role": "Doctor",
                "action": "review applications",
                "benefit": "manage requests efficiently",
                "priority": "medium"
            }
        ],
        "successMetrics": {
            "northStar": "User satisfaction score",
            "metrics": [
                {"name": "Application completion rate", "target": "95%", "timeFrame": "3 months"}
            ]
        }
    }


@pytest.fixture
def invalid_requirement_analysis_output():
    """Fixture providing an invalid requirement analysis output."""
    return {
        "productOneLiner": "Test product",
        # Missing required fields
        "featureList": {
            "p0": "not a list",  # Wrong type
            "p1": [],
            "p2": []
        }
    }


@pytest.fixture
def valid_prd_output():
    """Fixture providing a valid PRD output."""
    return {
        "title": "Medical Slide Lending Platform PRD",
        "version": "1.0",
        "sections": [
            {
                "title": "Overview",
                "content": "Platform for patients to borrow slides",
                "priority": "high"
            },
            {
                "title": "Requirements",
                "content": "Detailed requirements here",
                "priority": "normal"
            }
        ],
        "markdown": "# Medical Slide Lending Platform PRD\n\n## Overview\nPlatform for patients to borrow slides"
    }


@pytest.fixture
def valid_business_model_output():
    """Fixture providing a valid business model output."""
    return {
        "valueProposition": "Streamlined slide lending process",
        "targetCustomer": "Hospitals and patients",
        "revenueStreams": [
            {"name": "Subscription", "description": "Monthly fee", "pricing": "$99/month"}
        ],
        "costStructure": ["Development", "Hosting", "Support"],
        "keyMetrics": ["User growth", "Retention rate"]
    }


@pytest.fixture
def valid_tech_architecture_output():
    """Fixture providing a valid tech architecture output."""
    return {
        "overview": "Microservices architecture",
        "techStack": "Python FastAPI, PostgreSQL, Redis",
        "components": [
            {
                "name": "API Gateway",
                "description": "Entry point for all requests",
                "techStack": ["Nginx", "FastAPI"],
                "responsibilities": ["Routing", "Authentication"]
            }
        ],
        "dataFlow": "Client -> API Gateway -> Services",
        "deployment": "Docker containers on Kubernetes",
        "security": "JWT authentication, HTTPS"
    }


@pytest.fixture
def valid_milestone_plan_output():
    """Fixture providing a valid milestone plan output."""
    return {
        "phases": [
            {
                "name": "Phase 1: MVP",
                "duration": "2 months",
                "startDate": "2024-01-01",
                "endDate": "2024-03-01",
                "deliverables": ["Core features", "Basic UI"],
                "resources": ["2 developers", "1 designer"]
            }
        ],
        "totalDuration": "6 months",
        "criticalPath": ["Backend API", "Database setup"],
        "risks": [{"risk": "Technical complexity", "mitigation": "Hire senior developer"}]
    }


@pytest.fixture
def valid_medical_review_output():
    """Fixture providing a valid medical review output."""
    return {
        "summary": "The design is medically sound",
        "medicalRationality": {
            "score": 85,
            "assessment": "Good alignment with clinical workflow",
            "concerns": ["Data privacy needs attention"],
            "recommendations": ["Add audit logging"]
        },
        "complianceAnalysis": {
            "applicableRegulations": ["HIPAA", "等保三级"],
            "complianceStatus": "compliant",
            "gaps": [],
            "actions": []
        },
        "riskAssessment": [
            {"risk": "Data breach", "level": "medium", "impact": "High", "mitigation": "Encryption"}
        ],
        "approvalRecommendation": "approve"
    }


@pytest.fixture
def valid_compliance_check_output():
    """Fixture providing a valid compliance check output."""
    return {
        "summary": "Overall compliance is good",
        "overallStatus": "pass",
        "score": 85,
        "categories": [
            {
                "name": "Authentication",
                "status": "pass",
                "items": [
                    {"requirement": "Multi-factor auth", "status": "pass"}
                ]
            }
        ],
        "criticalIssues": [],
        "recommendations": ["Regular security audits"],
        "checklist": [
            {"item": "Data encryption", "checked": True, "category": "Security"}
        ]
    }


# ==================== Skill Processor Fixtures ====================

@pytest.fixture
def sample_skill_inputs():
    """Fixture providing sample inputs for various skills."""
    return {
        "requirement-analysis": {
            "idea": "A platform for patients to borrow medical slides",
            "targetUsers": "Patients needing external consultation",
            "industry": "medical",
            "constraints": "Must comply with HIPAA"
        },
        "write-prd": {
            "requirementAnalysis": '{"productOneLiner": "Test product"}',
            "template": "standard",
            "detailLevel": "detailed"
        },
        "tech-architecture": {
            "prd": "PRD content here",
            "scalability": "medium",
            "techStackPreference": "Python, FastAPI"
        },
        "business-model": {
            "productDescription": "Medical slide lending platform",
            "market": "Healthcare IT",
            "competitors": "Traditional hospital systems"
        },
        "milestone-plan": {
            "prd": "PRD content",
            "teamSize": "5",
            "architecture": "Microservices"
        },
        "medical-review": {
            "requirement": "Design for slide lending system",
            "featureType": "clinical_workflow",
            "patientData": True
        },
        "compliance-check": {
            "prd": "PRD with security features",
            "complianceLevel": "level3"
        }
    }


@pytest.fixture
def mock_llm_response():
    """Fixture providing a mock LLM response."""
    return '''```json
{
    "result": "success",
    "data": {
        "productOneLiner": "Test product",
        "userPersona": {
            "who": "Test user",
            "painPoints": "Test pain point",
            "currentSolutions": "Current solution",
            "whyNewProduct": "Why new"
        },
        "featureList": {
            "p0": ["Feature 1"],
            "p1": [],
            "p2": []
        },
        "userStories": [],
        "successMetrics": {}
    }
}
```'''


@pytest.fixture
def mock_llm_response_invalid_json():
    """Fixture providing an invalid JSON LLM response."""
    return "This is not valid JSON"


@pytest.fixture
def mock_cache_manager():
    """Fixture providing a mocked cache manager."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


# ==================== Test Configuration ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "llm: marks tests that interact with LLM providers")
    config.addinivalue_line("markers", "medical: marks tests related to medical terminology")
    config.addinivalue_line("markers", "validation: marks tests for output validation")
    config.addinivalue_line("markers", "skill: marks tests for skill processing")
    config.addinivalue_line("markers", "async_test: marks async tests")


# ==================== Async Fixtures ====================

@pytest_asyncio.fixture
async def async_mock_provider():
    """Fixture providing an async mock LLM provider."""
    from app.services.llm_provider import MockProvider
    return MockProvider()


@pytest_asyncio.fixture
async def skill_processor_with_mock():
    """Fixture providing a skill processor with mock provider."""
    from app.services.skill_processor_enhanced import SkillProcessorEnhanced
    processor = SkillProcessorEnhanced(llm_provider="mock", enable_cache=False)
    return processor
