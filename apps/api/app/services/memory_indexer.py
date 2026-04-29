"""Memory Indexer Service

Indexes PRD content and other documents into semantic memory chunks
for vector-based retrieval.
"""

import json
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.memory_chunk import MemoryChunk

logger = logging.getLogger(__name__)

# Chunking config
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by sentence boundaries."""
    if not text or not text.strip():
        return []

    # Simple paragraph-based chunking
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single paragraph exceeds chunk_size, split by sentences
            if len(para) > chunk_size:
                sentences = para.replace("。", "。\n").replace(".", ".\n").replace("!", "!\n").replace("?", "?\n").split("\n")
                current_chunk = ""
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(current_chunk) + len(sent) + 1 <= chunk_size:
                        current_chunk = (current_chunk + " " + sent).strip() if current_chunk else sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    # Apply overlap: merge adjacent chunks with overlap
    if overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
            else:
                prev = chunks[i - 1]
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                overlapped.append(overlap_text + "\n" + chunk)
        chunks = overlapped

    return chunks


class MemoryIndexer:
    """Indexes documents into semantic memory chunks for retrieval."""

    def __init__(self):
        self._embedder: Optional[Any] = None
        self._embedding_available = False

    async def _get_embedder(self) -> Optional[Any]:
        """Lazy-load sentence-transformers embedder."""
        if self._embedder is not None:
            return self._embedder

        try:
            from sentence_transformers import SentenceTransformer
            # Use a lightweight multilingual model
            model_name = "all-MiniLM-L6-v2"
            self._embedder = SentenceTransformer(model_name)
            self._embedding_available = True
            logger.info("Embedding model loaded: %s", model_name)
            return self._embedder
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", e)
            self._embedding_available = False
            return None

    async def index_document(
        self,
        db: AsyncSession,
        source_type: str,
        source_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Index a document into semantic memory chunks.

        Returns:
            Number of chunks indexed.
        """
        # Delete existing chunks for this source
        await db.execute(
            delete(MemoryChunk).where(
                MemoryChunk.source_type == source_type,
                MemoryChunk.source_id == source_id,
            )
        )

        chunks = _split_text(content)
        if not chunks:
            return 0

        # Generate embeddings if available
        embedder = await self._get_embedder()
        embeddings: Optional[List[List[float]]] = None
        if embedder is not None:
            try:
                import numpy as np
                vectors = embedder.encode(
                    chunks,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                embeddings = vectors.tolist()
            except Exception as e:
                logger.warning("Failed to generate embeddings: %s", e)

        # Store chunks
        for idx, chunk_text in enumerate(chunks):
            chunk = MemoryChunk(
                source_type=source_type,
                source_id=source_id,
                chunk_index=idx,
                content=chunk_text[:4000],  # Safety limit
                embedding=json.dumps(embeddings[idx]) if embeddings and idx < len(embeddings) else None,
                chunk_metadata=json.dumps(metadata or {}),
            )
            db.add(chunk)

        await db.commit()
        logger.info("Indexed %d chunks for %s:%s", len(chunks), source_type, source_id)
        return len(chunks)

    async def delete_document_index(
        self,
        db: AsyncSession,
        source_type: str,
        source_id: str,
    ) -> None:
        """Remove all indexed chunks for a document."""
        await db.execute(
            delete(MemoryChunk).where(
                MemoryChunk.source_type == source_type,
                MemoryChunk.source_id == source_id,
            )
        )
        await db.commit()
        logger.info("Deleted index for %s:%s", source_type, source_id)

    async def semantic_search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        source_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search indexed chunks by semantic similarity.

        Falls back to keyword matching if embeddings are unavailable.
        """
        query = query.strip()
        if not query:
            return []

        # Build base query
        stmt = select(MemoryChunk)
        if source_type:
            stmt = stmt.where(MemoryChunk.source_type == source_type)

        result = await db.execute(stmt)
        chunks = result.scalars().all()
        if not chunks:
            return []

        # Try semantic search with embeddings
        embedder = await self._get_embedder()
        if embedder is not None:
            try:
                import numpy as np
                query_embedding = embedder.encode(
                    [query],
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )[0]

                scored = []
                for chunk in chunks:
                    if chunk.embedding:
                        try:
                            chunk_embedding = np.array(json.loads(chunk.embedding))
                            score = float(np.dot(query_embedding, chunk_embedding))
                            if score > 0:
                                scored.append((chunk, score))
                        except (json.JSONDecodeError, ValueError):
                            continue

                scored.sort(key=lambda x: x[1], reverse=True)
                return [
                    {
                        "id": c.id,
                        "source_type": c.source_type,
                        "source_id": c.source_id,
                        "content": c.content,
                        "score": round(score, 4),
                        "metadata": json.loads(c.chunk_metadata) if c.chunk_metadata else {},
                    }
                    for c, score in scored[:top_k]
                ]
            except Exception as e:
                logger.warning("Semantic search failed, falling back to keyword: %s", e)

        # Fallback: keyword matching (Jaccard similarity)
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return []

        scored = []
        for chunk in chunks:
            chunk_tokens = set(_tokenize(chunk.content))
            intersection = query_tokens & chunk_tokens
            union = query_tokens | chunk_tokens
            score = len(intersection) / len(union) if union else 0.0
            if score > 0:
                scored.append((chunk, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "id": c.id,
                "source_type": c.source_type,
                "source_id": c.source_id,
                "content": c.content,
                "score": round(score, 4),
                "metadata": json.loads(c.metadata) if c.metadata else {},
            }
            for c, score in scored[:top_k]
        ]


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer for fallback keyword matching."""
    import re
    chinese_chars = list(re.findall(r"[一-鿿]", text))
    english_words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return chinese_chars + english_words


# Global indexer instance
memory_indexer = MemoryIndexer()
