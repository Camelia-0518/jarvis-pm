"""
RAG 检索引擎

基于语义向量（sentence-transformers）+ TF-IDF + 关键词匹配的混合检索。
轻量、优先本地计算，适合 Jarvis PM 的文档规模。
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import re

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class RetrievalResult(BaseModel):
    """检索结果"""
    doc_id: str = Field(description="文档ID")
    content: str = Field(description="文档内容")
    score: float = Field(default=0.0, description="相似度得分 0-1")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalEngine:
    """基于语义向量 + TF-IDF 的混合检索引擎"""

    def __init__(
        self,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
        enable_embedding: bool = True,
    ):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.vectorizer: Optional[Any] = None
        self.doc_matrix: Optional[Any] = None
        self._dirty = True

        # Embedding related
        self._enable_embedding = enable_embedding and SENTENCE_TRANSFORMERS_AVAILABLE
        self._embedding_model_name = embedding_model
        self.embedder: Optional[Any] = None
        self.embeddings: Optional[Any] = None

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """添加文档"""
        if not content or not content.strip():
            logger.warning("Skipping empty document: %s", doc_id)
            return

        self.documents[doc_id] = {
            "content": content.strip(),
            "metadata": metadata or {},
        }
        self._dirty = True
        logger.debug("Added document: %s", doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id not in self.documents:
            return False
        del self.documents[doc_id]
        self._dirty = True
        logger.debug("Deleted document: %s", doc_id)
        return True

    def clear(self) -> None:
        """清空所有文档"""
        self.documents.clear()
        self.vectorizer = None
        self.doc_matrix = None
        self.embeddings = None
        self._dirty = True

    def search(self, query: str, top_k: int = 3) -> List[RetrievalResult]:
        """
        检索相关文档。

        策略（按优先级）：
        1. 语义向量检索（sentence-transformers，最佳语义匹配）
        2. TF-IDF + cosine similarity（sklearn 可用且文档数 >= 2）
        3. 关键词匹配（Jaccard similarity，fallback）
        """
        if not self.documents:
            return []

        query = query.strip()
        if not query:
            return []

        # 1. 优先语义检索
        if self._enable_embedding and self._ensure_embedder():
            try:
                return self._semantic_search(query, top_k)
            except Exception as e:
                logger.warning("Semantic search failed: %s, falling back", e)

        # 2. TF-IDF 向量检索
        if SKLEARN_AVAILABLE and len(self.documents) >= 2:
            return self._vector_search(query, top_k)

        # 3. 关键词匹配 fallback
        return self._keyword_search(query, top_k)

    def _ensure_embedder(self) -> bool:
        """延迟初始化 embedder"""
        if self.embedder is not None:
            return True
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            return False
        try:
            logger.info("Loading embedding model: %s", self._embedding_model_name)
            self.embedder = SentenceTransformer(self._embedding_model_name)
            logger.info("Embedding model loaded successfully")
            return True
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", e)
            self._enable_embedding = False
            return False

    def _build_index(self) -> None:
        """构建/重建索引（TF-IDF + Embedding）"""
        if not self._dirty or not self.documents:
            return

        contents = [d["content"] for d in self.documents.values()]

        # Build TF-IDF index
        if SKLEARN_AVAILABLE:
            if JIEBA_AVAILABLE:
                def _jieba_tokenize(text: str) -> List[str]:
                    return [
                        t.strip()
                        for t in jieba.cut(text)
                        if t.strip() and not t.strip().isspace()
                    ]

                self.vectorizer = TfidfVectorizer(
                    tokenizer=_jieba_tokenize,
                    preprocessor=None,
                    token_pattern=None,
                    min_df=1,
                )
            else:
                self.vectorizer = TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 4),
                    min_df=1,
                )
            self.doc_matrix = self.vectorizer.fit_transform(contents)

        # Build Embedding index
        if self._enable_embedding and self._ensure_embedder():
            try:
                import numpy as np
                self.embeddings = self.embedder.encode(
                    contents,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
            except Exception as e:
                logger.warning("Failed to build embedding index: %s", e)
                self.embeddings = None

        self._dirty = False

    def _semantic_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """语义向量检索"""
        self._build_index()
        if self.embeddings is None or self.embedder is None:
            return []

        import numpy as np

        query_embedding = self.embedder.encode(
            [query],
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        # cosine similarity with normalized vectors = dot product
        scores = np.dot(self.embeddings, query_embedding[0])

        doc_ids = list(self.documents.keys())
        scored = [
            (doc_ids[i], float(scores[i]))
            for i in range(len(doc_ids))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in scored[:top_k]:
            if score > 0:
                doc = self.documents[doc_id]
                results.append(
                    RetrievalResult(
                        doc_id=doc_id,
                        content=doc["content"],
                        score=round(score, 4),
                        metadata=doc["metadata"],
                    )
                )
        return results

    def _vector_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """TF-IDF 向量检索"""
        self._build_index()

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.doc_matrix)[0]

        doc_ids = list(self.documents.keys())
        scored = [
            (doc_ids[i], float(scores[i]))
            for i in range(len(doc_ids))
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in scored[:top_k]:
            if score > 0:
                doc = self.documents[doc_id]
                results.append(
                    RetrievalResult(
                        doc_id=doc_id,
                        content=doc["content"],
                        score=round(score, 4),
                        metadata=doc["metadata"],
                    )
                )
        return results

    def _keyword_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """关键词检索（fallback）"""
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return []

        scored = []
        for doc_id, doc in self.documents.items():
            doc_tokens = set(self._tokenize(doc["content"]))
            intersection = query_tokens & doc_tokens
            union = query_tokens | doc_tokens
            score = len(intersection) / len(union) if union else 0.0
            scored.append((doc_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in scored[:top_k]:
            if score > 0:
                doc = self.documents[doc_id]
                results.append(
                    RetrievalResult(
                        doc_id=doc_id,
                        content=doc["content"],
                        score=round(score, 4),
                        metadata=doc["metadata"],
                    )
                )
        return results

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """中文/英文分词，优先使用 jieba"""
        if JIEBA_AVAILABLE:
            try:
                return [
                    t.strip()
                    for t in jieba.cut(text.strip())
                    if t.strip() and not t.strip().isspace()
                ]
            except Exception:
                pass

        chinese_chars = list(re.findall(r"[\u4e00-\u9fff]", text))
        english_words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return chinese_chars + english_words
