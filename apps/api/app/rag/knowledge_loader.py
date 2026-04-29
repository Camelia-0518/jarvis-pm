"""
Obsidian 知识库加载器

从 Obsidian Vault 读取 Markdown 文档并加载到 RetrievalEngine。
支持启动时全量加载 + 运行时基于 watchdog 的热重载。
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Any

from app.rag.retrieval.engine import RetrievalEngine

logger = logging.getLogger(__name__)

DEFAULT_VAULT_PATH = r"C:\Users\13400\Documents\Obsidian\MyVault"
DEFAULT_INCLUDE_DIRS = ["04-项目层", "05-知识层", "06-经验层"]


# Industry keyword mapping for automatic document tagging
_INDUSTRY_KEYWORDS = {
    "medical": [
        "医疗", "医院", "病理", "切片", "患者", "医生", "护士", "医护",
        "挂号", "就诊", "病历", "病案", "HIS", "医保", "药品",
        "检验", "检查", "处方", "住院", "门诊", "科室", "急诊",
        "medical", "hospital", "pathology", "patient", "doctor", "nurse",
        "healthcare", "clinical", "diagnosis", "prescription", "emr", "lis"
    ],
    "ecommerce": [
        "电商", "商品", "订单", "购物车", "支付", "物流", "库存",
        "促销", "优惠券", "会员", "商家", "平台", "SKU", "GMV",
        "ecommerce", "shop", "product", "order", "cart",
        "payment", "shipping", "inventory", "merchant"
    ],
    "saas": [
        "SaaS", "租户", "订阅", "MRR", "ARR", "NPS", "CAC",
        "onboarding", "activation", "retention", "churn",
        "多租户", "付费转化", "续费", "SLA", "API平台"
    ],
    "education": [
        "教育", "学校", "学生", "教师", "课程", "考试", "学习",
        "培训", "在线", "课堂", "作业", "成绩", "校园",
        "education", "school", "student", "teacher", "course",
        "learning", "training", "classroom", "academic"
    ],
    "finance": [
        "金融", "银行", "支付", "理财", "保险", "证券", "投资",
        "贷款", "信用卡", "转账", "风控", "合规", "反洗钱",
        "finance", "bank", "payment", "insurance", "investment",
        "trading", "risk", "compliance", "aml"
    ],
}


def _detect_industry(text: str) -> list[str]:
    """Detect industries mentioned in text based on keyword matching."""
    text_lower = text.lower()
    matched = []
    for industry, keywords in _INDUSTRY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(industry)
    return matched


def load_obsidian_documents(
    engine: RetrievalEngine,
    vault_path: Optional[str] = None,
    include_dirs: Optional[list[str]] = None,
) -> int:
    """
    从 Obsidian Vault 加载 Markdown 文档到检索引擎。

    Args:
        engine: RetrievalEngine 实例
        vault_path: Vault 根目录，默认使用 DEFAULT_VAULT_PATH
        include_dirs: 要扫描的子目录列表，默认使用 DEFAULT_INCLUDE_DIRS

    Returns:
        成功加载的文档数量
    """
    vault_path = vault_path or DEFAULT_VAULT_PATH
    include_dirs = include_dirs or DEFAULT_INCLUDE_DIRS
    vault = Path(vault_path)

    if not vault.exists() or not vault.is_dir():
        logger.warning("Obsidian vault not found at %s, skipping knowledge loading.", vault_path)
        return 0

    loaded = 0
    for subdir in include_dirs:
        target = vault / subdir
        if not target.exists():
            logger.debug("Vault subdirectory not found: %s", target)
            continue

        for md_file in target.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if not content.strip():
                    continue

                rel_path = md_file.relative_to(vault).as_posix()
                doc_id = f"obsidian::{rel_path}"

                # Auto-detect industry tags from path + filename + first 500 chars of content
                detect_text = f"{rel_path} {md_file.name} {content[:500]}"
                industries = _detect_industry(detect_text)

                engine.add_document(
                    doc_id=doc_id,
                    content=content,
                    metadata={
                        "source": "obsidian",
                        "path": rel_path,
                        "filename": md_file.name,
                        "industries": industries,
                    },
                )
                loaded += 1
            except Exception as e:
                logger.warning("Failed to load %s: %s", md_file, e)

    logger.info("Loaded %d documents from Obsidian vault.", loaded)
    return loaded


# ============== Watchdog-based hot reload ==============

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore


class _VaultEventHandler(FileSystemEventHandler):  # type: ignore[misc]
    """处理 Vault 文件变更事件"""

    def __init__(
        self,
        engine: RetrievalEngine,
        vault: Path,
        include_dirs: List[str],
    ):
        self.engine = engine
        self.vault = vault
        self.include_dirs = set(include_dirs)

    def _rel_path(self, path: Path) -> Optional[str]:
        try:
            return path.relative_to(self.vault).as_posix()
        except ValueError:
            return None

    def _is_target(self, path: Path) -> bool:
        rel = self._rel_path(path)
        if not rel:
            return False
        parts = Path(rel).parts
        if not parts:
            return False
        return parts[0] in self.include_dirs and path.suffix.lower() == ".md"

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._is_target(path):
            self._add_document(path)

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._is_target(path):
            self._add_document(path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if self._is_target(path):
            rel = self._rel_path(path)
            if rel:
                doc_id = f"obsidian::{rel}"
                self.engine.delete_document(doc_id)
                logger.info("Deleted from RAG: %s", doc_id)

    def on_moved(self, event):
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        if self._is_target(src_path):
            rel = self._rel_path(src_path)
            if rel:
                self.engine.delete_document(f"obsidian::{rel}")
        if self._is_target(dest_path):
            self._add_document(dest_path)

    def _add_document(self, path: Path):
        try:
            content = path.read_text(encoding="utf-8")
            if not content.strip():
                rel = self._rel_path(path)
                if rel:
                    self.engine.delete_document(f"obsidian::{rel}")
                return

            rel = path.relative_to(self.vault).as_posix()
            doc_id = f"obsidian::{rel}"

            # Auto-detect industry tags from path + filename + first 500 chars
            detect_text = f"{rel} {path.name} {content[:500]}"
            industries = _detect_industry(detect_text)

            self.engine.add_document(
                doc_id=doc_id,
                content=content,
                metadata={
                    "source": "obsidian",
                    "path": rel,
                    "filename": path.name,
                    "industries": industries,
                },
            )
            logger.info("Updated RAG document: %s", doc_id)
        except Exception as e:
            logger.warning("Failed to update %s: %s", path, e)


class ObsidianWatcher:
    """基于 watchdog 的 Vault 文件监控器"""

    def __init__(
        self,
        engine: RetrievalEngine,
        vault_path: Optional[str] = None,
        include_dirs: Optional[List[str]] = None,
    ):
        self.engine = engine
        self.vault_path = Path(vault_path or DEFAULT_VAULT_PATH)
        self.include_dirs = include_dirs or DEFAULT_INCLUDE_DIRS
        self._observer: Optional[Any] = None

    def start(self) -> bool:
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog not installed, skipping vault watcher")
            return False

        if not self.vault_path.exists() or not self.vault_path.is_dir():
            logger.warning("Vault not found at %s, skipping watcher", self.vault_path)
            return False

        self._observer = Observer()
        handler = _VaultEventHandler(self.engine, self.vault_path, self.include_dirs)
        scheduled = False
        for subdir in self.include_dirs:
            target = self.vault_path / subdir
            if target.exists():
                self._observer.schedule(handler, str(target), recursive=True)
                logger.info("Watching vault directory: %s", target)
                scheduled = True

        if scheduled:
            self._observer.start()
            return True
        return False

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Vault watcher stopped")
