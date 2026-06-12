"""Delivery management API endpoints"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.responses import ResponseBuilder
from app.core.security import get_current_user_id
from app.core.permissions import require_project_owner
from app.services.delivery_service import delivery_service
from app.models.delivery_plan import DeliveryPlan, DeliveryStatus
from app.models.audit_log import AuditLog

router = APIRouter()


class GenerateDeliveryRequest(BaseModel):
    project_id: str
    prd_id: Optional[str] = None
    industry: str = "medical"
    team_size: int = Field(default=5, ge=1, le=100)
    start_date: Optional[str] = None
    custom_input: Optional[Dict[str, Any]] = None


class GenerateSingleRequest(BaseModel):
    project_id: str
    prd_id: Optional[str] = None
    industry: str = "medical"
    agent_type: str = Field(..., description="delivery_planner | risk_manager | stakeholder_coordinator")



@router.post("/delivery/generate")
async def generate_delivery_plan(
    request: GenerateDeliveryRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete delivery plan including WBS, risk analysis, and stakeholder plan"""
    await require_project_owner(db, request.project_id, user_id)
    try:
        plan_data = await delivery_service.generate_delivery_plan(
            db=db,
            project_id=request.project_id,
            user_id=user_id,
            prd_id=request.prd_id,
            industry=request.industry,
            custom_input={
                "team_size": request.team_size,
                "start_date": request.start_date,
                **(request.custom_input or {}),
            },
        )
        plan = await delivery_service.save_delivery_plan(db, plan_data)

        db.add(AuditLog(
            user_id=user_id, workspace_id=plan.workspace_id if hasattr(plan, 'workspace_id') else None,
            action="create", resource_type="delivery", resource_id=plan.id,
            summary=f"生成了交付计划 {plan.title}",
        ))
        await db.commit()

        return ResponseBuilder.success(
            {
                "id": plan.id,
                "title": plan.title,
                "status": plan.status.value if plan.status else "draft",
                "wbs_tasks": len(plan.wbs.get("tasks", [])) if plan.wbs else 0,
                "risk_count": len(plan.risks) if plan.risks else 0,
                "milestone_phases": len(plan.milestones.get("phases", [])) if plan.milestones else 0,
                "stakeholder_count": len(plan.stakeholders) if plan.stakeholders else 0,
                "plan_markdown": plan.plan_markdown,
                "risk_markdown": plan.risk_markdown,
                "stakeholder_markdown": plan.stakeholder_markdown,
                "wbs": plan.wbs,
                "milestones": plan.milestones,
                "resources": plan.resources,
                "gantt": plan.gantt,
                "risks": plan.risks,
                "risk_matrix": plan.risk_matrix,
                "risk_response_plan": plan.risk_response_plan,
                "stakeholders": plan.stakeholders,
                "raci": plan.raci,
                "communication_plan": plan.communication_plan,
                "status_template": plan.status_template,
            },
            message="交付计划生成成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # Other exceptions handled by global exception handler (app.core.exceptions)


@router.post("/delivery/generate-single")
async def generate_single_component(
    request: GenerateSingleRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a single delivery component (plan, risk, or stakeholder)"""
    try:
        if request.agent_type not in ("delivery_planner", "risk_manager", "stakeholder_coordinator"):
            raise HTTPException(status_code=400, detail=f"Invalid agent_type: {request.agent_type}")

        from app.models.prd import PRD

        project = await require_project_owner(db, request.project_id, user_id)

        prd_content = ""
        if request.prd_id:
            prd = await db.get(PRD, request.prd_id)
            if prd:
                prd_content = prd.markdown or ""

        input_data = {
            "product_name": project.name,
            "description": project.description or "",
            "prd_content": prd_content,
            "industry": request.industry,
        }

        from app.services.delivery_service import delivery_service as ds
        result = await ds._run_required_agent(request.agent_type, input_data)

        return ResponseBuilder.success(
            {
                "agent_type": request.agent_type,
                "output": result.output,
                "data": result.data,
                "execution_time": result.execution_time,
            },
            message=f"{request.agent_type} 生成成功",
        )
    except HTTPException:
        raise


@router.get("/delivery/plans")
async def list_delivery_plans(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List delivery plans with optional filters"""
    result = await delivery_service.list_delivery_plans(
        db=db,
        project_id=project_id,
        user_id=None,
        status=status,
        page=page,
        limit=limit,
    )
    return ResponseBuilder.success(result)


@router.get("/delivery/plans/{plan_id}")
async def get_delivery_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single delivery plan by ID"""
    try:
        plan = await delivery_service.get_delivery_plan(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Delivery plan not found")

        return ResponseBuilder.success({
            "id": plan.id,
            "project_id": plan.project_id,
            "prd_id": plan.prd_id,
            "title": plan.title,
            "status": plan.status.value if plan.status else "draft",
            "industry": plan.industry,
            "wbs": plan.wbs,
            "milestones": plan.milestones,
            "resources": plan.resources,
            "gantt": plan.gantt,
            "risks": plan.risks,
            "risk_matrix": plan.risk_matrix,
            "risk_response_plan": plan.risk_response_plan,
            "stakeholders": plan.stakeholders,
            "raci": plan.raci,
            "communication_plan": plan.communication_plan,
            "status_template": plan.status_template,
            "plan_markdown": plan.plan_markdown,
            "risk_markdown": plan.risk_markdown,
            "stakeholder_markdown": plan.stakeholder_markdown,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        })
    except HTTPException:
        raise


@router.patch("/delivery/plans/{plan_id}")
async def update_delivery_plan(
    plan_id: str,
    updates: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Update delivery plan — supports status, title, markdown fields, wbs, milestones, gantt, risks"""
    try:
        plan = await delivery_service.get_delivery_plan(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Delivery plan not found")

        scalar_fields = {"status", "title", "plan_markdown", "risk_markdown", "stakeholder_markdown"}
        json_fields = {"wbs", "milestones", "resources", "gantt", "risks", "risk_matrix",
                       "stakeholders", "raci", "communication_plan", "status_template"}

        for key, value in updates.items():
            if key in scalar_fields:
                if key == "status":
                    try:
                        value = DeliveryStatus(value)
                    except ValueError:
                        raise HTTPException(status_code=400, detail=f"Invalid status: {value}")
                setattr(plan, key, value)
            elif key in json_fields and isinstance(value, (dict, list)):
                setattr(plan, key, value)

        await db.flush()
        return ResponseBuilder.success(message="更新成功")
    except HTTPException:
        raise


@router.delete("/delivery/plans/{plan_id}")
async def delete_delivery_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a delivery plan"""
    try:
        plan = await delivery_service.get_delivery_plan(db, plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Delivery plan not found")

        plan.soft_delete()
        await db.flush()
        return ResponseBuilder.success(message="删除成功")
    except HTTPException:
        raise


@router.get("/delivery/dashboard")
async def delivery_dashboard(
    project_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get delivery dashboard summary"""
    summary = await delivery_service.get_dashboard_summary(db, project_id)
    return ResponseBuilder.success(summary)
