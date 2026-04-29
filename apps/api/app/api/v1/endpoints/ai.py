"""AI endpoints"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import json
import time

from app.core.database import get_db
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.services.ai_service import ai_service
from app.agents.llm_client import create_default_client
from app.api.v1.endpoints.rag import retrieval_engine
from app.rag.context.optimizer import ContextOptimizer, ConversationContext

router = APIRouter()
context_optimizer = ContextOptimizer()


def _build_rag_context(query: str) -> str:
    """从 RAG 检索引擎构建参考资料上下文。"""
    results = retrieval_engine.search(query, top_k=3)
    if not results:
        return ""
    parts = ["【参考资料】"]
    for i, r in enumerate(results, 1):
        title = r.metadata.get("filename", r.doc_id) if r.metadata else r.doc_id
        snippet = r.content[:500].replace("\n", " ")
        parts.append(f"[{i}] {title}: {snippet}")
    return "\n".join(parts)


def _ensure_conversation(session_id: str) -> ConversationContext:
    """获取或创建对话上下文。"""
    if session_id not in context_optimizer.conversations:
        context_optimizer.conversations[session_id] = ConversationContext(session_id=session_id)
    return context_optimizer.conversations[session_id]


class ChatRequest(BaseModel):
    """Chat request"""
    message: str = Field(..., min_length=1)
    context: Optional[dict] = None


class OptimizePromptRequest(BaseModel):
    """Optimize prompt request"""
    input: str = Field(..., min_length=1)
    context: Optional[dict] = None


class GeneratePRDRequest(BaseModel):
    """Generate PRD request"""
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    industry: Optional[str] = None
    context: Optional[dict] = None


class ReviewMaterialRequest(BaseModel):
    """Review material request"""
    project_id: str
    prd_id: Optional[str] = None
    material_type: str = Field(..., pattern="^(agenda|qa|risks|decisions|standup)$")


@router.post("/chat", response_model=dict)
async def chat(
    data: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Chat with AI assistant (with RAG + context optimizer)"""
    session_id = (data.context or {}).get("conversation_id", "default")
    conv = _ensure_conversation(session_id)
    conv.add_message("user", data.message)

    # Build RAG context
    rag_context = _build_rag_context(data.message)

    # Build enhanced system prompt
    base_system = (data.context or {}).get(
        "system_prompt",
        """你是Jarvis，一位专精于产品管理的AI助手。
帮助用户进行PRD撰写、需求分析和项目规划。
回答简洁专业，聚焦产品思维而非技术实现细节。
使用中文回复。

重要原则：
- 当你提供涉及具体数字、法规条款、竞品数据、市场调研结论时，必须明确告知用户这些内容的来源和可信度。
- 如果你不确定某个事实，请使用占位符或明确说明"此处为假设，需人工核实"，禁止编造虚假信息。
- 在输出较长报告时，请在开头加上数据来源声明。""",
    )

    enhanced_system = base_system
    if rag_context:
        enhanced_system += f"\n\n{rag_context}"

    # Add recent conversation history hint
    recent_msgs = conv.get_recent_messages(3)
    if len(recent_msgs) > 1:
        history_lines = []
        for msg in recent_msgs[:-1]:
            prefix = "用户" if msg.role == "user" else "助手"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            history_lines.append(f"{prefix}：{content}")
        enhanced_system += "\n\n【近期对话】\n" + "\n".join(history_lines)

    chat_context = dict(data.context or {})
    chat_context["system_prompt"] = enhanced_system

    response_text = await ai_service.chat(data.message, chat_context)

    # Record assistant response
    conv.add_message("assistant", response_text)
    return ResponseBuilder.success({
        "response": response_text,
        "reply": response_text,
    })


@router.post("/optimize-prompt", response_model=dict)
async def optimize_prompt(
    data: OptimizePromptRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Optimize a prompt"""
    result = await ai_service.optimize_prompt(data.input, data.context)
    # Ensure stable schema even if LLM returns unexpected JSON
    return ResponseBuilder.success({
        "task_type": result.get("task_type", "general"),
        "structured_prompt": result.get("structured_prompt", data.input),
        "next_steps": result.get("next_steps", "Review and refine the prompt")
    })


@router.post("/generate-prd", response_model=dict)
async def generate_prd(
    data: GeneratePRDRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate PRD using AI"""
    result = await ai_service.generate_prd(
        title=data.title,
        description=data.description,
        industry=data.industry or "general",
        context=data.context
    )
    return ResponseBuilder.success(result)


@router.post("/generate-prd-stream")
async def generate_prd_stream(
    data: GeneratePRDRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Stream PRD generation using SSE"""
    async def event_generator():
        full_markdown = ""
        try:
            async for chunk in ai_service.generate_prd_stream(
                title=data.title,
                description=data.description,
                industry=data.industry or "general",
                context=data.context
            ):
                full_markdown += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=True)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'markdown': full_markdown}, ensure_ascii=True)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/review-materials", response_model=dict)
async def review_materials(
    data: ReviewMaterialRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate review materials"""
    result = await ai_service.generate_review_material(
        prd_id=data.prd_id or data.project_id,
        material_type=data.material_type
    )
    return ResponseBuilder.success({
        "id": f"review_{data.material_type}_{int(time.time())}",
        "material_type": data.material_type,
        "content": {"raw": result.get("content", "")},
        "markdown": result.get("content", "# Review Material")
    })


async def _chat_stream_generator_llm(messages: list):
    """Generate SSE stream for chat response using real LLM."""
    llm = create_default_client()
    full_content = ""
    try:
        async for chunk in llm.chat_stream(messages, temperature=0.7, max_tokens=2000):
            full_content += chunk
            payload = json.dumps({"content": chunk, "done": False})
            yield f"data: {payload}\n\n"
    except Exception as e:
        # Yield error as final chunk so client can display it
        payload = json.dumps({"content": f"\n[Error: {str(e)}]", "done": False})
        yield f"data: {payload}\n\n"
    final = json.dumps({"content": "", "done": True, "full_content": full_content})
    yield f"data: {final}\n\n"


async def _chat_stream_with_history(messages: list, session_id: str):
    """包装流式生成器，在结束后记录助手回复到上下文优化器。"""
    full_content = ""
    async for chunk in _chat_stream_generator_llm(messages):
        if chunk.startswith("data: "):
            try:
                payload = json.loads(chunk[6:].strip())
                if payload.get("done"):
                    full_content = payload.get("full_content", "")
            except Exception:
                pass
        yield chunk
    if full_content and session_id:
        conv = _ensure_conversation(session_id)
        conv.add_message("assistant", full_content)


@router.post("/chat/stream")
async def chat_stream(
    conversation_id: str = Query(...),
    content: str = Query(...),
    agent_role: Optional[str] = Query("orchestrator"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Stream chat response via SSE (with RAG + context optimizer)"""
    session_id = conversation_id
    conv = _ensure_conversation(session_id)
    conv.add_message("user", content)

    # Build RAG context
    rag_context = _build_rag_context(content)

    system_prompt = """你是Jarvis，一位专精于产品管理的AI助手。
帮助用户进行PRD撰写、需求分析和项目规划。
回答简洁专业，聚焦产品思维而非技术实现细节。
使用中文回复。"""

    if rag_context:
        system_prompt += f"\n\n{rag_context}"

    # Add recent conversation history hint
    recent_msgs = conv.get_recent_messages(3)
    if len(recent_msgs) > 1:
        history_lines = []
        for msg in recent_msgs[:-1]:
            prefix = "用户" if msg.role == "user" else "助手"
            c = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            history_lines.append(f"{prefix}：{c}")
        system_prompt += "\n\n【近期对话】\n" + "\n".join(history_lines)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]
    return StreamingResponse(
        _chat_stream_with_history(messages, session_id),
        media_type="text/event-stream",
    )
