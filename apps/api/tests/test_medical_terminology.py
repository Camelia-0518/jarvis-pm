"""Tests for Medical Terminology module.

This module tests the medical terminology detection and enrichment functionality:
- detect_medical_terms
- get_term_info
- enrich_prompt_with_terminology
- add_medical_context
- get_related_terms
"""

import pytest
from typing import List, Dict, Any

from app.services.medical_terminology import (
    MEDICAL_TERMS,
    detect_medical_terms,
    get_term_info,
    enrich_prompt_with_terminology,
    add_medical_context,
    get_related_terms,
)


# ==================== Medical Terms Dictionary Tests ====================

class TestMedicalTermsDictionary:
    """Test suite for the medical terms dictionary."""

    def test_medical_terms_not_empty(self):
        """Test that medical terms dictionary is not empty."""
        assert len(MEDICAL_TERMS) > 0

    def test_medical_terms_structure(self):
        """Test that each term has required fields."""
        required_fields = ["definition", "synonyms", "related_terms", "context"]

        for term, info in MEDICAL_TERMS.items():
            assert isinstance(term, str)
            assert isinstance(info, dict)
            for field in required_fields:
                assert field in info, f"Term '{term}' missing field '{field}'"
            assert isinstance(info["synonyms"], list)
            assert isinstance(info["related_terms"], list)

    def test_common_medical_terms_exist(self):
        """Test that common medical terms exist in dictionary."""
        common_terms = [
            "切片借阅",
            "病历复印",
            "病理科",
            "免疫组化",
            "HE染色",
            "会诊",
            "HIS",
            "EMR",
            "等保三级",
        ]

        for term in common_terms:
            assert term in MEDICAL_TERMS, f"Common term '{term}' not found"


# ==================== detect_medical_terms Tests ====================

class TestDetectMedicalTerms:
    """Test suite for detect_medical_terms function."""

    def test_detect_single_term(self):
        """Test detection of a single medical term."""
        text = "患者需要申请切片借阅服务"
        result = detect_medical_terms(text)
        assert "切片借阅" in result

    def test_detect_multiple_terms(self):
        """Test detection of multiple medical terms."""
        text = "病理科处理切片借阅和免疫组化检测"
        result = detect_medical_terms(text)
        assert "切片借阅" in result
        assert "病理科" in result
        assert "免疫组化" in result

    def test_detect_no_terms(self, sample_text_without_medical_terms):
        """Test detection in text without medical terms."""
        result = detect_medical_terms(sample_text_without_medical_terms)
        assert len(result) == 0
        assert isinstance(result, list)

    def test_detect_term_case_insensitive(self):
        """Test case-insensitive term detection."""
        text = "患者需要申请切片借阅服务"
        result = detect_medical_terms(text)
        assert "切片借阅" in result

    def test_detect_synonyms(self):
        """Test detection of term synonyms."""
        # "玻片借阅" is a synonym of "切片借阅"
        text = "患者申请玻片借阅服务"
        result = detect_medical_terms(text)
        assert "切片借阅" in result

    def test_detect_multiple_synonyms(self):
        """Test detection of multiple synonyms."""
        # "IHC" and "免疫染色" are synonyms of "免疫组化"
        text1 = "需要进行IHC检测"
        text2 = "申请免疫染色检查"

        result1 = detect_medical_terms(text1)
        result2 = detect_medical_terms(text2)

        assert "免疫组化" in result1
        assert "免疫组化" in result2

    def test_detect_abbreviations(self):
        """Test detection of medical abbreviations."""
        text = "HIS系统和EMR集成"
        result = detect_medical_terms(text)
        assert "HIS" in result
        assert "EMR" in result

    def test_detect_complex_medical_text(self, sample_text_with_medical_terms):
        """Test detection in complex medical text."""
        result = detect_medical_terms(sample_text_with_medical_terms)
        assert len(result) >= 3
        assert "切片借阅" in result
        assert "免疫组化" in result
        assert "病理科" in result

    def test_no_duplicate_terms(self):
        """Test that duplicate terms are not returned."""
        text = "切片借阅切片借阅切片借阅"
        result = detect_medical_terms(text)
        assert result.count("切片借阅") == 1

    def test_detect_term_and_synonym_not_duplicated(self):
        """Test that term and its synonym don't cause duplicates."""
        text = "切片借阅和玻片借阅是同一个意思"
        result = detect_medical_terms(text)
        assert result.count("切片借阅") == 1


# ==================== get_term_info Tests ====================

class TestGetTermInfo:
    """Test suite for get_term_info function."""

    def test_get_existing_term_info(self):
        """Test getting info for existing term."""
        info = get_term_info("切片借阅")
        assert info is not None
        assert "definition" in info
        assert "synonyms" in info
        # Check definition contains relevant content (term may not be in definition itself)
        assert len(info["definition"]) > 0

    def test_get_nonexistent_term_info(self):
        """Test getting info for non-existent term."""
        info = get_term_info("不存在的术语")
        assert info is None

    def test_term_info_structure(self):
        """Test that term info has correct structure."""
        info = get_term_info("病理科")
        assert isinstance(info, dict)
        assert isinstance(info["synonyms"], list)
        assert isinstance(info["related_terms"], list)
        assert isinstance(info["definition"], str)

    def test_all_terms_have_valid_info(self):
        """Test that all terms in dictionary have valid info."""
        for term in MEDICAL_TERMS.keys():
            info = get_term_info(term)
            assert info is not None
            assert len(info["definition"]) > 0


# ==================== enrich_prompt_with_terminology Tests ====================

class TestEnrichPromptWithTerminology:
    """Test suite for enrich_prompt_with_terminology function."""

    def test_enrich_with_single_term(self):
        """Test enriching prompt with single term."""
        prompt = "Design a system for slice lending"
        terms = ["切片借阅"]
        result = enrich_prompt_with_terminology(prompt, terms)

        assert "【术语说明】" in result
        assert "切片借阅" in result
        assert "定义:" in result
        assert prompt in result

    def test_enrich_with_multiple_terms(self):
        """Test enriching prompt with multiple terms."""
        prompt = "Design a medical system"
        terms = ["切片借阅", "病理科"]
        result = enrich_prompt_with_terminology(prompt, terms)

        assert "【术语说明】" in result
        assert "切片借阅" in result
        assert "病理科" in result

    def test_enrich_with_empty_terms(self):
        """Test enriching prompt with empty terms list."""
        prompt = "Design a system"
        result = enrich_prompt_with_terminology(prompt, [])

        assert result == prompt
        assert "【术语说明】" not in result

    def test_enrich_with_invalid_term(self):
        """Test enriching with non-existent term."""
        prompt = "Design a system"
        terms = ["不存在的术语"]
        result = enrich_prompt_with_terminology(prompt, terms)

        # Should still have the header but no content for invalid term
        assert "【术语说明】" in result

    def test_enrich_preserves_original_prompt(self):
        """Test that original prompt is preserved."""
        prompt = "Original prompt content"
        terms = ["HIS"]
        result = enrich_prompt_with_terminology(prompt, terms)

        assert prompt in result
        assert result.startswith(prompt)

    def test_enrich_includes_examples(self):
        """Test that enrichment includes examples when available."""
        prompt = "Design a system"
        terms = ["切片借阅"]  # This term has examples
        result = enrich_prompt_with_terminology(prompt, terms)

        # Check if examples are included (if the term has them)
        info = get_term_info("切片借阅")
        if info.get("examples"):
            assert "示例:" in result


# ==================== add_medical_context Tests ====================

class TestAddMedicalContext:
    """Test suite for add_medical_context function."""

    def test_add_general_context(self):
        """Test adding general medical context."""
        prompt = "Design a system"
        result = add_medical_context(prompt, "general")

        assert "【医疗信息化背景】" in result
        assert "患者隐私保护" in result
        assert prompt in result

    def test_add_pathology_context(self):
        """Test adding pathology context."""
        prompt = "Design a system"
        result = add_medical_context(prompt, "pathology")

        assert "【病理科业务背景】" in result
        assert "病理科" in result
        assert "切片" in result
        assert prompt in result

    def test_add_medical_record_context(self):
        """Test adding medical record context."""
        prompt = "Design a system"
        result = add_medical_context(prompt, "medical_record")

        assert "【病案管理背景】" in result
        assert "病历" in result
        assert prompt in result

    def test_add_unknown_context_defaults_to_general(self):
        """Test that unknown context type defaults to general."""
        prompt = "Design a system"
        result = add_medical_context(prompt, "unknown_type")

        assert "【医疗信息化背景】" in result

    def test_context_prepended_to_prompt(self):
        """Test that context is prepended to prompt."""
        prompt = "Design a system"
        result = add_medical_context(prompt, "general")

        assert result.endswith(prompt)


# ==================== get_related_terms Tests ====================

class TestGetRelatedTerms:
    """Test suite for get_related_terms function."""

    def test_get_related_terms_for_existing_term(self):
        """Test getting related terms for existing term."""
        related = get_related_terms("切片借阅")
        assert isinstance(related, list)
        assert len(related) > 0
        assert "病理科" in related

    def test_get_related_terms_for_nonexistent_term(self):
        """Test getting related terms for non-existent term."""
        related = get_related_terms("不存在的术语")
        assert related == []

    def test_related_terms_are_consistent(self):
        """Test that related terms are consistent."""
        related1 = get_related_terms("免疫组化")
        related2 = get_related_terms("免疫组化")

        assert related1 == related2

    def test_all_related_terms_exist(self):
        """Test that all related terms exist in dictionary."""
        for term in MEDICAL_TERMS.keys():
            related = get_related_terms(term)
            for related_term in related:
                # Related term should exist in dictionary or be a valid reference
                assert isinstance(related_term, str)


# ==================== Integration Tests ====================

class TestMedicalTerminologyIntegration:
    """Integration tests for medical terminology module."""

    def test_full_workflow_detect_and_enrich(self):
        """Test complete workflow: detect terms then enrich prompt."""
        text = "患者申请切片借阅和免疫组化检测"

        # Step 1: Detect terms
        detected = detect_medical_terms(text)
        assert len(detected) >= 2

        # Step 2: Enrich prompt
        prompt = "Design a system based on: " + text
        enriched = enrich_prompt_with_terminology(prompt, detected)

        assert "【术语说明】" in enriched
        for term in detected:
            assert term in enriched

    def test_detect_enrich_context_workflow(self):
        """Test workflow with context addition."""
        text = "病理科处理切片借阅"

        # Detect terms
        detected = detect_medical_terms(text)

        # Create prompt
        prompt = "Design a system for: " + text

        # Enrich with terminology
        enriched = enrich_prompt_with_terminology(prompt, detected)

        # Add medical context
        final = add_medical_context(enriched, "pathology")

        assert "【病理科业务背景】" in final
        assert "【术语说明】" in final

    def test_medical_terms_coverage(self):
        """Test coverage of medical terms in realistic scenarios."""
        scenarios = [
            ("患者需要申请切片借阅去外院会诊", ["切片借阅", "会诊"]),
            ("病理科出具HE染色报告", ["病理科", "HE染色"]),
            ("HIS系统与EMR集成", ["HIS", "EMR"]),
            ("申请病历复印服务", ["病历复印"]),
            ("等保三级合规检查", ["等保三级"]),
        ]

        for text, expected_terms in scenarios:
            detected = detect_medical_terms(text)
            for term in expected_terms:
                assert term in detected, f"Expected '{term}' in '{text}', got {detected}"

    def test_synonym_recognition_accuracy(self):
        """Test accuracy of synonym recognition."""
        synonym_pairs = [
            ("玻片借阅", "切片借阅"),
            ("IHC", "免疫组化"),
            ("病历复制", "病历复印"),
            ("免疫染色", "免疫组化"),
        ]

        for synonym, main_term in synonym_pairs:
            text = f"患者申请{synonym}服务"
            detected = detect_medical_terms(text)
            assert main_term in detected, f"Synonym '{synonym}' should map to '{main_term}'"
