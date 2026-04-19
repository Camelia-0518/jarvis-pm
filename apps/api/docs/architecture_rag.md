# Enterprise Knowledge Base RAG Architecture

> Task 13: Enterprise Knowledge Base RAG for Jarvis PM  
> Status: Design Document  
> Author: Architect  
> Date: 2026-04-15

---

## 1. System Overview

### 1.1 Problem Statement

Current AI-generated content (PRDs, user research, compliance checks) in Jarvis PM suffers from hallucinations because the LLM has no access to:
- Historical PRDs and product documents
- Company compliance templates and SOPs
- Real-world user research and interview notes
- Industry-specific terminology and standards

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Jarvis PM RAG System                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│   │   Upload    │───▶│  Document   │───▶│   Chunk &   │───▶│  Embedding  │  │
│   │    UI       │    │   Parser    │    │   Extract   │    │   Engine    │  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        │                      │                  │                 │         │
│        │                      │                  │                 │         │
│        ▼                      ▼                  ▼                 ▼         │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                        PostgreSQL + Vector Store                     │    │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │    │
│   │  │ knowledge_docs  │  │ knowledge_chunks│  │    embeddings       │  │    │
│   │  │  (metadata)     │  │  (text chunks)  │  │  (tf-idf / vector)  │  │    │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                      ▲                                       │
│                                      │                                       │
│   ┌─────────────┐    ┌─────────────┐│    ┌─────────────┐    ┌─────────────┐  │
│   │   Prompt    │◄───│   Context   │◄────│  Retrieval  │◄───│    Query    │  │
│   │  Augmenter  │    │   Builder   │     │   Engine    │    │  Rewriter   │  │
│   └─────────────┘    └─────────────┘     └─────────────┘    └─────────────┘  │
│          │                                                                  │
│          ▼                                                                  │
│   ┌─────────────┐                                                           │
│   │     LLM     │                                                           │
│   │  (Kimi/    │                                                           │
│   │  Claude)   │                                                           │
│   └─────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow

1. **Ingestion**: User uploads documents (PDF, Word, Markdown, TXT) via frontend or admin bulk-imports Obsidian vault
2. **Parsing**: Document parsers extract raw text and metadata
3. **Chunking**: Text is split into semantic or fixed-size chunks with overlap
4. **Embedding**: Chunks are converted to vectors (TF-IDF or dense embeddings)
5. **Storage**: Documents, chunks, and embeddings are persisted to PostgreSQL + optional vector store
6. **Retrieval**: On AI generation requests, queries are rewritten and matched against the vector index
7. **Augmentation**: Top-K chunks are injected into the LLM system prompt as retrieved context
8. **Generation**: LLM produces grounded, citation-aware output

---

## 2. Document Ingestion Pipeline

### 2.1 Supported Formats

| Format | Parser Library | Notes |
|--------|----------------|-------|
| PDF | `PyPDF2` / `pdfplumber` | Text extraction; tables as markdown |
| Word (.docx) | `python-docx` | Paragraphs, headings, tables |
| Markdown | Native | Frontmatter parsed for metadata |
| TXT | Native | UTF-8 encoding assumed |

**MVP scope**: Markdown + TXT only (no new dependencies).  
**V1 scope**: Add PDF + Word support.

### 2.2 Document Parser Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class ParsedDocument:
    title: str
    content: str
    metadata: Dict[str, Any]
    pages: List[str]  # per-page or per-section content

class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        ...

class MarkdownParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        import frontmatter
        with open(file_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
        return ParsedDocument(
            title=post.get("title", ""),
            content=post.content,
            metadata=dict(post.metadata),
            pages=[post.content],
        )

class TextParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ParsedDocument(
            title="",
            content=content,
            metadata={},
            pages=[content],
        )
```

### 2.3 Chunking Strategy

#### Option A: Fixed-Size with Overlap (MVP)

```python
def chunk_fixed_size(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """Split text into fixed-size chunks with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
```

- **Pros**: Simple, deterministic, fast
- **Cons**: May cut sentences/paragraphs mid-thought

#### Option B: Semantic Chunking (V1)

```python
def chunk_semantic(text: str, max_chunk_size: int = 512) -> List[str]:
    """Split by paragraphs/headings, respecting max size."""
    import re
    # Split by markdown headers or double newlines
    sections = re.split(r"\n(?=#{1,6}\s)", text)
    chunks = []
    current = ""
    for section in sections:
        if len(current) + len(section) > max_chunk_size:
            if current:
                chunks.append(current.strip())
            current = section
        else:
            current += "\n\n" + section
    if current:
        chunks.append(current.strip())
    return chunks
```

- **Pros**: Preserves semantic boundaries (headers, paragraphs)
- **Cons**: Slightly more complex, variable chunk sizes

**Recommendation**: Use **fixed-size with overlap for MVP**, switch to **semantic chunking for V1**.

### 2.4 Metadata Extraction

Every document and chunk carries metadata:

| Field | Source | Example |
|-------|--------|---------|
| `project_id` | Upload UI selection or frontmatter | `"proj_123"` |
| `doc_type` | Frontmatter tag or filename pattern | `"PRD"`, `"合规文档"`, `"流程图"`, `"用户调研"` |
| `upload_date` | Server timestamp | `2026-04-15T10:30:00Z` |
| `author` | Frontmatter or uploader | `"张三"` |
| `source` | System origin | `"upload"`, `"obsidian"` |
| `filename` | Original file name | `"slice-lending-prd-v2.md"` |

```python
@dataclass
class DocumentMetadata:
    project_id: str | None
    doc_type: str
    upload_date: str
    author: str | None
    source: str
    filename: str
```

---

## 3. Embedding & Storage Options

### 3.1 Option A: TF-IDF + Cosine Similarity (MVP)

**Already implemented** in `app/rag/retrieval/engine.py`.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)
doc_matrix = vectorizer.fit_transform(chunks)
```

**Pros**:
- `scikit-learn==1.4.0` already installed
- Zero new dependencies
- Fast for small-to-medium document sets (<10k chunks)
- Works well for Chinese keyword matching with `char_wb` analyzer

**Cons**:
- No semantic understanding ("患者隐私" vs "数据保护" may not match)
- Performance degrades with large vocabulary
- No out-of-vocabulary generalization

### 3.2 Option B: Dense Embeddings + Vector DB (V1)

**Embedding Model**: `sentence-transformers` with a multilingual model

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")  # or "paraphrase-multilingual-MiniLM-L12-v2"
embeddings = model.encode(chunks, normalize_embeddings=True)
```

**Vector Store Options**:

| Store | Pros | Cons |
|-------|------|------|
| **ChromaDB** | Easy Python API, persistent, good docs | Extra process/service |
| **FAISS-CPU** | Facebook出品, extremely fast, in-memory | No native persistence, manual save/load |
| **pgvector** | Stays in PostgreSQL, ACID, no new infra | Requires PostgreSQL extension |

**Recommended V1 Stack**: `sentence-transformers` + `chromadb`

```python
import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma_db"))
collection = client.get_or_create_collection(name="jarvis_kb")

collection.add(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    embeddings=embeddings.tolist(),
    metadatas=metadatas,
)
```

### 3.3 Recommendation & Trade-offs

| Criterion | TF-IDF (MVP) | Dense + Chroma (V1) |
|-----------|--------------|---------------------|
| Setup time | 0 days | 1 day |
| New dependencies | 0 | 2-3 |
| Semantic search | Poor | Excellent |
| Chinese support | Good (char n-grams) | Excellent (bge-m3) |
| Scale | <10k chunks | >100k chunks |
| Maintenance | Minimal | Low |

**Decision**:
- **MVP**: Extend existing TF-IDF engine to support chunk-level storage and project-scoped retrieval. Ship in 1-2 days.
- **V1**: Migrate to `sentence-transformers` + `ChromaDB` with `bge-m3` model. Budget 1 week.

---

## 4. Retrieval Strategy

### 4.1 Trigger Points

RAG retrieval should run **before** the following AI calls in `ai_service.py`:

| Function | Trigger Condition | Query Source |
|----------|-------------------|--------------|
| `generate_prd()` | Always | `title + description + industry` |
| `generate_prd_chapter()` | Always | `chapter focus + prompt` |
| `chat()` | If message contains PRD/compliance/research intent | User message |
| `generate_review_material()` | Optional | `prd_id + material_type` |

```python
# Proposed integration in ai_service.py
async def _retrieve_context(
    self,
    query: str,
    project_id: str | None = None,
    top_k: int = 5,
) -> str:
    """Retrieve relevant knowledge base context."""
    from app.rag.retrieval.engine import retrieval_engine
    results = retrieval_engine.search(query, top_k=top_k)
    if project_id:
        results = [r for r in results if r.metadata.get("project_id") == project_id]
    if not results:
        return ""
    context = "\n\n---\n\n".join(
        f"[来源: {r.metadata.get('filename', '未知')}]\n{r.content}"
        for r in results
    )
    return f"\n\n以下是从企业知识库检索到的相关文档片段：\n\n{context}\n\n"
```

### 4.2 Query Rewriting / Expansion

For better retrieval, rewrite the raw prompt into a search query:

```python
def rewrite_query(raw_prompt: str, industry: str = "general") -> str:
    """Expand user prompt into a retrieval-friendly query."""
    # Simple expansion: extract key noun phrases
    # V1: Use a lightweight LLM call or keyword extractor
    keywords = _extract_keywords(raw_prompt)
    query = " ".join(keywords)
    if industry != "general":
        query += f" {industry}"
    return query

def _extract_keywords(text: str) -> List[str]:
    """Naive keyword extraction for MVP."""
    import jieba
    words = jieba.lcut(text)
    # Filter stopwords and short tokens
    stopwords = set(["的", "了", "是", "我", "有", "和", "就", "不", "人", "在"])
    return [w for w in words if len(w.strip()) > 1 and w not in stopwords]
```

**MVP**: No rewriting; use raw prompt directly.  
**V1**: Add `jieba` keyword extraction or a lightweight LLM rewrite step.

### 4.3 Top-K Retrieval with Reranking

```python
async def retrieve_with_rerank(
    query: str,
    project_id: str | None = None,
    initial_k: int = 10,
    final_k: int = 5,
) -> List[RetrievalResult]:
    """Two-stage retrieval: vector search + simple reranking."""
    results = retrieval_engine.search(query, top_k=initial_k)
    if project_id:
        # Boost project-matching documents
        for r in results:
            if r.metadata.get("project_id") == project_id:
                r.score *= 1.2
        results.sort(key=lambda x: x.score, reverse=True)
    return results[:final_k]
```

### 4.4 Context Window Management

Each retrieved chunk should include a **citation header** so the LLM can reference sources.

**Token budget allocation** (for 8k max_tokens models like Kimi):

| Component | Tokens |
|-----------|--------|
| System prompt | ~1,500 |
| Retrieved context | ~2,500 |
| User prompt + JSON schema | ~2,000 |
| Generation buffer | ~2,000 |

**Context builder**:

```python
def build_rag_context(
    results: List[RetrievalResult],
    max_tokens: int = 2500,
    chars_per_token: float = 2.0,
) -> str:
    """Build context string respecting token budget."""
    max_chars = int(max_tokens * chars_per_token)
    parts = []
    current_len = 0
    for r in results:
        part = f"[来源: {r.metadata.get('filename', '未知')}, 相关度: {r.score:.2f}]\n{r.content}\n\n"
        if current_len + len(part) > max_chars:
            break
        parts.append(part)
        current_len += len(part)
    return "\n---\n".join(parts)
```

---

## 5. Database Schema

### 5.1 SQLAlchemy Models

```python
# app/models/knowledge_base.py

import uuid
import enum
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Integer, Enum
from sqlalchemy.sql import func
from app.core.database import Base

class DocumentType(str, enum.Enum):
    PRD = "prd"
    COMPLIANCE = "compliance"
    FLOWCHART = "flowchart"
    RESEARCH = "research"
    SOP = "sop"
    OTHER = "other"

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    doc_type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    source = Column(String, default="upload")  # upload, obsidian
    author = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    content = Column(Text, default="")  # full raw text
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 5.2 Embeddings Storage

#### MVP (TF-IDF)

No separate embeddings table needed. The `RetrievalEngine` holds the TF-IDF matrix in memory and rebuilds it on startup from `knowledge_chunks.content`.

```python
async def rebuild_index_from_db():
    """Load all chunks from DB into RetrievalEngine."""
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(KnowledgeChunk))
        chunks = result.scalars().all()
        for chunk in chunks:
            retrieval_engine.add_document(
                doc_id=chunk.id,
                content=chunk.content,
                metadata={
                    **chunk.metadata_json,
                    "document_id": chunk.document_id,
                    "project_id": chunk.project_id,
                },
            )
```

#### V1 (Dense Embeddings + Chroma)

Store vectors in ChromaDB. Keep `knowledge_documents` and `knowledge_chunks` in PostgreSQL as the source of truth.

```python
# Sync Chroma collection with DB state
def sync_chroma_with_db(chunks: List[KnowledgeChunk], embeddings: List[List[float]]):
    collection.add(
        ids=[c.id for c in chunks],
        documents=[c.content for c in chunks],
        embeddings=embeddings,
        metadatas=[{
            "document_id": c.document_id,
            "project_id": c.project_id,
            "chunk_index": c.chunk_index,
        } for c in chunks],
    )
```

### 5.3 Indexes

Add to `INDEX_DEFINITIONS` in `app/core/database.py`:

```python
"idx_knowledge_docs_project_id": "CREATE INDEX IF NOT EXISTS idx_knowledge_docs_project_id ON knowledge_documents(project_id)",
"idx_knowledge_docs_doc_type": "CREATE INDEX IF NOT EXISTS idx_knowledge_docs_doc_type ON knowledge_documents(doc_type)",
"idx_knowledge_chunks_document_id": "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_id ON knowledge_chunks(document_id)",
"idx_knowledge_chunks_project_id": "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_project_id ON knowledge_chunks(project_id)",
```

---

## 6. Integration Points

### 6.1 AI Service Modifications

Modify `app/services/ai_service.py` to inject RAG context before generation.

#### `generate_prd()`

```python
async def generate_prd(
    self,
    title: str,
    description: str,
    industry: str = "general",
    context: Optional[Dict] = None,
    template: str = "default",
    project_id: Optional[str] = None,
    use_rag: bool = True,
) -> Dict[str, Any]:
    context = context or {}
    rag_context = ""
    if use_rag and project_id:
        query = f"{title} {description} {industry} PRD"
        rag_context = await self._retrieve_context(query, project_id=project_id, top_k=5)

    prompt = f"""... existing prompt ...
{rag_context}
标题: {title}
描述: {description}
..."""
```

#### `generate_prd_chapter()`

```python
async def generate_prd_chapter(
    self,
    chapter: str,
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    industry: str = "general",
    project_id: Optional[str] = None,
    use_rag: bool = True,
) -> Dict[str, Any]:
    rag_context = ""
    if use_rag and project_id:
        chapter_info = chapter_prompts.get(chapter, chapter_prompts["1"])
        query = f"{chapter_info['title']} {chapter_info['focus']} {prompt}"
        rag_context = await self._retrieve_context(query, project_id=project_id, top_k=5)

    system_prompt = f"""... existing system prompt ...
{rag_context}
..."""
```

#### `chat()`

```python
async def chat(
    self,
    message: str,
    context: Optional[Dict] = None,
    project_id: Optional[str] = None,
    use_rag: bool = True,
) -> str:
    context = context or {}
    rag_context = ""
    if use_rag and project_id and any(kw in message for kw in ["PRD", "需求", "合规", "流程", "调研"]):
        rag_context = await self._retrieve_context(message, project_id=project_id, top_k=3)

    system_prompt = context.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
    if rag_context:
        system_prompt += f"\n\n在回答时，请参考以下企业知识库内容：\n{rag_context}"
```

### 6.2 API Endpoint Changes

Update `app/api/v1/endpoints/ai.py` and `prd_generator.py` to accept `project_id` and forward it to `AIService`.

```python
# Example pydantic schema update
class PRDGenerateRequest(BaseModel):
    title: str
    description: str
    industry: str = "general"
    template: str = "default"
    project_id: Optional[str] = None
    use_rag: bool = True
```

### 6.3 Prompt Augmentation Template

```markdown
## 企业知识库参考

以下文档片段来自本项目的知识库，请在生成内容时优先参考这些资料。
如果知识库内容与通用经验冲突，以知识库内容为准。
如果知识库未覆盖某些问题，请明确标注为"待补充"，禁止编造。

---

[来源: slice-lending-prd-v1.md, 相关度: 0.92]
1. 背景与目标
   切片借阅平台旨在解决病理科玻片外借流程繁琐的问题...

---

[来源: compliance-checklist-2026.md, 相关度: 0.87]
医疗数据合规要求：
- 患者隐私数据必须加密存储
- 等保三级要求访问日志保留180天以上
```

---

## 7. Frontend UI

### 7.1 Knowledge Base Management Page

Route: `/projects/[id]/knowledge-base`

**Features**:
1. **Upload Documents**
   - Drag-and-drop zone
   - Format filter: `.md`, `.txt`, `.pdf`, `.docx`
   - Doc-type selector before upload (PRD / 合规文档 / 流程图 / 用户调研 / SOP / 其他)
   - Progress indicator

2. **Document List**
   - Table with columns: Name | Type | Source | Upload Date | Author | Actions
   - Actions: View raw text / Re-index / Delete
   - Filter by doc_type

3. **Obsidian Sync**
   - Button: "Sync from Obsidian Vault"
   - Shows last sync time and document count
   - Background re-indexing status

### 7.2 Project-Level RAG Toggle

Add a switch in the project settings sidebar:

```tsx
// Component pseudo-code
<RAGToggle
  label="启用企业知识库 (RAG)"
  description="AI生成PRD时将自动检索本项目关联的知识库文档"
  checked={project.settings.use_rag}
  onChange={(v) => updateProjectSettings({ use_rag: v })}
/>
```

When disabled, `use_rag=false` is passed to AI service calls.

### 7.3 API Endpoints for Frontend

```python
# app/api/v1/endpoints/knowledge.py (new file)

@router.post("/projects/{project_id}/knowledge/upload")
async def upload_document(project_id: str, file: UploadFile, doc_type: DocumentType):
    ...

@router.get("/projects/{project_id}/knowledge/documents")
async def list_documents(project_id: str, page: int = 1, doc_type: Optional[str] = None):
    ...

@router.delete("/projects/{project_id}/knowledge/documents/{doc_id}")
async def delete_document(project_id: str, doc_id: str):
    ...

@router.post("/projects/{project_id}/knowledge/sync-obsidian")
async def sync_obsidian(project_id: str):
    ...
```

---

## 8. Implementation Roadmap

### Phase 1: MVP (1-2 days)

**Goal**: Working RAG for Markdown/TXT with TF-IDF, integrated into PRD generation.

**Tasks**:
1. [ ] Create `app/models/knowledge_base.py` with `KnowledgeDocument` and `KnowledgeChunk`
2. [ ] Add migration/indexes in `database.py`
3. [ ] Build `app/services/knowledge_service.py`:
   - `upload_document()` -> parse -> chunk -> save to DB -> rebuild index
   - `delete_document()` -> remove from DB -> rebuild index
   - `list_documents()`
4. [ ] Extend `RetrievalEngine` to load chunks from DB on startup (replace Obsidian-only loader)
5. [ ] Modify `ai_service.py`:
   - Add `_retrieve_context()` helper
   - Inject context into `generate_prd()` and `generate_prd_chapter()`
6. [ ] Update API endpoints (`ai.py`, `prd_generator.py`) to accept `project_id` and `use_rag`
7. [ ] Add frontend knowledge base page (basic upload + list + delete)

**Deliverable**: PRD generation can retrieve from uploaded Markdown/TXT documents.

### Phase 2: V1 (1 week)

**Goal**: Production-ready RAG with dense embeddings, full format support, and advanced retrieval.

**Tasks**:
1. [ ] Add dependencies: `sentence-transformers`, `chromadb`, `python-docx`, `pdfplumber`, `python-frontmatter`, `jieba`
2. [ ] Implement `DocumentParser` classes for PDF, Word, Markdown, TXT
3. [ ] Switch `RetrievalEngine` to ChromaDB + `bge-m3` embeddings
4. [ ] Implement semantic chunking
5. [ ] Add query rewriting with `jieba` keyword extraction
6. [ ] Add reranking with project_id boost
7. [ ] Build Obsidian sync UI with background job tracking
8. [ ] Add retrieval metrics logging (latency, hit rate, relevance scores)
9. [ ] Write tests for ingestion, retrieval, and prompt augmentation

**Deliverable**: Fully-featured enterprise knowledge base with semantic search.

---

## 9. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Reuse existing TF-IDF for MVP** | `scikit-learn` is already installed; fastest path to value |
| **Store chunks in PostgreSQL** | Single source of truth; vector store is an index, not primary storage |
| **Project-scoped retrieval** | Prevents cross-project leakage; boosts relevance |
| **Opt-in RAG toggle per project** | Users control when retrieval runs; avoids unexpected behavior |
| **Citation headers in context** | Makes LLM output traceable and builds user trust |
| **No LLM-based reranking in MVP** | Keeps MVP simple; can add cross-encoder reranker in V2 |

---

## 10. Open Questions

1. Should we support real-time collaborative editing of knowledge base documents?
2. Do we need document versioning (track changes across uploads)?
3. Should we implement automatic knowledge base updates when a PRD is approved?
4. What is the budget for cloud GPU embedding inference if document volume grows beyond local CPU capacity?
