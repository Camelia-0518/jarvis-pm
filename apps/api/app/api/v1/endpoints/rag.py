"""RAG retrieval endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from app.rag.retrieval.engine import RetrievalEngine, RetrievalResult

router = APIRouter()

# Global engine instance populated at startup
retrieval_engine = RetrievalEngine()


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
        results = retrieval_engine.search(request.query, top_k=request.top_k)
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
