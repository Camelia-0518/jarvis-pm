"""Workflow API endpoints

提供工作流定义查询、执行、流式执行等功能。
"""


from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uuid
import asyncio
import json
import logging
import time
import traceback
from cachetools import TTLCache

from app.services.workflow_engine import WorkflowEngine, STANDARD_WORKFLOWS
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user_id
from app.services.skill_processor import skill_processor
from app.core.responses import ResponseBuilder
from app.core.database import AsyncSessionLocal
from app.models.prd import PRD, PRDStatus
from app.models.delivery_plan import DeliveryPlan
from app.models.prd_annotation import PRDAnnotation, AnnotationType
from app.models.requirement import Requirement

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory execution storage with TTL to prevent memory leaks
# maxsize=1000, ttl=3600s (1 hour) — old records auto-evicted
execution_records: TTLCache = TTLCache(maxsize=1000, ttl=3600)

# Hold references to background tasks to prevent GC from cancelling them.
# asyncio.create_task returns a Task that is only weakly referenced by the event loop;
# if we drop the only strong reference the task may be garbage-collected prematurely.
_background_tasks: set = set()


# ============== Request/Response Models ==============

class WorkflowExecuteRequest(BaseModel):
    workflow_name: str = Field(..., min_length=1, description="工作流名称/ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="初始输入参数")
    project_id: Optional[str] = Field(default=None, description="关联项目ID")
    context: Optional[Dict[str, str]] = Field(default=None, description="执行上下文")


class WorkflowStepResult(BaseModel):
    step_name: str
    skill_id: str
    status: str
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration: Optional[float] = None


class WorkflowExecuteResponse(BaseModel):
    execution_id: str
    workflow: str
    completed: bool
    results: List[WorkflowStepResult]
    outputs: Dict[str, Any]
    duration: Optional[float] = None
    error: Optional[str] = None


# ============== Helpers ==============

class SkillExecutionError(Exception):
    """Raised when a skill execution returns success=False."""
    def __init__(self, skill_id: str, error: str, is_empty_output: bool = False):
        self.skill_id = skill_id
        self.error = error
        self.is_empty_output = is_empty_output
        super().__init__(f"[{skill_id}] {error}")


def _create_skill_executor():
    """Create a skill executor bound to the real skill processor."""
    async def executor(skill_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        result = await skill_processor.execute_skill(skill_id, inputs)
        if not result.get("success"):
            error_msg = result.get("error", "Skill execution failed")
            is_empty = "empty output" in error_msg.lower() or "no substantive content" in error_msg.lower()
            raise SkillExecutionError(skill_id, error_msg, is_empty_output=is_empty)
        output = result.get("output", {})
        if "formatted_output" in result and isinstance(output, dict):
            output["formatted_output"] = result["formatted_output"]
        output["_meta"] = {
            "execution_time_ms": result.get("execution_time", 0),
            "token_usage": result.get("token_usage", {}),
        }
        return output
    return executor


# ============== Endpoints ==============

@rate_limit(requests=100, window=60)
@router.get("/templates", response_model=dict)
async def list_workflows():
    """获取所有预置工作流模板列表"""
    engine = WorkflowEngine(skill_executor=_create_skill_executor())
    return ResponseBuilder.success(engine.get_workflow_list())


@rate_limit(requests=100, window=60)
@router.get("/templates/{workflow_name}", response_model=dict)
async def get_workflow_detail(workflow_name: str):
    """获取工作流模板详情"""
    engine = WorkflowEngine(skill_executor=_create_skill_executor())
    detail = engine.get_workflow_detail(workflow_name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_name} 不存在")
    return ResponseBuilder.success(detail)


@rate_limit(requests=30, window=60)
@router.post("/execute", response_model=dict)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    user_id: str = Depends(get_current_user_id),
):
    """同步执行工作流

    按顺序执行工作流中的每个步骤，等待全部完成后返回结果。
    有 project_id 时自动持久化每步输出到数据库。
    """
    engine = WorkflowEngine(skill_executor=_create_skill_executor())

    if request.workflow_name not in STANDARD_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"工作流 {request.workflow_name} 不存在")

    execution_id = str(uuid.uuid4())
    created_resources: Dict[str, str] = {}

    try:
        result = await engine.execute_workflow(
            workflow_name=request.workflow_name,
            initial_inputs=request.inputs,
            stop_on_error=True
        )

        # Persist each completed step if we have a project
        if request.project_id and result.get("results"):
            for step_result in result["results"]:
                if step_result.get("status") == "completed":
                    output = step_result.get("output", {})
                    if isinstance(output, dict):
                        await _persist_step_output(
                            skill_id=step_result.get("skill_id", ""),
                            step_name=step_result.get("step_name", ""),
                            output=output,
                            project_id=request.project_id,
                            user_id=user_id,
                            created_resources=created_resources,
                        )

        record = {
            "execution_id": execution_id,
            "workflow": request.workflow_name,
            "project_id": request.project_id,
            "status": "completed" if result.get("completed") else "failed",
            "result": {
                **result,
                "created_resources": created_resources,
            },
            "context": request.context,
        }
        execution_records[execution_id] = record

        return ResponseBuilder.success({
            "execution_id": execution_id,
            **result,
            "created_resources": created_resources,
        })
    except Exception as e:
        execution_records[execution_id] = {
            "execution_id": execution_id,
            "workflow": request.workflow_name,
            "project_id": request.project_id,
            "status": "failed",
            "error": str(e),
            "context": request.context,
        }
        raise HTTPException(status_code=500, detail=str(e))


def _extract_text_from_output(output: Dict[str, Any]) -> str:
    """Extract text content from a step output, handling various formats."""
    if isinstance(output, str):
        return output
    # Try common keys for markdown/text content
    for key in ("formatted_output", "markdown", "content", "text", "result", "summary"):
        val = output.get(key)
        if isinstance(val, str) and val.strip():
            return val
    # Fallback: stringify if it looks like markdown
    if "title" in output or "sections" in output:
        return json.dumps(output, ensure_ascii=False, indent=2)
    return str(output) if output else ""


def _parse_duration_weeks(duration) -> int:
    """Parse duration string like '2周', '3周', '1个月' to number of weeks."""
    if isinstance(duration, (int, float)):
        return max(1, int(duration))
    if not isinstance(duration, str):
        return 1
    s = duration.strip()
    import re as _re
    num_match = _re.search(r'(\d+\.?\d*)', s)
    num = float(num_match.group(1)) if num_match else 1
    if "月" in s:
        return max(1, int(num * 4))
    if "天" in s or "日" in s:
        return max(1, int(num / 7) or 1)
    return max(1, int(num))


def _parse_relative_week(week_str) -> int:
    """Parse relative week string like '第1周' to week number (0-indexed)."""
    if isinstance(week_str, (int, float)):
        return int(week_str)
    if not isinstance(week_str, str):
        return 0
    import re as _re
    m = _re.search(r'第\s*(\d+)', week_str)
    if m:
        return int(m.group(1)) - 1
    m = _re.search(r'(\d+)', week_str)
    return (int(m.group(1)) - 1) if m else 0


def _normalize_milestone_plan_data(output: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    """Normalize LLM-generated milestone-plan output to match DB schema.

    AI prompt template produces:
      phases[].{name, duration(str), startDate/endDate(relative), deliverables, resources}
      risks[].{risk, mitigation}

    DB/frontend expects:
      phases[].{phase_id, name, start(ISO), end(ISO), duration_weeks(int), deliverables, milestone, checkpoint}
      risks[].{id, category, risk, probability, impact, risk_score, risk_level, prevention, contingency, trigger, owner}
      risk_matrix.{grid, summary}
      wbs.{tasks, total_tasks, total_effort_days}
      gantt.{items, start_date, total_days}
    """
    from datetime import datetime as _dt, timedelta as _td
    import re as _re

    today = _dt.now().strftime("%Y-%m-%d")

    # ---- 1. Normalize phases ----
    raw_phases = output.get("phases", [])
    if isinstance(raw_phases, dict):
        raw_phases = raw_phases.get("phases", raw_phases.get("milestones", []))
    if not isinstance(raw_phases, list):
        raw_phases = []

    normalized_phases = []
    cumulative_weeks = 0
    for i, p in enumerate(raw_phases):
        if not isinstance(p, dict):
            continue
        duration_weeks = _parse_duration_weeks(p.get("duration", "2周"))

        # Parse start/end: try ISO first, then relative week
        start_raw = p.get("start") or p.get("startDate") or ""
        end_raw = p.get("end") or p.get("endDate") or ""
        if isinstance(start_raw, str) and _re.match(r'^\d{4}-\d{2}-\d{2}', start_raw):
            start_date = start_raw
        else:
            start_week = _parse_relative_week(start_raw) if start_raw else cumulative_weeks
            start_d = _dt.now() + _td(weeks=start_week)
            start_date = start_d.strftime("%Y-%m-%d")
        if isinstance(end_raw, str) and _re.match(r'^\d{4}-\d{2}-\d{2}', end_raw):
            end_date = end_raw
        else:
            end_week = _parse_relative_week(end_raw) if end_raw else cumulative_weeks + duration_weeks
            end_d = _dt.now() + _td(weeks=end_week)
            end_date = end_d.strftime("%Y-%m-%d")

        phase_name = p.get("name", f"阶段{i + 1}")
        checkpoint_phases = {"需求分析", "系统设计", "测试验证", "部署上线", "项目启动"}

        normalized_phases.append({
            "phase_id": str(i + 1),
            "name": phase_name,
            "start": start_date,
            "end": end_date,
            "duration_weeks": duration_weeks,
            "deliverables": p.get("deliverables", [])[:5],
            "milestone": f"{phase_name}完成",
            "checkpoint": phase_name in checkpoint_phases,
        })
        cumulative_weeks += duration_weeks

    # ---- 2. Normalize risks ----
    raw_risks = output.get("risks", [])
    if isinstance(raw_risks, dict):
        raw_risks = raw_risks.get("risks", raw_risks.get("items", []))
    if not isinstance(raw_risks, list):
        raw_risks = []

    # Category detection by keyword
    CATEGORY_KEYWORDS = [
        ("需求风险", ["需求", "变更", "范围"]),
        ("技术风险", ["技术", "架构", "接口", "性能", "兼容", "数据迁移", "数据质量"]),
        ("合规风险", ["合规", "等保", "安全", "隐私", "测评"]),
        ("干系人风险", ["干系人", "用户", "领导", "科室", "参与"]),
        ("进度风险", ["进度", "延期", "协调", "供应商", "人员", "离职"]),
        ("资源风险", ["资源", "设备", "硬件", "预算"]),
        ("业务风险", ["业务", "中断", "抵触", "使用率"]),
    ]

    def _guess_category(risk_text: str) -> str:
        for cat, kws in CATEGORY_KEYWORDS:
            for kw in kws:
                if kw in risk_text:
                    return cat
        return "进度风险"

    def _guess_owner(category: str) -> str:
        mapping = {
            "需求风险": "产品经理", "技术风险": "技术负责人", "合规风险": "安全合规负责人",
            "干系人风险": "项目经理", "进度风险": "项目经理", "资源风险": "资源经理",
            "业务风险": "项目总监",
        }
        return mapping.get(category, "项目经理")

    normalized_risks = []
    for i, r in enumerate(raw_risks):
        risk_text = r.get("risk") or r.get("description") or r.get("name", "")
        mitigation = r.get("mitigation") or r.get("prevention") or r.get("contingency", "")
        category = r.get("category") or _guess_category(risk_text)

        # Split mitigation into prevention + contingency
        if "；" in mitigation:
            parts = mitigation.split("；")
            prevention = parts[0]
            contingency = parts[-1] if len(parts) > 1 else ""
        elif ";" in mitigation:
            parts = mitigation.split(";")
            prevention = parts[0]
            contingency = parts[-1] if len(parts) > 1 else ""
        else:
            prevention = mitigation[:80]
            contingency = "升级至项目指导委员会决策"

        # Default probability/impact (can't reliably infer from description alone)
        prob = 0.5
        impact = 0.5
        score = prob * impact

        normalized_risks.append({
            "id": f"RSK-{i + 1:03d}",
            "category": category,
            "risk": risk_text,
            "probability": prob,
            "impact": impact,
            "risk_score": score,
            "risk_level": "中",
            "prevention": prevention[:200],
            "contingency": contingency[:200],
            "trigger": "",
            "owner": r.get("owner") or _guess_owner(category),
        })

    # ---- 3. Build risk matrix from normalized risks ----
    risk_grid = {}
    for pl in ("低(0-0.3)", "中(0.3-0.5)", "高(0.5-1.0)"):
        for il in ("低(0-0.3)", "中(0.3-0.5)", "高(0.5-1.0)"):
            risk_grid[f"{pl}/{il}"] = {"count": 0, "risks": []}
    for r in normalized_risks:
        p_val = r["probability"]
        i_val = r["impact"]
        p_label = "低(0-0.3)" if p_val <= 0.3 else ("高(0.5-1.0)" if p_val > 0.5 else "中(0.3-0.5)")
        i_label = "低(0-0.3)" if i_val <= 0.3 else ("高(0.5-1.0)" if i_val > 0.5 else "中(0.3-0.5)")
        key = f"{p_label}/{i_label}"
        if key in risk_grid:
            risk_grid[key]["count"] += 1
            risk_grid[key]["risks"].append(r["id"])

    risk_matrix = {
        "grid": risk_grid,
        "total_risks": len(normalized_risks),
        "summary": {
            "极高": 0,
            "高": len([r for r in normalized_risks if r["risk_score"] > 0.3]),
            "中": len([r for r in normalized_risks if 0.1 < r["risk_score"] <= 0.3]),
            "低": len([r for r in normalized_risks if r["risk_score"] <= 0.1]),
        },
    }

    # ---- 4. Generate WBS from phases and risks ----
    wbs_tasks = []
    tid = 1
    phase_task_templates = {
        "项目启动": ["项目章程编写与审批", "组建项目团队", "召开项目启动会", "确定沟通机制"],
        "需求分析": ["业务需求调研", "需求规格说明书编写", "需求评审与确认", "原型设计"],
        "系统设计": ["系统架构设计", "数据库设计", "接口规范定义", "安全方案设计"],
        "开发实施": ["迭代1：核心功能开发", "迭代2：扩展功能开发", "迭代3：集成联调", "代码评审"],
        "测试验证": ["功能测试", "集成测试", "性能测试", "用户验收测试"],
        "部署上线": ["生产环境部署", "数据迁移与校验", "灰度发布", "正式上线切换"],
        "培训与交接": ["管理员培训", "操作员培训", "文档移交", "项目验收"],
        "运维保障": ["上线后陪跑", "问题跟踪修复", "运维报告", "知识库沉淀"],
    }

    for phase in normalized_phases:
        phase_name = phase["name"]
        templates = None
        for key, tmpl in phase_task_templates.items():
            if key in phase_name:
                templates = tmpl
                break
        if not templates:
            # Generic tasks based on deliverables
            templates = phase.get("deliverables", [])[:4] or [f"{phase_name}任务{i}" for i in range(1, 5)]
        for task_name in templates:
            effort_days = max(2, min(15, len(task_name) * 2 + 3))
            wbs_tasks.append({
                "id": f"WBS-{tid:03d}",
                "phase_id": phase["phase_id"],
                "phase_name": phase_name,
                "name": task_name,
                "effort_days": effort_days,
                "dependencies": [wbs_tasks[-1]["id"]] if wbs_tasks and tid > 1 else [],
                "role": "开发工程师",
                "priority": "P1",
                "phase": "一期",
            })
            tid += 1

    wbs = {
        "tasks": wbs_tasks,
        "total_tasks": len(wbs_tasks),
        "total_effort_days": sum(t["effort_days"] for t in wbs_tasks),
    }

    # ---- 5. Generate Gantt from WBS ----
    gantt_items = []
    current_offset = 0
    for task in wbs_tasks:
        duration = max(1, task["effort_days"] // 5)
        gantt_items.append({
            "id": task["id"],
            "name": task["name"],
            "phase": task["phase_name"],
            "start_offset_days": current_offset,
            "duration_weeks": duration,
            "dependencies": task.get("dependencies", []),
            "priority": task.get("priority", "P1"),
            "role": task.get("role", ""),
            "phase_label": task.get("phase", ""),
        })
        current_offset += duration * 7

    gantt = {
        "items": gantt_items,
        "total_days": current_offset or 90,
        "start_date": today,
    }

    # Resources estimate
    total_effort = wbs["total_effort_days"]
    resources = {
        "total_person_days": total_effort,
        "buffer_person_days": int(total_effort * 0.2),
        "total_with_buffer": int(total_effort * 1.2),
        "team_size": 5,
        "estimated_calendar_days": max(1, int(total_effort * 1.2 / 5)),
        "roles": [{"role": "开发工程师", "count": 3}, {"role": "测试工程师", "count": 1}, {"role": "项目经理", "count": 1}],
        "recommendation": f"建议团队规模 5 人，含风险缓冲 {int(total_effort * 0.2)} 人天（20%）",
    }

    return {
        "wbs": wbs,
        "milestones": {"phases": normalized_phases},
        "resources": resources,
        "gantt": gantt,
        "risks": normalized_risks,
        "risk_matrix": risk_matrix,
        "stakeholders": [],
    }


async def _persist_step_output(
    skill_id: str,
    step_name: str,
    output: Dict[str, Any],
    project_id: str,
    user_id: str,
    created_resources: Dict[str, str],
):
    """Persist a completed skill step's output to the appropriate database table."""
    logger.info(f"Skill chain persist: {skill_id}/{step_name} project={project_id}")

    text_output = _extract_text_from_output(output)

    try:
        async with AsyncSessionLocal() as db:
            if skill_id == "write-prd":
                title = output.get("title") or step_name
                if isinstance(title, dict):
                    title = title.get("title", "AI 生成的 PRD")
                if not isinstance(title, str) or not title.strip():
                    title = "AI 生成的 PRD"

                # Detect document type for display categorization
                doc_type = "prd"
                title_lower = str(title).lower()
                if any(kw in title_lower for kw in ["需求洞察", "洞察报告", "discovery"]):
                    doc_type = "discovery"
                elif any(kw in title_lower for kw in ["合规审查", "审查报告", "compliance"]):
                    doc_type = "audit"
                elif any(kw in title_lower for kw in ["项目章程", "project charter"]):
                    doc_type = "charter"
                elif any(kw in title_lower for kw in ["状态报告", "周报", "日报", "status report"]):
                    doc_type = "status_report"
                elif any(kw in title_lower for kw in ["ai产品", "ai产品prd", "大模型"]):
                    doc_type = "ai_model"
                elif any(kw in title_lower for kw in ["devops", "部署", "监控", "运维"]):
                    doc_type = "devops"
                elif any(kw in title_lower for kw in ["交付路径", "playbook", "标准化"]):
                    doc_type = "playbook"
                elif any(kw in title_lower for kw in ["复盘", "retrospective"]):
                    doc_type = "retrospective"
                elif any(kw in title_lower for kw in ["沟通简报", "stakeholder"]):
                    doc_type = "stakeholder_brief"

                new_prd = PRD(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    title=str(title)[:200],
                    version="1.0",
                    status=PRDStatus.DRAFT,
                    content={"chapters": {}, "source": "skill_chain"},
                    markdown=text_output,
                    ai_generated={"source": "skill_chain", "skill_id": skill_id, "step": step_name, "doc_type": doc_type},
                    created_by=user_id,
                )
                db.add(new_prd)
                print(f"[PERSIST] PRD added, committing...", flush=True)
                await db.commit()
                await db.refresh(new_prd)
                created_resources["prd_id"] = new_prd.id
                created_resources["prd_title"] = new_prd.title
                print(f"[PERSIST] PRD {new_prd.id} created successfully", flush=True)
                logger.info(f"Skill chain: created PRD {new_prd.id} from {skill_id}")

            elif skill_id == "milestone-plan":
                from app.models.delivery_plan import DeliveryPlan
                prd_id = created_resources.get("prd_id")
                normalized = _normalize_milestone_plan_data(output, project_id)

                plan = DeliveryPlan(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    prd_id=prd_id,
                    title=f"{created_resources.get('prd_title', '项目')} - 交付计划",
                    status="draft",
                    wbs=normalized["wbs"],
                    milestones=normalized["milestones"],
                    resources=normalized["resources"],
                    gantt=normalized["gantt"],
                    risks=normalized["risks"],
                    risk_matrix=normalized["risk_matrix"],
                    stakeholders=normalized["stakeholders"],
                    plan_markdown=text_output,
                    ai_generated={"source": "skill_chain", "skill_id": skill_id, "step": step_name},
                    created_by=user_id,
                )
                db.add(plan)
                await db.commit()
                await db.refresh(plan)
                created_resources["plan_id"] = plan.id
                logger.info(f"Skill chain: created delivery plan {plan.id} from {skill_id}")

            elif skill_id == "compliance-check":
                from app.models.prd_annotation import PRDAnnotation, AnnotationType
                prd_id = created_resources.get("prd_id")
                if not prd_id:
                    return
                issues = output.get("criticalIssues", []) or output.get("critical_issues", [])
                recommendations = output.get("recommendations", [])
                all_items = issues + recommendations
                for item in all_items[:10]:
                    text = item if isinstance(item, str) else item.get("description", str(item))
                    ann = PRDAnnotation(
                        prd_id=prd_id,
                        content=text[:500],
                        annotation_type=AnnotationType.ISSUE,
                        status="open",
                        created_by=user_id,
                    )
                    db.add(ann)
                await db.commit()
                logger.info(f"Skill chain: created {len(all_items[:10])} compliance annotations from {skill_id}")

            elif skill_id == "medical-review":
                from app.models.prd_annotation import PRDAnnotation, AnnotationType
                prd_id = created_resources.get("prd_id")
                if not prd_id:
                    return
                summary = output.get("summary", "")
                if summary:
                    ann = PRDAnnotation(
                        prd_id=prd_id,
                        content=f"[医疗评审] {str(summary)[:500]}",
                        annotation_type=AnnotationType.SUGGESTION,
                        status="open",
                        created_by=user_id,
                    )
                    db.add(ann)
                medical = output.get("medicalRationality", {})
                concerns = medical.get("concerns", []) if isinstance(medical, dict) else []
                for c in concerns[:5]:
                    text = c if isinstance(c, str) else str(c)
                    ann = PRDAnnotation(
                        prd_id=prd_id,
                        content=f"[合理性关注] {text[:500]}",
                        annotation_type=AnnotationType.ISSUE,
                        status="open",
                        created_by=user_id,
                    )
                    db.add(ann)
                await db.commit()
                logger.info(f"Skill chain: created medical review annotations from {skill_id}")

            elif skill_id == "requirement-analysis":
                from app.models.requirement import Requirement
                feature_list = output.get("featureList", {}) or output.get("feature_list", {})
                p0_features = feature_list.get("p0", [])
                for feature in p0_features[:5]:
                    req = Requirement(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        title=str(feature)[:200] if isinstance(feature, str) else str(feature.get("name", feature))[:200],
                        description=output.get("productOneLiner", "") or text_output[:500],
                        status="backlog",
                        priority="p0",
                        created_by=user_id,
                    )
                    db.add(req)
                await db.commit()
                logger.info(f"Skill chain: created requirements from {skill_id}")

    except Exception as e:
        logger.error(f"Skill chain persist failed for {skill_id}/{step_name}: {e}", exc_info=True)


async def _run_workflow_background(
    execution_id: str,
    workflow_name: str,
    inputs: Dict[str, Any],
    project_id: Optional[str],
    context: Optional[Dict[str, str]],
    user_id: str = "system",
):
    """后台执行工作流并通过 WebSocket 实时推送进度，每步完成后持久化结果"""
    from app.websocket.manager import websocket_manager

    task_ref = asyncio.current_task()
    if task_ref is not None:
        _background_tasks.add(task_ref)

    engine = WorkflowEngine(skill_executor=_create_skill_executor())
    created_resources: Dict[str, str] = {}
    try:
        results = []
        outputs = {}
        # 等待 WebSocket 连接就绪（前端在 POST 返回后才建立 WS 连接）
        for _ in range(10):
            if execution_id in websocket_manager.active_connections:
                break
            await asyncio.sleep(0.5)
        async for event in engine.execute_workflow_stream(
            workflow_name=workflow_name,
            initial_inputs=inputs
        ):
            await websocket_manager.broadcast_to_workflow(execution_id, event)
            if event["type"] == "step_complete":
                results.append(event)
                step_output = event.get("output", {})
                outputs[event.get("step_name", "")] = step_output
                print(f"[BG] step_complete: skill_id={event.get('skill_id', 'MISSING')}, step_name={event.get('step_name', 'MISSING')}, has_project={bool(project_id)}", flush=True)

                # 注入 timing/token 信息到 WebSocket 通知
                inner = step_output.get("output", step_output)
                meta = inner.get("_meta", {}) if isinstance(inner, dict) else {}
                await websocket_manager.broadcast_to_workflow(execution_id, {
                    "type": "step_detail",
                    "step_name": event.get("step_name", ""),
                    "skill_id": event.get("skill_id", ""),
                    "execution_time_ms": meta.get("execution_time_ms", 0),
                    "token_usage": meta.get("token_usage", {}),
                })

                # Persist to database if we have a project
                if project_id:
                    await _persist_step_output(
                        skill_id=event.get("skill_id", ""),
                        step_name=event.get("step_name", ""),
                        output=inner,
                        project_id=project_id,
                        user_id=user_id,
                        created_resources=created_resources,
                    )

            elif event["type"] == "step_error":
                step_error_info = {
                    "step_name": event.get("step_name", ""),
                    "error": event.get("error", "未知错误"),
                }
                await websocket_manager.broadcast_to_workflow(execution_id, {
                    "type": "error",
                    "error": step_error_info["error"],
                })
                # 保存错误到 results，避免丢失诊断信息
                results.append(event)
                break

        # 获取工作流定义以确定预期步骤数
        workflow_def = STANDARD_WORKFLOWS.get(workflow_name)
        expected_steps = len(workflow_def.steps) if workflow_def else 0

        is_completed = (
            len(results) == expected_steps
            and all(r.get("type") == "step_complete" for r in results)
        ) if results else False

        execution_records[execution_id] = {
            "execution_id": execution_id,
            "workflow": workflow_name,
            "project_id": project_id,
            "status": "completed" if is_completed else "failed",
            "result": {
                "outputs": outputs,
                "results": results,
                "created_resources": created_resources,
                "expected_steps": expected_steps,
                "completed_steps": len([r for r in results if r.get("type") == "step_complete"]),
            },
            "context": context,
        }

        await websocket_manager.send_complete(execution_id, outputs)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(
            "Workflow %s [%s] failed: %s\n%s",
            workflow_name, execution_id, e, tb
        )
        execution_records[execution_id] = {
            "execution_id": execution_id,
            "workflow": workflow_name,
            "project_id": project_id,
            "status": "failed",
            "error": f"{type(e).__name__}: {e}",
            "traceback": tb,
            "context": context,
        }
        await websocket_manager.send_error(execution_id, f"{type(e).__name__}: {e}")
    finally:
        if task_ref is not None:
            _background_tasks.discard(task_ref)


@rate_limit(requests=30, window=60)
@router.post("/execute-async", response_model=dict)
async def execute_workflow_async(
    request: WorkflowExecuteRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    """异步执行工作流

    立即返回 execution_id，工作流在后台执行。
    可通过 /executions/{execution_id} 轮询状态。
    """
    if request.workflow_name not in STANDARD_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"工作流 {request.workflow_name} 不存在")

    execution_id = str(uuid.uuid4())
    execution_records[execution_id] = {
        "execution_id": execution_id,
        "workflow": request.workflow_name,
        "project_id": request.project_id,
        "status": "running",
        "context": request.context,
    }

    task = asyncio.create_task(
        _run_workflow_background(
            execution_id,
            request.workflow_name,
            request.inputs,
            request.project_id,
            request.context,
            user_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return ResponseBuilder.success({
        "execution_id": execution_id,
        "workflow": request.workflow_name,
        "status": "running",
        "message": "工作流已提交后台执行，请轮询 /executions/{execution_id} 获取结果"
    })


# Skill chain mapping (matches frontend SKILL_CHAINS)
CHAIN_WORKFLOW_MAP = {
    "full-delivery": "full-delivery",
    "compliance-audit": "compliance-audit",
    "requirement-discovery": "requirement-discovery",
    "quick-prd": "quick-prd",
    "ai-model-prd": "ai-model-prd",
    "devops-prd": "devops-prd",
    "project-kickoff": "project-kickoff",
    "weekly-report": "weekly-report",
    "stakeholder-brief": "stakeholder-brief",
    "delivery-playbook": "delivery-playbook",
    "retrospective": "retrospective",
}


class WorkflowChainExecuteRequest(BaseModel):
    chain_id: str = Field(..., min_length=1, description="技能链ID")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="初始输入参数")
    project_id: Optional[str] = Field(default=None, description="关联项目ID")
    context: Optional[Dict[str, str]] = Field(default=None, description="执行上下文")


@rate_limit(requests=10, window=60)
@router.post("/execute-chain", response_model=dict)
async def execute_skill_chain(
    request: WorkflowChainExecuteRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
):
    """执行技能链

    根据 chain_id 映射到对应的工作流定义，在后台异步执行。
    返回 execution_id，前端轮询 /executions/{execution_id} 获取进度和结果。
    每步完成后自动持久化到数据库（PRD/交付计划/批注等）。
    """
    workflow_name = CHAIN_WORKFLOW_MAP.get(request.chain_id)
    if not workflow_name:
        raise HTTPException(status_code=404, detail=f"技能链 {request.chain_id} 不存在")

    if workflow_name not in STANDARD_WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"工作流 {workflow_name} 未注册")

    execution_id = str(uuid.uuid4())
    execution_records[execution_id] = {
        "execution_id": execution_id,
        "workflow": workflow_name,
        "chain_id": request.chain_id,
        "project_id": request.project_id,
        "status": "running",
        "context": request.context,
        "started_at": time.time(),
    }

    task = asyncio.create_task(
        _run_workflow_background(
            execution_id,
            workflow_name,
            request.inputs,
            request.project_id,
            request.context,
            user_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return ResponseBuilder.success({
        "execution_id": execution_id,
        "chain_id": request.chain_id,
        "workflow": workflow_name,
        "status": "running",
        "message": "技能链已提交后台执行，请轮询 /executions/{execution_id} 获取结果"
    })


@rate_limit(requests=100, window=60)
@router.get("/executions/{execution_id}", response_model=dict)
async def get_execution_status(execution_id: str):
    """获取工作流执行状态"""
    if execution_id not in execution_records:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return ResponseBuilder.success(execution_records[execution_id])


@rate_limit(requests=100, window=60)
@router.get("/executions", response_model=dict)
async def list_executions(
    workflow: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """获取工作流执行历史列表"""
    records = list(execution_records.values())

    if workflow:
        records = [r for r in records if r.get("workflow") == workflow]
    if status:
        records = [r for r in records if r.get("status") == status]

    total = len(records)
    paginated = records[offset:offset + limit]

    return ResponseBuilder.paginated(
        data=paginated,
        page=offset // limit + 1,
        limit=limit,
        total=total
    )