"""
代码生成 API 路由
提供 PRD 转代码的接口
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

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

router = APIRouter(prefix="/code", tags=["code-generation"])


# Schemas
class PRDRequest(BaseModel):
    """PRD 请求"""
    prd_content: str
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
