"""Delivery service — coordinates delivery planning agents"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.agents.registry import AgentRegistry
from app.core.exceptions import ExternalAPIError
from app.models.delivery_plan import DeliveryPlan, DeliveryStatus
from app.models.prd import PRD
from app.models.project import Project
from app.schemas.delivery import sanitize_delivery_payload

logger = logging.getLogger(__name__)


class DeliveryService:
    """Orchestrates delivery plan generation using specialized agents"""

    def __init__(self):
        self._registry = AgentRegistry()

    async def _run_required_agent(self, name: str, input_data: dict) -> Any:
        """Run a required agent with existence check, success check, and data fallback.

        Raises RuntimeError if the agent is not registered or its execution fails,
        so callers get a clear error instead of an AttributeError or silent corruption.
        """
        agent = self._registry.create_instance(name)
        if agent is None:
            raise ExternalAPIError(service=name, message="Agent not registered")

        result = await agent.execute(input_data)
        if not result.success:
            raise ExternalAPIError(service=name, message=result.error or "Agent execution returned failure")

        if result.data is None:
            result.data = {}

        return result

    async def generate_delivery_plan(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
        prd_id: Optional[str] = None,
        industry: str = "medical",
        custom_input: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        product_name = project.name
        description = project.description or ""
        prd_content = ""
        if prd_id:
            prd = await db.get(PRD, prd_id)
            if prd:
                prd_content = prd.markdown or ""

        # Filter out None values to avoid downstream strptime/type errors
        filtered_input = {k: v for k, v in (custom_input or {}).items() if v is not None}
        input_data = {
            "product_name": product_name,
            "description": description,
            "prd_content": prd_content,
            "industry": industry or project.industry or "medical",
            **filtered_input,
        }

        # Phase 1: Generate delivery plan (WBS + milestones + resources + gantt)
        planner_result = await self._run_required_agent("delivery_planner", input_data)

        # Phase 2: Risk analysis
        risk_result = await self._run_required_agent("risk_manager", {**input_data, "project_phase": "planning"})

        # Phase 3: Stakeholder coordination
        stakeholder_result = await self._run_required_agent("stakeholder_coordinator", input_data)

        # Build combined result
        plan_data = {
            "project_id": project_id,
            "prd_id": prd_id,
            "title": f"{product_name} 交付计划",
            "industry": input_data["industry"],
            "status": DeliveryStatus.DRAFT.value,
            "wbs": planner_result.data.get("wbs", {}),
            "milestones": planner_result.data.get("milestones", {}),
            "resources": planner_result.data.get("resources", {}),
            "gantt": planner_result.data.get("gantt", {}),
            "risks": risk_result.data.get("risks", []),
            "risk_matrix": risk_result.data.get("matrix", {}),
            "risk_response_plan": risk_result.data.get("response_plan", {}),
            "stakeholders": stakeholder_result.data.get("stakeholders", []),
            "raci": stakeholder_result.data.get("raci", {}),
            "communication_plan": stakeholder_result.data.get("communication_plan", {}),
            "status_template": stakeholder_result.data.get("status_template", {}),
            "plan_markdown": planner_result.output,
            "risk_markdown": risk_result.output,
            "stakeholder_markdown": stakeholder_result.output,
            "ai_generated": {
                "planner_success": planner_result.success,
                "risk_success": risk_result.success,
                "stakeholder_success": stakeholder_result.success,
                "generated_at": __import__("datetime").datetime.now().isoformat(),
            },
            "created_by": user_id,
        }

        # Sanitize agent output before persistence — strips malformed fields
        # and fills defaults so unstable AI output won't corrupt the database.
        plan_data = sanitize_delivery_payload(plan_data)

        return plan_data

    async def save_delivery_plan(
        self,
        db: AsyncSession,
        plan_data: Dict[str, Any],
    ) -> DeliveryPlan:
        plan = DeliveryPlan(**{k: v for k, v in plan_data.items() if k in DeliveryPlan.__table__.columns.keys()})
        db.add(plan)
        await db.flush()
        await db.refresh(plan)
        return plan

    async def get_delivery_plan(self, db: AsyncSession, plan_id: str) -> Optional[DeliveryPlan]:
        result = await db.execute(
            select(DeliveryPlan).where(
                DeliveryPlan.id == plan_id,
                DeliveryPlan.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_delivery_plans(
        self,
        db: AsyncSession,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        query = select(DeliveryPlan).where(DeliveryPlan.deleted_at.is_(None))
        if project_id:
            query = query.where(DeliveryPlan.project_id == project_id)
        if user_id:
            query = query.where(DeliveryPlan.created_by == user_id)
        if status:
            query = query.where(DeliveryPlan.status == status)
        # Count total BEFORE pagination
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(DeliveryPlan.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = await db.execute(query)
        plans = result.scalars().all()

        return {
            "items": [
                {
                    "id": p.id,
                    "project_id": p.project_id,
                    "prd_id": p.prd_id,
                    "title": p.title,
                    "status": p.status.value if p.status else "draft",
                    "industry": p.industry,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    # Summary counts — defensively handle JSON fields that may be list or dict
                    "wbs_task_count": (
                        len((p.wbs or {}).get("tasks", [])) if isinstance(p.wbs, dict)
                        else len(p.wbs) if isinstance(p.wbs, list)
                        else 0
                    ),
                    "risk_count": len(p.risks) if isinstance(p.risks, list) else 0,
                    "milestone_count": (
                        len((p.milestones or {}).get("phases", [])) if isinstance(p.milestones, dict)
                        else len(p.milestones) if isinstance(p.milestones, list)
                        else 0
                    ),
                }
                for p in plans
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }

    async def get_dashboard_summary(self, db: AsyncSession, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get delivery dashboard summary with health metrics.

        Risk Health scoring:
          - red:   any plan at_risk, OR high-risk ratio > 40%
          - yellow: high risks exist, OR avg > 3 risks per plan
          - green:  low risk

        Delivery Health scoring:
          - red:   >20% plans at_risk, OR task completion < 30%, OR overdue phases exist
          - yellow: >70% plans still draft, OR task completion < 50%
          - green:  healthy progress
        """
        from datetime import date as _date

        query = select(DeliveryPlan).where(DeliveryPlan.deleted_at.is_(None))
        if project_id:
            query = query.where(DeliveryPlan.project_id == project_id)
        result = await db.execute(query)
        plans = result.scalars().all()

        total = len(plans)
        at_risk = sum(1 for p in plans if p.status == DeliveryStatus.AT_RISK)
        in_progress = sum(1 for p in plans if p.status == DeliveryStatus.IN_PROGRESS)
        completed = sum(1 for p in plans if p.status == DeliveryStatus.COMPLETED)
        draft = sum(1 for p in plans if p.status == DeliveryStatus.DRAFT)

        # Risk statistics
        total_risks = sum(len(p.risks) if isinstance(p.risks, list) else 0 for p in plans)
        high_risks = sum(
            sum(1 for r in (p.risks or []) if isinstance(r, dict) and r.get("risk_level") in ("极高", "高"))
            for p in plans
        )
        risk_ratio = high_risks / max(total_risks, 1)

        # Task completion statistics
        total_tasks = 0
        completed_tasks = 0
        in_progress_tasks = 0
        for p in plans:
            wbs = p.wbs if isinstance(p.wbs, dict) else {}
            tasks = wbs.get("tasks", []) if isinstance(wbs, dict) else []
            if isinstance(tasks, list):
                for t in tasks:
                    if isinstance(t, dict):
                        total_tasks += 1
                        status = t.get("status", "todo")
                        if status == "done":
                            completed_tasks += 1
                        elif status == "in_progress":
                            in_progress_tasks += 1

        task_completion = completed_tasks / max(total_tasks, 1)

        # Phase progress & overdue check
        total_phases = 0
        total_progress = 0
        overdue_count = 0
        today = _date.today()
        for p in plans:
            ms = p.milestones
            if isinstance(ms, dict):
                phases = ms.get("phases", [])
            elif isinstance(ms, list):
                phases = ms
            else:
                phases = []
            if not isinstance(phases, list):
                continue
            for ph in phases:
                if not isinstance(ph, dict):
                    continue
                total_phases += 1
                total_progress += ph.get("progress", 0) if isinstance(ph.get("progress"), (int, float)) else 0
                # Check overdue: end date past and progress < 100
                end_str = ph.get("end") or ph.get("endDate") or ""
                if isinstance(end_str, str) and end_str:
                    try:
                        end_date = _date.fromisoformat(end_str[:10])
                        prog = ph.get("progress", 0)
                        if isinstance(prog, (int, float)) and end_date < today and prog < 100:
                            overdue_count += 1
                    except (ValueError, TypeError):
                        pass

        avg_progress = round(total_progress / max(total_phases, 1), 1)

        # ---- Health scores ----
        active = in_progress + completed
        active_ratio = active / max(total, 1)

        # Risk health
        if at_risk > 0 or risk_ratio > 0.4:
            risk_health = "red"
        elif high_risks > 0 or total_risks > total * 3:
            risk_health = "yellow"
        else:
            risk_health = "green"

        # Delivery health
        if at_risk > total * 0.2 or task_completion < 0.3 or overdue_count > 0:
            delivery_health = "red"
        elif active_ratio < 0.3 or task_completion < 0.5:
            delivery_health = "yellow"
        else:
            delivery_health = "green"

        return {
            "total_plans": total,
            "draft": draft,
            "at_risk": at_risk,
            "in_progress": in_progress,
            "completed": completed,
            "total_risks": total_risks,
            "high_risks": high_risks,
            "risk_health": risk_health,
            "delivery_health": delivery_health,
            # New task-level metrics
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "task_completion_rate": round(task_completion, 2),
            "total_phases": total_phases,
            "avg_phase_progress": avg_progress,
            "overdue_phases": overdue_count,
            # Health breakdown for UI
            "health_detail": {
                "risk": {
                    "score": risk_health,
                    "at_risk_plans": at_risk,
                    "high_risk_ratio": round(risk_ratio, 2),
                    "avg_risks_per_plan": round(total_risks / max(total, 1), 1),
                },
                "delivery": {
                    "score": delivery_health,
                    "active_ratio": round(active_ratio, 2),
                    "task_completion": round(task_completion, 2),
                    "overdue_phases": overdue_count,
                },
            },
        }


delivery_service = DeliveryService()
