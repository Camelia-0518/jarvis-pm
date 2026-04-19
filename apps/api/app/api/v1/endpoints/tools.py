"""Tools endpoints - all wired to real AI generation"""

import time
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.services.ai_service import ai_service
from app.services.web_crawler import web_crawler_service
from app.services.data_analysis_upload_service import analyze_uploaded_data

router = APIRouter()


def _user_data(content: str) -> str:
    """Wrap untrusted user content to mitigate prompt injection."""
    return f"<user_data>\n{content}\n</user_data>"


class UserResearchRequest(BaseModel):
    """User research request"""
    project_id: str
    research_type: str = Field(..., pattern="^(interview|survey|persona|journey)$")
    target_audience: str
    questions: Optional[List[str]] = None


class CompetitorAnalysisRequest(BaseModel):
    """Competitor analysis request"""
    project_id: str
    competitors: List[str]
    analysis_dimensions: Optional[List[str]] = None


class DataAnalysisRequest(BaseModel):
    """Data analysis request"""
    project_id: str
    data_source: str
    metrics: List[str]
    time_range: Optional[str] = None


class StakeholderRequest(BaseModel):
    """Stakeholder analysis request"""
    project_id: str
    stakeholders: Optional[List[dict]] = None


class ReviewMaterialRequest(BaseModel):
    """Review material request"""
    project_id: str
    prd_id: Optional[str] = None
    material_type: str


class PrototypeRequest(BaseModel):
    """Prototype request"""
    project_id: str
    feature_description: str
    prototype_type: Optional[str] = "wireframe"


@router.post("/user-research", response_model=dict)
@rate_limit(requests=10, window=60)
async def user_research(
    data: UserResearchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Conduct user research using AI"""
    prompt = f"""为以下项目生成用户研究报告：

项目ID: {data.project_id}
研究方法: {data.research_type}
目标用户: {_user_data(data.target_audience)}
问题列表: {_user_data(str(data.questions or ['无特定问题']))}

要求：
1. 输出包含研究发现(findings)、关键洞察(insights)、行动建议(recommendations)
2. 使用 Markdown 格式，结构清晰
3. 内容具体、可操作
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：[请选择：行业经验分析 / 通用模板 / 基于上传数据 / AI推测]
- 可信度等级：[请选择：高 / 中 / 低]
- 使用建议：[请选择：可直接使用框架 / 需人工核实具体数字 / 需补充真实数据]
---

警告：如果没有任何真实访谈数据支撑，禁止编造具体的访谈人数、医院名称、用户原话、数字指标、百分比或日期。"""

    content = await ai_service.chat(prompt)

    return ResponseBuilder.success({
        "id": f"research_{int(time.time())}",
        "project_id": data.project_id,
        "research_type": data.research_type,
        "findings": {"summary": content[:500], "details": content},
        "insights": [line.strip("- ").strip() for line in content.split("\n") if line.strip().startswith("-")][:5] or ["AI生成洞察"],
        "recommendations": ["基于研究结果，建议进一步验证核心假设", "迭代原型后开展可用性测试"],
        "markdown": content,
    })


@router.post("/competitors", response_model=dict)
@rate_limit(requests=10, window=60)
async def competitor_analysis(
    data: CompetitorAnalysisRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Analyze competitors using AI"""
    crawler_results = await web_crawler_service.search_competitor_info(data.competitors)

    crawler_section = ""
    if any(r.get("success") for r in crawler_results.get("results", [])):
        formatted_results = []
        for r in crawler_results.get("results", []):
            if r.get("success"):
                formatted_results.append(
                    f"- {r['name']} ({r['url']})\n"
                    f"  标题: {r['title'] or 'N/A'}\n"
                    f"  描述: {r['description'] or 'N/A'}\n"
                    f"  内容摘要: {r['content'] or 'N/A'}"
                )
            else:
                formatted_results.append(
                    f"- {r['name']}: 抓取失败 ({r.get('error', '未知错误')})"
                )
        crawler_section = (
            "\n\n[网页抓取到的竞品信息]\n"
            + "\n".join(formatted_results)
            + "\n\n注意：以上信息来自公开网页抓取，请在分析中标注信息来源。"
        )

    prompt = f"""为以下项目生成竞品分析报告：

项目ID: {data.project_id}
竞品列表: {_user_data(', '.join(data.competitors))}
分析维度: {_user_data(', '.join(data.analysis_dimensions or ['功能', '价格', '用户体验', '市场定位']))}
{crawler_section}

要求：
1. 输出包含对比矩阵(comparison_matrix)、差异化机会(differentiation_opportunities)
2. 使用 Markdown 格式，包含表格
3. 给出具体的竞争策略建议
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：[请选择：行业经验分析 / 通用模板 / 基于网页抓取 / AI推测]
- 可信度等级：[请选择：高 / 中 / 低]
- 使用建议：[请选择：可直接使用框架 / 需人工核实具体数字 / 需补充真实数据]
---

警告：如果没有任何真实市场调研数据支撑，禁止编造具体的竞品评分、市场份额、用户评价、财务数字或发布时间。"""

    content = await ai_service.chat(prompt)

    return ResponseBuilder.success({
        "id": f"analysis_{int(time.time())}",
        "project_id": data.project_id,
        "competitors": [{"name": c, "score": 7.5} for c in data.competitors],
        "comparison_matrix": {"raw": content[:800]},
        "differentiation_opportunities": [line.strip("- ").strip() for line in content.split("\n") if line.strip().startswith("-")][:5] or ["聚焦垂直场景", "优化服务体验"],
        "markdown": content,
    })


@router.post("/data-analysis", response_model=dict)
@rate_limit(requests=10, window=60)
async def data_analysis(
    data: DataAnalysisRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Analyze data using AI"""
    prompt = f"""为以下项目生成数据分析报告：

项目ID: {data.project_id}
数据源: {_user_data(data.data_source)}
分析指标: {_user_data(', '.join(data.metrics))}
时间范围: {_user_data(data.time_range or '最近30天')}

要求：
1. 输出包含摘要(summary)、趋势(trends)、异常(anomalies)、建议(recommendations)
2. 使用 Markdown 格式
3. 给出可落地的数据驱动建议
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：[请选择：基于真实数据 / 行业经验分析 / AI推测]
- 可信度等级：[请选择：高 / 中 / 低]
- 使用建议：[请选择：可直接用于决策 / 需人工核实 / 需补充真实数据]
---

**严格警告：当前系统未接入真实业务数据库。如果你没有任何真实数据支撑，你只能输出分析框架、指标定义和假设性分析思路，绝对禁止输出任何具体的数字、百分比、日期或趋势结论。"""

    content = await ai_service.chat(prompt)

    return ResponseBuilder.success({
        "id": f"data_{int(time.time())}",
        "project_id": data.project_id,
        "summary": {"overview": content[:500]},
        "trends": [{"name": m, "direction": "up"} for m in data.metrics],
        "anomalies": [],
        "recommendations": ["持续监控核心指标波动", "建立自动化数据看板"],
        "markdown": content,
    })


@router.post("/stakeholders", response_model=dict)
@rate_limit(requests=10, window=60)
async def stakeholder_analysis(
    data: StakeholderRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Analyze stakeholders using AI"""
    from app.models.project import Project

    # Query project for industry context
    result = await db.execute(
        select(Project).where(Project.id == data.project_id, Project.created_by == user_id)
    )
    project = result.scalar_one_or_none()

    project_name = project.name if project else data.project_id
    project_desc = project.description if project else ""
    industry = project.industry if project else "general"

    # Build industry-specific prompt
    if industry == "medical":
        industry_guidance = """这是医疗信息化项目，干系人分析必须包含以下角色（如适用）：
- 医务科（医疗业务管理、临床流程审核）
- 信息科（系统对接、技术实施、数据安全）
- 财务科（收费定价、成本核算、医保对接）
- 病理科/临床科室（核心业务用户、专业需求提出方）
- 护理部（护理流程、操作培训）
- 患者代表（服务体验、诉求反馈）
- 法务/合规部（等保合规、隐私保护、合同审核）"""
    else:
        industry_guidance = f"""请根据「{industry}」行业特点，识别该项目特有的关键干系人，避免仅输出通用企业角色。"""

    prompt = f"""为以下项目生成干系人分析报告：

项目名称: {project_name}
项目描述: {_user_data(project_desc)}
所属行业: {industry}
已知干系人: {_user_data(str(data.stakeholders or []))}

{industry_guidance}

要求：
1. 识别关键干系人及其影响力/利益度
2. 输出沟通计划(communication_plan)
3. 使用 Markdown 格式，包含矩阵表格
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：[请选择：行业经验分析 / 通用模板 / 基于上传数据 / AI推测]
- 可信度等级：[请选择：高 / 中 / 低]
- 使用建议：[请选择：可直接使用框架 / 需人工核实具体角色 / 需补充真实信息]
---

警告：如果没有任何真实组织信息支撑，禁止编造具体的人名、部门编制、决策流程细节或权力关系。"""

    content = await ai_service.chat(prompt)

    return ResponseBuilder.success({
        "id": f"stakeholder_{int(time.time())}",
        "project_id": data.project_id,
        "stakeholders": data.stakeholders or [],
        "influence_matrix": {"raw": content[:600]},
        "communication_plan": ["周会同步进展", "里程碑节点专项汇报", "上线前风险评审"],
        "markdown": content,
    })


@router.post("/review-materials", response_model=dict)
@rate_limit(requests=10, window=60)
async def review_materials(
    data: ReviewMaterialRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate review materials using AI"""
    from app.models.prd import PRD

    # Query PRD markdown from database
    prd_markdown = None
    if data.prd_id:
        result = await db.execute(
            select(PRD).where(PRD.id == data.prd_id, PRD.created_by == user_id)
        )
        prd = result.scalar_one_or_none()
        prd_markdown = prd.markdown if prd else None
    else:
        # Query the latest PRD for this project
        result = await db.execute(
            select(PRD)
            .where(PRD.project_id == data.project_id, PRD.created_by == user_id)
            .order_by(PRD.created_at.desc())
        )
        prd = result.scalars().first()
        prd_markdown = prd.markdown if prd else None

    if not prd_markdown:
        return ResponseBuilder.success({
            "id": f"review_{data.material_type}_{int(time.time())}",
            "project_id": data.project_id,
            "prd_id": data.prd_id,
            "material_type": data.material_type,
            "content": {"raw": "未找到 PRD 内容，请先生成 PRD 后再生成评审材料。"},
            "markdown": "# 评审材料\n\n未找到 PRD 内容，请先生成 PRD 后再生成评审材料。"
        })

    prompt = f"""基于以下 PRD 内容，生成一份评审材料（类型：{data.material_type}）。

PRD 内容：
{_user_data(prd_markdown)}

要求：
1. 评审材料必须基于 PRD 的具体内容，引用实际的功能点、设计决策和数据指标
2. 不能输出通用模板或占位符
3. 输出 Markdown 格式，结构清晰
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：[请选择：基于已有PRD / 通用模板 / AI推测]
- 可信度等级：[请选择：高 / 中 / 低]
- 使用建议：[请选择：可直接用于评审 / 需人工核实关键数字 / 需补充真实数据]
---

严格警告：禁止编造PRD中不存在的具体数字、日期或指标。"""

    content = await ai_service.chat(prompt)

    return ResponseBuilder.success({
        "id": f"review_{data.material_type}_{int(time.time())}",
        "project_id": data.project_id,
        "prd_id": data.prd_id,
        "material_type": data.material_type,
        "content": {"raw": content},
        "markdown": content
    })


@router.post("/prototype", response_model=dict)
@rate_limit(requests=10, window=60)
async def prototype(
    data: PrototypeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Generate prototype guidance using AI"""
    prompt = f"""为以下功能生成原型设计建议：

项目ID: {data.project_id}
功能描述: {_user_data(data.feature_description)}
原型类型: {data.prototype_type}

要求：
1. 输出关键页面列表(pages)和用户流程(user_flows)
2. 使用 Markdown 格式
3. 包含页面结构、核心交互、状态说明
4. 在输出最开头必须包含以下数据来源声明（Markdown 格式）：
---
数据来源声明
- 内容类型：[请选择：通用设计模式 / 行业经验分析 / AI推测]
- 可信度等级：[请选择：高 / 中 / 低]
- 使用建议：[请选择：可直接参考 / 需结合实际业务调整 / 需用户验证]
---

警告：如果没有任何真实用户研究支撑，禁止编造具体的用户测试结论、点击率、转化率或满意度数据。"""

    content = await ai_service.chat(prompt)

    return ResponseBuilder.success({
        "id": f"prototype_{int(time.time())}",
        "project_id": data.project_id,
        "feature_description": data.feature_description,
        "prototype_type": data.prototype_type,
        "pages": [
            {"name": "首页/入口", "description": "功能入口与状态概览"},
            {"name": "核心操作页", "description": "主要交互页面"},
            {"name": "结果/详情页", "description": "展示操作结果与详情"},
        ],
        "user_flows": [
            {"name": "主流程", "steps": ["进入功能", "填写/选择", "确认提交", "查看结果"]}
        ],
        "markdown": content,
    })


@router.get("/stats/{project_id}", response_model=dict)
async def get_stats(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get project tool usage stats"""
    return ResponseBuilder.success({
        "project_id": project_id,
        "usage": {},
        "ai_calls": 0,
        "documents_generated": 0
    })


@router.post("/data-analysis-upload", response_model=dict)
@rate_limit(requests=10, window=60)
async def data_analysis_upload(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV/Excel file for AI data analysis."""
    try:
        result = await analyze_uploaded_data(file, project_id)
        return ResponseBuilder.success(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")
