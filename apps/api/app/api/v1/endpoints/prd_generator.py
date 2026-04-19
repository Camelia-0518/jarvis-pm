"""
PRD Generator API Endpoints

提供PRD生成的REST API接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.services.prd_generator import prd_generator_service

router = APIRouter()


class PRDGenerateRequest(BaseModel):
    """PRD生成请求"""
    product_name: str
    description: str
    target_users: Optional[str] = None
    key_features: Optional[List[str]] = None
    industry: Optional[str] = None
    template_id: Optional[str] = None
    save_to_obsidian: bool = True
    save_local: bool = True


class PRDGenerateResponse(BaseModel):
    """PRD生成响应"""
    success: bool
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    obsidian_path: Optional[str] = None
    local_path: Optional[str] = None
    execution_time: float
    error: Optional[str] = None


class PRDExportRequest(BaseModel):
    """PRD导出请求"""
    content: str
    format: str = "markdown"  # markdown, json, feishu
    filename: Optional[str] = None


class PRDExportResponse(BaseModel):
    """PRD导出响应"""
    success: bool
    content: str
    filename: str
    format: str
    error: Optional[str] = None


class TemplateInfo(BaseModel):
    """模板信息"""
    id: str
    name: str
    industry: str
    description: str
    keywords: List[str]


@router.post("/generate", response_model=PRDGenerateResponse)
async def generate_prd(request: PRDGenerateRequest):
    """
    生成PRD文档

    根据产品需求描述生成完整的PRD文档
    """
    try:
        result = await prd_generator_service.generate_prd(
            product_name=request.product_name,
            description=request.description,
            target_users=request.target_users,
            key_features=request.key_features,
            industry=request.industry,
            template_id=request.template_id,
            save_to_obsidian=request.save_to_obsidian,
            save_local=request.save_local
        )

        if not result["success"]:
            return PRDGenerateResponse(
                success=False,
                error=result.get("error", "生成失败"),
                execution_time=result.get("execution_time", 0)
            )

        return PRDGenerateResponse(
            success=True,
            content=result["content"],
            metadata=result["metadata"],
            obsidian_path=result.get("obsidian_result", {}).get("file_path") if result.get("obsidian_result") else None,
            local_path=result.get("local_path"),
            execution_time=result["execution_time"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成PRD失败: {str(e)}")


@router.post("/export", response_model=PRDExportResponse)
async def export_prd(request: PRDExportRequest):
    """
    导出PRD到不同格式

    支持格式: markdown, json, feishu
    """
    try:
        result = prd_generator_service.export_prd(
            content=request.content,
            format=request.format,
            filename=request.filename
        )

        if not result["success"]:
            return PRDExportResponse(
                success=False,
                content="",
                filename="",
                format=request.format,
                error=result.get("error", "导出失败")
            )

        return PRDExportResponse(
            success=True,
            content=result["content"],
            filename=result["filename"],
            format=result["format"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出PRD失败: {str(e)}")


@router.get("/templates", response_model=List[TemplateInfo])
async def list_templates(industry: Optional[str] = None):
    """
    获取可用的PRD模板列表
    """
    from app.agents.templates import get_template_system, IndustryType

    template_system = get_template_system()

    # 转换industry字符串为枚举
    industry_enum = None
    if industry:
        try:
            industry_enum = IndustryType(industry)
        except ValueError:
            pass

    templates = template_system.list_templates(industry=industry_enum)

    return [TemplateInfo(**t) for t in templates]


@router.get("/templates/{template_id}")
async def get_template_detail(template_id: str):
    """
    获取模板详细信息
    """
    from app.agents.templates import get_template_system

    template_system = get_template_system()
    template = template_system.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return {
        "id": template.id,
        "name": template.name,
        "industry": template.industry.value,
        "description": template.description,
        "keywords": template.keywords,
        "compliance_requirements": [
            {
                "name": req.name,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "checklist": req.checklist
            }
            for req in template.compliance_requirements
        ],
        "mandatory_checks": template.mandatory_checks
    }


@router.post("/quick-generate")
async def quick_generate(description: str, product_name: Optional[str] = None):
    """
    快速生成PRD（简化接口）

    只需要提供需求描述，自动提取产品名称
    """
    # 如果没有提供产品名称，从描述中提取
    if not product_name:
        # 简单提取前10个字符作为产品名称
        product_name = description[:20] + "..." if len(description) > 20 else description

    try:
        result = await prd_generator_service.generate_prd(
            product_name=product_name,
            description=description,
            save_to_obsidian=True,
            save_local=True
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "生成失败"),
                "execution_time": result.get("execution_time", 0)
            }

        return {
            "success": True,
            "content": result["content"],
            "metadata": result["metadata"],
            "obsidian_path": result.get("obsidian_result", {}).get("file_path") if result.get("obsidian_result") else None,
            "local_path": result.get("local_path"),
            "execution_time": result["execution_time"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成PRD失败: {str(e)}")
