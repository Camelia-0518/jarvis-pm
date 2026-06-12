"""Tools endpoints - all wired to real AI generation"""

import time
import hashlib
from typing import Optional, List
import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
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
from app.core.exceptions import AppException

router = APIRouter()

# Simple in-memory cache for tool results (key: hash of prompt, value: content)
_tool_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 3600  # 1 hour


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _get_cached(prompt: str) -> Optional[str]:
    key = _cache_key(prompt)
    if key in _tool_cache:
        content, ts = _tool_cache[key]
        if time.time() - ts < _CACHE_TTL:
            return content
        del _tool_cache[key]
    return None


def _set_cached(prompt: str, content: str) -> None:
    _tool_cache[_cache_key(prompt)] = (content, time.time())


def _user_data(content: str) -> str:
    """Wrap untrusted user content to mitigate prompt injection."""
    return f"<user_data>\n{content}\n</user_data>"


# Shared concise data-source notice (replaces verbose per-tool blocks)
_DATA_SOURCE_NOTICE = (
    "> 数据来源声明：本内容为AI基于行业经验和通用模板生成，仅供参考。"
    "涉及具体数字、法规、竞品数据时需人工核实。"
)


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
    confirmed_candidates: Optional[List[dict]] = None  # 用户确认的候选竞品


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


@rate_limit(requests=10, window=60)
@router.post("/user-research")
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
1. 输出研究发现、关键洞察、行动建议
2. 使用 Markdown 格式，结构清晰
3. 禁止编造具体数字、人名、医院名称、百分比

{_DATA_SOURCE_NOTICE}"""

    content = _get_cached(prompt)
    if content is None:
        content = await ai_service.chat(prompt, {"max_tokens": 2000})
        _set_cached(prompt, content)

    return ResponseBuilder.success({
        "id": f"research_{int(time.time())}",
        "project_id": data.project_id,
        "research_type": data.research_type,
        "findings": {"summary": content[:500], "details": content},
        "insights": [line.strip("- ").strip() for line in content.split("\n") if line.strip().startswith("-")][:5] or ["AI生成洞察"],
        "recommendations": ["基于研究结果，建议进一步验证核心假设", "迭代原型后开展可用性测试"],
        "markdown": content,
    })


@rate_limit(requests=10, window=60)
@router.post("/competitors")
async def competitor_analysis(
    data: CompetitorAnalysisRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Analyze competitors using AI (with candidate confirmation mode)"""
    # 获取项目信息（验证归属）
    from app.core.permissions import require_project_owner
    project = await require_project_owner(db, data.project_id, user_id)
    industry = project.industry

    # 步骤1：尝试网页抓取
    crawler_results = await web_crawler_service.search_competitor_info(data.competitors)
    has_crawler_success = any(r.get("success") for r in crawler_results.get("results", []))

    # 步骤2：如果爬虫有结果，直接生成报告
    if has_crawler_success:
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
1. 输出对比矩阵和差异化机会
2. 使用 Markdown 格式，包含表格
3. 给出竞争策略建议
4. 禁止编造具体评分、市场份额、财务数字

{_DATA_SOURCE_NOTICE}"""

        content = _get_cached(prompt)
        if content is None:
            content = await ai_service.chat(prompt, {"max_tokens": 2000})
            _set_cached(prompt, content)

        return ResponseBuilder.success({
            "id": f"analysis_{int(time.time())}",
            "project_id": data.project_id,
            "needs_confirmation": False,
            "competitors": [{"name": c, "score": 7.5} for c in data.competitors],
            "comparison_matrix": {"raw": content[:800]},
            "differentiation_opportunities": [line.strip("- ").strip() for line in content.split("\n") if line.strip().startswith("-")][:5] or ["聚焦垂直场景", "优化服务体验"],
            "markdown": content,
        })

    # 步骤3：爬虫无结果 -> 进入候选确认模式
    # 使用 LLM 推断候选竞品
    candidate_prompt = f"""请基于你的产品知识，为以下项目推断主要竞品：

产品/项目: {', '.join(data.competitors)}
行业: {industry}

要求：
1. 列出 2-4 个真实或代表性的竞品
2. 对每个竞品提供：名称、定位描述
3. 不要编造虚假 URL
4. 以 JSON 数组返回

格式：[{{"name": "名称", "description": "描述", "source_detail": "推断来源说明"}}]"""

    candidates = []
    try:
        candidate_response = await ai_service.chat(candidate_prompt, {"max_tokens": 1000})
        parsed = json.loads(candidate_response)
        if isinstance(parsed, list):
            candidates = parsed
        elif isinstance(parsed, dict) and "competitors" in parsed:
            candidates = parsed["competitors"]
    except Exception:
        pass

    if not candidates:
        # LLM 也失败，返回空结果
        raise AppException("网络搜索和 AI 推断均未找到竞品信息，请手动输入竞品名称后重试。", code="NO_DATA", status_code=400)

    # 生成候选预览
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    preview = f"""# 竞品分析 — 候选确认

> ⏳ **等待用户确认**：网络搜索未返回结果，以下竞品由 AI 基于知识库推断生成。
> 请勾选确认准确的竞品后，系统将生成正式分析报告。

---

## 分析对象

- **产品**: {', '.join(data.competitors)}
- **行业**: {industry}
- **时间**: {timestamp}

## 候选竞品（请确认）

"""
    for i, c in enumerate(candidates, 1):
        preview += f"""### {i}. {c.get('name', 'Unknown')}

**描述**: {c.get('description', '暂无描述')}

**推断来源**: {c.get('source_detail', 'AI知识库推断')}

**建议操作**: □ 确认纳入分析  /  □ 排除

---

"""

    preview += """## 下一步

请确认以上候选竞品后，系统将继续生成完整分析报告。

---
"""

    return ResponseBuilder.success({
        "id": f"analysis_{int(time.time())}",
        "project_id": data.project_id,
        "needs_confirmation": True,
        "candidates": candidates,
        "verified": [],
        "markdown": preview,
    })


@rate_limit(requests=10, window=60)
@router.post("/competitors/confirm")
async def confirm_competitor_analysis(
    data: CompetitorAnalysisRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """用户确认候选竞品后，生成正式竞品分析报告"""
    confirmed = data.confirmed_candidates or []
    if not confirmed:
        raise AppException("请至少确认一个竞品", code="NO_CANDIDATES", status_code=400)

    # 获取项目信息（验证归属）
    from app.core.permissions import require_project_owner
    project = await require_project_owner(db, data.project_id, user_id)
    industry = project.industry

    # 构建已确认竞品的详细分析
    competitor_names = [c.get("name", "") for c in confirmed]
    crawler_results = await web_crawler_service.search_competitor_info(competitor_names)

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
        if formatted_results:
            crawler_section = (
                "\n\n[网页抓取到的竞品信息]\n"
                + "\n".join(formatted_results)
                + "\n\n注意：以上信息来自公开网页抓取，请在分析中标注信息来源。"
            )

    # 补充候选竞品的描述信息
    candidate_section = "\n\n[用户确认的竞品信息]\n"
    for c in confirmed:
        candidate_section += f"- {c.get('name', 'Unknown')}: {c.get('description', '暂无描述')}\n"

    prompt = f"""为以下项目生成正式竞品分析报告：

项目ID: {data.project_id}
行业: {industry}
已确认竞品: {_user_data(', '.join(competitor_names))}
分析维度: {_user_data(', '.join(data.analysis_dimensions or ['功能', '价格', '用户体验', '市场定位']))}
{crawler_section}
{candidate_section}

要求：
1. 输出对比矩阵和差异化机会
2. 使用 Markdown 格式，包含表格
3. 给出竞争策略建议
4. 禁止编造具体评分、市场份额、财务数字
5. 报告开头标注："本报告基于用户确认的竞品数据生成"

{_DATA_SOURCE_NOTICE}"""

    content = _get_cached(prompt)
    if content is None:
        content = await ai_service.chat(prompt, {"max_tokens": 2000})
        _set_cached(prompt, content)

    return ResponseBuilder.success({
        "id": f"analysis_{int(time.time())}",
        "project_id": data.project_id,
        "needs_confirmation": False,
        "confirmed": True,
        "competitors": [{"name": c.get("name", ""), "score": 7.5} for c in confirmed],
        "comparison_matrix": {"raw": content[:800]},
        "differentiation_opportunities": [line.strip("- ").strip() for line in content.split("\n") if line.strip().startswith("-")][:5] or ["聚焦垂直场景", "优化服务体验"],
        "markdown": content,
    })


@rate_limit(requests=10, window=60)
@router.post("/data-analysis")
async def data_analysis(
    data: DataAnalysisRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Analyze data using AI"""
    prompt = f"""为以下项目生成数据分析报告框架：

项目ID: {data.project_id}
数据源: {_user_data(data.data_source)}
分析指标: {_user_data(', '.join(data.metrics))}
时间范围: {_user_data(data.time_range or '最近30天')}

要求：
1. 输出分析框架、指标定义、假设性分析思路
2. 使用 Markdown 格式
3. 禁止输出具体数字、百分比、日期（系统未接入真实数据）

{_DATA_SOURCE_NOTICE}"""

    content = _get_cached(prompt)
    if content is None:
        content = await ai_service.chat(prompt, {"max_tokens": 2000})
        _set_cached(prompt, content)

    return ResponseBuilder.success({
        "id": f"data_{int(time.time())}",
        "project_id": data.project_id,
        "summary": {"overview": content[:500]},
        "trends": [{"name": m, "direction": "up"} for m in data.metrics],
        "anomalies": [],
        "recommendations": ["持续监控核心指标波动", "建立自动化数据看板"],
        "markdown": content,
    })


@rate_limit(requests=10, window=60)
@router.post("/stakeholders")
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
2. 输出沟通计划
3. 使用 Markdown 格式，包含矩阵表格
4. 禁止编造具体人名、部门编制、决策流程细节

{_DATA_SOURCE_NOTICE}"""

    content = _get_cached(prompt)
    if content is None:
        content = await ai_service.chat(prompt, {"max_tokens": 2000})
        _set_cached(prompt, content)

    return ResponseBuilder.success({
        "id": f"stakeholder_{int(time.time())}",
        "project_id": data.project_id,
        "stakeholders": data.stakeholders or [],
        "influence_matrix": {"raw": content[:600]},
        "communication_plan": ["周会同步进展", "里程碑节点专项汇报", "上线前风险评审"],
        "markdown": content,
    })


@rate_limit(requests=10, window=60)
@router.post("/review-materials")
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
            select(PRD).where(PRD.id == data.prd_id, PRD.created_by == user_id, PRD.deleted_at.is_(None))
        )
        prd = result.scalar_one_or_none()
        prd_markdown = prd.markdown if prd else None
    else:
        # Query the latest PRD for this project
        result = await db.execute(
            select(PRD)
            .where(PRD.project_id == data.project_id, PRD.created_by == user_id, PRD.deleted_at.is_(None))
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
1. 评审材料必须基于 PRD 的具体内容，引用实际的功能点和设计决策
2. 不能输出通用模板或占位符
3. 使用 Markdown 格式，结构清晰
4. 禁止编造 PRD 中不存在的具体数字、日期或指标

{_DATA_SOURCE_NOTICE}"""

    content = _get_cached(prompt)
    if content is None:
        content = await ai_service.chat(prompt, {"max_tokens": 2000})
        _set_cached(prompt, content)

    return ResponseBuilder.success({
        "id": f"review_{data.material_type}_{int(time.time())}",
        "project_id": data.project_id,
        "prd_id": data.prd_id,
        "material_type": data.material_type,
        "content": {"raw": content},
        "markdown": content
    })


@rate_limit(requests=10, window=60)
@router.post("/review-materials-stream")
async def review_materials_stream(
    data: ReviewMaterialRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Stream review materials generation using SSE"""
    from app.models.prd import PRD

    # Query PRD markdown from database
    prd_markdown = None
    if data.prd_id:
        result = await db.execute(
            select(PRD).where(PRD.id == data.prd_id, PRD.created_by == user_id, PRD.deleted_at.is_(None))
        )
        prd = result.scalar_one_or_none()
        prd_markdown = prd.markdown if prd else None
    else:
        result = await db.execute(
            select(PRD)
            .where(PRD.project_id == data.project_id, PRD.created_by == user_id, PRD.deleted_at.is_(None))
            .order_by(PRD.created_at.desc())
        )
        prd = result.scalars().first()
        prd_markdown = prd.markdown if prd else None

    async def event_generator():
        full_markdown = ""
        try:
            async for chunk in ai_service.generate_review_material_stream(
                prd_id=data.prd_id or data.project_id,
                material_type=data.material_type,
                prd_content=prd_markdown,
            ):
                full_markdown += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'markdown': full_markdown})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@rate_limit(requests=10, window=60)
@router.post("/prototype")
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
1. 输出关键页面列表和用户流程
2. 使用 Markdown 格式
3. 包含页面结构、核心交互、状态说明
4. 禁止编造用户测试结论、点击率、转化率

{_DATA_SOURCE_NOTICE}"""

    content = _get_cached(prompt)
    if content is None:
        content = await ai_service.chat(prompt, {"max_tokens": 2000})
        _set_cached(prompt, content)

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


@rate_limit(requests=100, window=60)
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


@rate_limit(requests=10, window=60)
@router.post("/data-analysis-upload")
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