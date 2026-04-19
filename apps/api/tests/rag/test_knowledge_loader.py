"""Tests for RAG knowledge loader."""

import pytest
from pathlib import Path

from app.rag.retrieval.engine import RetrievalEngine
from app.rag.knowledge_loader import load_obsidian_documents


class TestKnowledgeLoader:
    def test_load_from_nonexistent_vault(self):
        engine = RetrievalEngine()
        count = load_obsidian_documents(engine, vault_path="/does/not/exist")
        assert count == 0
        assert engine.search("anything") == []

    def test_load_from_temp_vault(self, tmp_path):
        # Create a mock vault structure
        vault = tmp_path / "MyVault"
        projects = vault / "04-项目层"
        projects.mkdir(parents=True)

        md1 = projects / "切片借阅平台.md"
        md1.write_text("# 切片借阅平台\n\n这是一个医疗项目。", encoding="utf-8")

        md2 = projects / "sub" / "病案复印.md"
        md2.parent.mkdir(parents=True)
        md2.write_text("# 病案复印\n\n患者在线申请病历复印。", encoding="utf-8")

        engine = RetrievalEngine()
        count = load_obsidian_documents(
            engine,
            vault_path=str(vault),
            include_dirs=["04-项目层"],
        )
        assert count == 2

        results = engine.search("切片借阅", top_k=1)
        assert len(results) == 1
        assert "切片借阅平台" in results[0].content
        assert results[0].metadata["filename"] == "切片借阅平台.md"

    def test_skips_empty_files(self, tmp_path):
        vault = tmp_path / "MyVault"
        projects = vault / "04-项目层"
        projects.mkdir(parents=True)

        empty_md = projects / "empty.md"
        empty_md.write_text("   \n\n  ", encoding="utf-8")

        valid_md = projects / "valid.md"
        valid_md.write_text("有内容", encoding="utf-8")

        engine = RetrievalEngine()
        count = load_obsidian_documents(
            engine,
            vault_path=str(vault),
            include_dirs=["04-项目层"],
        )
        assert count == 1

    def test_respects_include_dirs(self, tmp_path):
        vault = tmp_path / "MyVault"
        (vault / "04-项目层").mkdir(parents=True)
        (vault / "07-任务层").mkdir(parents=True)

        (vault / "04-项目层" / "a.md").write_text("项目文档", encoding="utf-8")
        (vault / "07-任务层" / "b.md").write_text("任务文档", encoding="utf-8")

        engine = RetrievalEngine()
        count = load_obsidian_documents(
            engine,
            vault_path=str(vault),
            include_dirs=["04-项目层"],
        )
        assert count == 1
        results = engine.search("项目")
        assert len(results) == 1
        assert results[0].metadata["path"] == "04-项目层/a.md"
