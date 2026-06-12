"""
代码生成 API 路由
提供 PRD 转代码的接口
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.prototype_generator import (
    generate_prototype_from_prd,
    extract_ui_requirements,
)
from app.services.api_generator import (
    generate_api_from_prd,
    generate_swagger_ui,
)
from app.services.component_generator import (
    generate_components_from_prd,
    get_component_suggestions,
)
from app.services.prototype_ai_service import prototype_ai_service
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.tasks import create_task, get_task, start_background_task
from app.core.rate_limit import rate_limit
from app.core.html_sanitizer import sanitize_html, validate_prototype_interactions
from app.models.persona import Persona
from app.models.competitor import Competitor

router = APIRouter(tags=["code-generation"])


# Schemas
class PRDRequest(BaseModel):
    """PRD 请求"""
    prd_content: str
    options: Optional[Dict[str, Any]] = None


class PrototypeAIRequest(BaseModel):
    """AI 增强原型生成请求"""
    prd_content: str
    project_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class PrototypeResponse(BaseModel):
    """原型生成响应"""
    files: Dict[str, str]
    metadata: Dict[str, Any]


class APISpecResponse(BaseModel):
    """API 规范生成响应"""
    openapi: Dict[str, Any]
    crud_files: Dict[str, str]
    metadata: Dict[str, Any]


class ComponentsResponse(BaseModel):
    """组件生成响应"""
    components: list
    files: Dict[str, str]
    metadata: Dict[str, Any]


class UIRequirementsResponse(BaseModel):
    """UI 需求提取响应"""
    project_name: str
    description: str
    pages: list
    interactions: list
    theme: Dict[str, str]


class ComponentSuggestionsResponse(BaseModel):
    """组件建议响应"""
    suggestions: list


class ExportRequest(BaseModel):
    """导出请求"""
    format: str  # html, zip, json
    files: Optional[Dict[str, str]] = None


class PreviewRequest(BaseModel):
    """预览请求"""
    files: Dict[str, str]
    device: Optional[str] = "desktop"  # desktop, tablet, mobile


# Routes
@rate_limit(requests=20, window=60)
@router.post("/prototype")
async def generate_prototype(request: PRDRequest, http_request: Request):
    """
    从 PRD 生成原型

    - **prd_content**: PRD 文档内容
    - **options**: 可选配置项

    返回包含 HTML/CSS/JS 文件的字典
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    try:
        result = generate_prototype_from_prd(request.prd_content)
        # Sanitize AI-generated HTML to prevent XSS
        if result.get("files", {}).get("index.html"):
            result["files"]["index.html"] = sanitize_html(result["files"]["index.html"])
        return result
    except Exception:
        logging.exception("Prototype generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="原型生成失败，请稍后重试"
        )


@rate_limit(requests=10, window=60)
@router.post("/prototype-ai/extract")
async def extract_prototype_skeleton(request: PrototypeAIRequest, http_request: Request):
    """
    从 PRD 提取产品骨架（异步任务）

    - 提交异步任务，立刻返回 task_id
    - 前端轮询 /prototype-ai/tasks/{task_id} 获取进度和结果
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    task_id = await create_task(
        prd_content=request.prd_content,
        options=request.options or {},
    )

    await start_background_task(
        task_id=task_id,
        coro=prototype_ai_service.extract_skeleton,
    )

    return {
        "task_id": task_id,
        "message": "骨架提取任务已提交，请轮询查询进度",
    }


@rate_limit(requests=100, window=60)
@router.get("/prototype-ai/tasks/{task_id}")
async def get_prototype_task(task_id: str):
    """查询异步原型任务状态"""
    task = await get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "skeleton": task.get("skeleton"),
        "html": task.get("html"),
        "report": task.get("report"),
        "error": task.get("error"),
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
    }


@rate_limit(requests=10, window=60)
@router.post("/prototype-ai/sync")
async def generate_prototype_ai_sync(request: PrototypeAIRequest, http_request: Request):
    """
    AI 增强原型生成 - 非流式一次性返回

    - 基于骨架生成高保真原型
    - 一次性返回完整 HTML 和生成报告
    - 支持缓存，相同骨架秒级复用
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    # 如果没有提供骨架，先自动提取
    skeleton = request.options.get("skeleton") if request.options else None
    if not skeleton:
        skeleton = await prototype_ai_service.extract_skeleton(
            request.prd_content,
            request.options or {},
        )

    style = (request.options or {}).get("style", "high-fidelity")

    # 收集所有事件，拼接完整 HTML
    html_parts: list[str] = []
    report: Dict[str, Any] = {}
    async for event in prototype_ai_service.generate_prototype_stream(skeleton, {"style": style}):
        if event["event"] == "chunk":
            html_parts.append(event["data"])
        elif event["event"] == "done":
            report = event["data"].get("report", {})
    html = "".join(html_parts)

    return {
        "html": sanitize_html(html),
        "report": report,
    }


@rate_limit(requests=10, window=60)
@router.post("/prototype-ai")
async def generate_prototype_ai(
    request: PrototypeAIRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    AI 增强原型生成（调用 Kimi API）- 兼容旧接口

    - 基于 PRD 内容生成可运行的 HTML 原型
    - 自动注入项目用户画像和竞品信息
    - 内部走新流水线：提取骨架 → 生成原型
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    # 收集项目上下文（验证归属）
    personas_text = ""
    competitors_text = ""
    if request.project_id:
        try:
            from app.core.permissions import require_project_owner
            proj = await require_project_owner(db, request.project_id, user_id)

            persona_result = await db.execute(
                select(Persona).where(Persona.project_id == request.project_id, Persona.deleted_at.is_(None))
            )
            personas = persona_result.scalars().all()
            if personas:
                personas_text = "\n".join([
                    f"- {p.name}（{p.role}）: {p.description or ''} 痛点: {p.pain_points or ''} 目标: {p.goals or ''}"
                    for p in personas
                ])

            competitor_result = await db.execute(
                select(Competitor).where(Competitor.project_id == request.project_id, Competitor.deleted_at.is_(None))
            )
            competitors = competitor_result.scalars().all()
            if competitors:
                competitors_text = "\n".join([
                    f"- {c.name}: {c.description or ''} 优势: {c.strengths or ''} 定价: {c.pricing or ''}"
                    for c in competitors
                ])
        except Exception as e:
            logging.warning("Failed to load project context for PRD enrichment: %s", e)

    # 将上下文附加到 PRD 中
    enriched_prd = request.prd_content
    if personas_text:
        enriched_prd += f"\n\n【用户画像】\n{personas_text}"
    if competitors_text:
        enriched_prd += f"\n\n【竞品信息】\n{competitors_text}"

    try:
        # 新流水线：提取骨架 → 生成原型
        skeleton = await prototype_ai_service.extract_skeleton(enriched_prd, request.options or {})

        html_parts: list[str] = []
        report: Dict[str, Any] = {}
        async for event in prototype_ai_service.generate_prototype_stream(skeleton, request.options or {}):
            if event["event"] == "chunk":
                html_parts.append(event["data"])
            elif event["event"] == "done":
                report = event["data"].get("report", {})
            elif event["event"] == "error":
                raise Exception(event["data"].get("message", "生成失败"))
        html_code = "".join(html_parts)

        # 构建页面列表
        pages = []
        for i, p in enumerate(report.get("page_list", [])):
            pages.append({
                "name": p["name"],
                "route": f"/{p['name']}",
                "title": p["name"],
            })
        if not pages:
            pages = [{"name": "index", "route": "/", "title": "原型首页"}]

        # Validate prototype interactions
        interaction_report = validate_prototype_interactions(html_code)

        return {
            "files": {
                "index.html": sanitize_html(html_code),
                "styles.css": "",
                "scripts.js": "",
            },
            "metadata": {
                "name": skeleton.get("product_name", "AI 生成原型"),
                "description": f"基于 PRD 生成，包含 {report.get('pages', 0)} 个页面，{report.get('interactions', {}).get('total', 0)} 个交互点",
                "page_count": report.get("pages", 1),
                "pages": pages,
                "generated_by": "ai",
                "report": report,
                "interaction_validation": interaction_report,
            }
        }
    except Exception:
        logging.exception("AI prototype generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 原型生成失败，请稍后重试"
        )


@rate_limit(requests=30, window=60)
@router.post("/prototype/ui-requirements", response_model=UIRequirementsResponse)
async def extract_ui_requirements_endpoint(request: PRDRequest):
    """
    从 PRD 提取 UI 需求

    提取页面、组件、交互等结构化需求
    """
    if not request.prd_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容不能为空"
        )

    try:
        result = extract_ui_requirements(request.prd_content)
        return result
    except Exception:
        logging.exception("UI requirements extraction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="UI 需求提取失败，请稍后重试"
        )


@rate_limit(requests=20, window=60)
@router.post("/api-spec")
async def generate_api_spec(request: PRDRequest, http_request: Request):
    """
    从 PRD 生成 API 规范

    - **prd_content**: PRD 文档内容

    返回 OpenAPI 3.0 规范和 CRUD 代码
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    try:
        result = generate_api_from_prd(request.prd_content)
        return result
    except Exception:
        logging.exception("API spec generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API 规范生成失败，请稍后重试"
        )


@rate_limit(requests=30, window=60)
@router.post("/api-spec/swagger-ui")
async def generate_swagger_ui_endpoint(request: PRDRequest):
    """
    从 PRD 生成 Swagger UI HTML

    返回可直接在浏览器中打开的 Swagger UI 页面
    """
    if not request.prd_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容不能为空"
        )

    try:
        result = generate_api_from_prd(request.prd_content)
        swagger_html = generate_swagger_ui(result["openapi"])
        return {"html": swagger_html}
    except Exception:
        logging.exception("Swagger UI generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Swagger UI 生成失败，请稍后重试"
        )


@rate_limit(requests=20, window=60)
@router.post("/components")
async def generate_components(request: PRDRequest, http_request: Request):
    """
    从 PRD 生成前端组件

    - **prd_content**: PRD 文档内容

    返回 React + TypeScript 组件代码
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    try:
        result = generate_components_from_prd(request.prd_content)
        return result
    except Exception:
        logging.exception("Component generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="组件生成失败，请稍后重试"
        )


@rate_limit(requests=30, window=60)
@router.post("/components/suggestions", response_model=ComponentSuggestionsResponse)
async def get_component_suggestions_endpoint(request: PRDRequest):
    """
    获取组件建议

    分析 PRD 并推荐需要的组件列表
    """
    if not request.prd_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容不能为空"
        )

    try:
        suggestions = get_component_suggestions(request.prd_content)
        return {"suggestions": suggestions}
    except Exception:
        logging.exception("Component suggestions failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="组件建议获取失败，请稍后重试"
        )


@rate_limit(requests=5, window=60)
@router.post("/generate-all")
async def generate_all(request: PRDRequest, http_request: Request):
    """
    从 PRD 生成所有代码

    同时生成原型、API 规范和前端组件
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    try:
        # 并行生成，避免同步调用阻塞事件循环
        loop = asyncio.get_running_loop()
        prototype, api_spec, components = await asyncio.gather(
            loop.run_in_executor(None, generate_prototype_from_prd, request.prd_content),
            loop.run_in_executor(None, generate_api_from_prd, request.prd_content),
            loop.run_in_executor(None, generate_components_from_prd, request.prd_content),
        )

        return {
            "prototype": prototype,
            "api_spec": api_spec,
            "components": components,
            "summary": {
                "pages": prototype["metadata"]["page_count"],
                "endpoints": api_spec["metadata"]["endpoint_count"],
                "schemas": api_spec["metadata"]["schema_count"],
                "components": components["metadata"]["total_count"],
            }
        }
    except Exception:
        logging.exception("Code generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="代码生成失败，请稍后重试"
        )


@rate_limit(requests=10, window=60)
@router.post("/export")
async def export_code(request: ExportRequest):
    """
    导出代码

    - **format**: 导出格式 (html, zip, json)
    - **files**: 要导出的文件
    """
    if request.format not in ["html", "zip", "json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的导出格式"
        )

    # 这里可以实现实际的导出逻辑
    # 例如生成 ZIP 文件或返回下载链接

    return {
        "message": f"代码已导出为 {request.format} 格式",
        "download_url": f"/downloads/export.{request.format}",
    }


@rate_limit(requests=30, window=60)
@router.post("/preview")
async def preview_prototype(request: PreviewRequest):
    """
    预览原型

    - **files**: 原型文件
    - **device**: 预览设备类型
    """
    if not request.files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件不能为空"
        )

    # 合并文件为单个 HTML
    html = request.files.get("index.html", "")
    css = request.files.get("styles.css", "")
    js = request.files.get("scripts.js", "")

    if css and "styles.css" not in html:
        html = html.replace("</head>", f"<style>{css}</style></head>")

    if js and "scripts.js" not in html:
        html = html.replace("</body>", f"<script>{js}</script></body>")

    return {
        "html": html,
        "device": request.device,
    }