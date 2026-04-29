"""
代码生成 API 路由
提供 PRD 转代码的接口
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
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
from app.services.ai_service import ai_service
from app.core.database import get_db
from app.core.security import get_current_user_id
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
@router.post("/prototype", response_model=PrototypeResponse)
async def generate_prototype(request: PRDRequest):
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
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"原型生成失败: {str(e)}"
        )


@router.post("/prototype-ai", response_model=PrototypeResponse)
async def generate_prototype_ai(
    request: PrototypeAIRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    AI 增强原型生成（调用 Kimi API）

    - 基于 PRD 内容生成可运行的 HTML 原型
    - 自动注入项目用户画像和竞品信息
    - 只使用已配置的 Kimi API，不引入其他服务
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD 内容太短，请提供完整的 PRD 文档"
        )

    # 收集项目上下文
    personas_text = ""
    competitors_text = ""
    if request.project_id:
        try:
            persona_result = await db.execute(
                select(Persona).where(Persona.project_id == request.project_id)
            )
            personas = persona_result.scalars().all()
            if personas:
                personas_text = "\n".join([
                    f"- {p.name}（{p.role}）: {p.description or ''} 痛点: {p.pain_points or ''} 目标: {p.goals or ''}"
                    for p in personas
                ])

            competitor_result = await db.execute(
                select(Competitor).where(Competitor.project_id == request.project_id)
            )
            competitors = competitor_result.scalars().all()
            if competitors:
                competitors_text = "\n".join([
                    f"- {c.name}: {c.description or ''} 优势: {c.strengths or ''} 定价: {c.pricing or ''}"
                    for c in competitors
                ])
        except Exception:
            pass  # 忽略查询失败，继续生成

    # 构建 prompt
    context_parts = ["基于以下 PRD 内容生成一个可交互的前端原型页面："]
    context_parts.append(f"\nPRD 内容:\n{request.prd_content[:3000]}")  # 限制长度

    if personas_text:
        context_parts.append(f"\n目标用户画像:\n{personas_text}")
    if competitors_text:
        context_parts.append(f"\n竞品参考:\n{competitors_text}")

    prompt = "\n".join(context_parts) + """

要求：
1. 输出一个完整的、可独立运行的 HTML 文件
2. 使用 Tailwind CSS CDN（https://cdn.tailcdn.com）进行样式设计
3. 包含所有必要的 HTML 结构、内联 CSS 和内联 JavaScript
4. 原型应体现 PRD 中描述的核心业务流程和关键页面
5. 如果是医疗行业，界面应体现专业、简洁、可信赖的风格
6. 如果是 SaaS/电商行业，界面应体现现代、清晰、易用的风格
7. 包含模拟数据和交互（如表单填写、页面切换、弹窗等）
8. 使用中文界面
9. 确保代码在浏览器中可直接打开运行

请直接输出 HTML 代码，用 ```html 和 ``` 包裹。"""

    try:
        content = await ai_service.chat(
            prompt,
            {"max_tokens": 8000, "system_prompt": "你是一位资深前端工程师，擅长用 HTML + Tailwind CSS 快速构建高保真产品原型。你输出的是可直接运行的代码，不是设计建议。"}
        )

        # 提取 HTML 代码块
        html_code = content
        if "```html" in content:
            html_code = content.split("```html")[1].split("```")[0].strip()
        elif "```" in content:
            html_code = content.split("```")[1].split("```")[0].strip()

        # 如果没有找到代码块，使用原始内容
        if not html_code.strip():
            html_code = content

        # 确保包含基础 HTML 结构
        if not html_code.strip().startswith("<"):
            html_code = f"<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n<title>原型预览</title>\n<script src=\"https://cdn.tailwindcss.com\"></script>\n</head>\n<body class=\"bg-gray-50\">\n{html_code}\n</body>\n</html>"

        return {
            "files": {
                "index.html": html_code,
                "styles.css": "",
                "scripts.js": "",
            },
            "metadata": {
                "name": "AI 生成原型",
                "description": "基于 PRD 和项目上下文生成的可交互原型",
                "page_count": 1,
                "pages": [{"name": "index", "route": "/", "title": "原型首页"}],
                "generated_by": "ai",
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_ERROR,
            detail=f"AI 原型生成失败: {str(e)}"
        )


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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"UI 需求提取失败: {str(e)}"
        )


@router.post("/api-spec", response_model=APISpecResponse)
async def generate_api_spec(request: PRDRequest):
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API 规范生成失败: {str(e)}"
        )


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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Swagger UI 生成失败: {str(e)}"
        )


@router.post("/components", response_model=ComponentsResponse)
async def generate_components(request: PRDRequest):
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"组件生成失败: {str(e)}"
        )


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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"组件建议获取失败: {str(e)}"
        )


@router.post("/generate-all")
async def generate_all(request: PRDRequest):
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
        # 生成原型
        prototype = generate_prototype_from_prd(request.prd_content)

        # 生成 API 规范
        api_spec = generate_api_from_prd(request.prd_content)

        # 生成组件
        components = generate_components_from_prd(request.prd_content)

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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"代码生成失败: {str(e)}"
        )


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
