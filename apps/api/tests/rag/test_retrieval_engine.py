"""Tests for RAG retrieval engine."""

import pytest
from app.rag.retrieval.engine import RetrievalEngine, RetrievalResult


class TestRetrievalEngine:
    def test_add_and_search_document(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "病案复印系统需求文档", {"type": "prd"})
        engine.add_document("doc2", "消息推送平台技术方案", {"type": "tech"})

        results = engine.search("病案复印", top_k=2)
        assert len(results) > 0
        assert results[0].doc_id == "doc1"
        assert results[0].score > 0

    def test_search_empty_engine(self):
        engine = RetrievalEngine()
        assert engine.search("anything") == []

    def test_delete_document(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "test content")
        assert engine.delete_document("doc1") is True
        assert engine.search("test") == []

    def test_delete_nonexistent(self):
        engine = RetrievalEngine()
        assert engine.delete_document("missing") is False

    def test_clear(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "test")
        engine.clear()
        assert engine.search("test") == []

    def test_keyword_fallback_with_single_doc(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "病案复印申请流程")
        results = engine.search("病案")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    def test_metadata_preserved(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "content", {"author": "pm"})
        results = engine.search("content")
        assert results[0].metadata["author"] == "pm"

    def test_empty_content_skipped(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "")
        engine.add_document("doc2", "   ")
        assert engine.search("anything") == []

    def test_empty_query(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "test")
        assert engine.search("") == []
        assert engine.search("   ") == []

    def test_vector_search_ranks_correctly(self):
        engine = RetrievalEngine()
        engine.add_document("doc1", "病案复印系统用于患者申请病历复印")
        engine.add_document("doc2", "消息推送平台发送短信和APP通知")
        engine.add_document("doc3", "医院管理系统包含病案管理和复印审批")

        results = engine.search("病案复印", top_k=3)
        # 不相关的 doc2 应被过滤，只返回得分 > 0 的结果
        assert len(results) >= 1
        returned_ids = {r.doc_id for r in results}
        assert "doc2" not in returned_ids
        assert results[0].doc_id in ("doc1", "doc3")
        assert all(isinstance(r, RetrievalResult) for r in results)
