"""RAG retrieval endpoints"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import ResponseBuilder

router = APIRouter()

# Lazy-loaded engine wrapper - avoids heavy model loading at import time
class _LazyEngine:
    def __init__(self):
        self._engine = None

    def _ensure(self):
        if self._engine is None:
            from app.rag.retrieval.engine import RetrievalEngine
            self._engine = RetrievalEngine()
        return self._engine

    def search(self, query, top_k=5):
        return self._ensure().search(query, top_k=top_k)

    def add_document(self, doc_id, content, metadata=None):
        return self._ensure().add_document(doc_id, content, metadata=metadata)

    def delete_document(self, doc_id):
        return self._ensure().delete_document(doc_id)

    def clear(self):
        return self._ensure().clear()

    @property
    def documents(self):
        return self._ensure().documents

retrieval_engine = _LazyEngine()

def get_retrieval_engine():
    return retrieval_engine


class SearchRequest(BaseModel):
    query: str = Field(..., description="检索关键词")
    top_k: int = Field(default=3, ge=1, le=10, description="返回结果数量")


class SearchResultItem(BaseModel):
    doc_id: str
    content: str
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """在 Obsidian 知识库中检索相关文档"""
    try:
        results = get_retrieval_engine().search(request.query, top_k=request.top_k)
        return SearchResponse(
            query=request.query,
            results=[
                SearchResultItem(
                    doc_id=r.doc_id,
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                )
                for r in results
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.post("/query", response_model=SearchResponse)
async def query_documents(request: SearchRequest):
    """在 Obsidian 知识库中检索相关文档（/search 的别名）"""
    return await search_documents(request)


# ==================== Semantic Memory Search ====================

class MemorySearchRequest(BaseModel):
    query: str = Field(..., description="语义查询")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    source_type: Optional[str] = Field(default=None, description="按来源过滤: prd, project, knowledge")


class MemorySearchResultItem(BaseModel):
    id: str
    source_type: str
    source_id: str
    content: str
    score: float
    metadata: dict


class MemorySearchResponse(BaseModel):
    query: str
    results: List[MemorySearchResultItem]


@router.post("/memory-search", response_model=MemorySearchResponse)
async def memory_search(
    request: MemorySearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """语义记忆检索 - 在已索引的 PRD/项目/知识库中搜索相关内容"""
    try:
        from app.services.memory_indexer import memory_indexer
        results = await memory_indexer.semantic_search(
            db=db,
            query=request.query,
            top_k=request.top_k,
            source_type=request.source_type,
        )
        return MemorySearchResponse(
            query=request.query,
            results=[
                MemorySearchResultItem(
                    id=r["id"],
                    source_type=r["source_type"],
                    source_id=r["source_id"],
                    content=r["content"],
                    score=r["score"],
                    metadata=r.get("metadata", {}),
                )
                for r in results
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语义检索失败: {str(e)}")


@router.post("/memory-search/query", response_model=MemorySearchResponse)
async def memory_search_query(
    request: MemorySearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """语义记忆检索（/memory-search 的别名）"""
    return await memory_search(request, db)


@router.post("/memory-index/{source_type}/{source_id}", response_model=dict)
async def index_memory_document(
    source_type: str,
    source_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db)
):
    """手动索引文档到语义记忆"""
    content = data.get("content", "")
    if not content:
        return ResponseBuilder.error(code="INVALID", message="content is required")

    try:
        from app.services.memory_indexer import memory_indexer
        count = await memory_indexer.index_document(
            db=db,
            source_type=source_type,
            source_id=source_id,
            content=content,
            metadata=data.get("metadata", {}),
        )
        return ResponseBuilder.success({
            "indexed_chunks": count,
            "source_type": source_type,
            "source_id": source_id,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"索引失败: {str(e)}")


@router.delete("/memory-index/{source_type}/{source_id}", response_model=dict)
async def delete_memory_index(
    source_type: str,
    source_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除文档的语义记忆索引"""
    try:
        from app.services.memory_indexer import memory_indexer
        await memory_indexer.delete_document_index(db, source_type, source_id)
        return ResponseBuilder.success({
            "message": "索引已删除",
            "source_type": source_type,
            "source_id": source_id,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除索引失败: {str(e)}")
