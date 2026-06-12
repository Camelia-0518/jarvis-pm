"""系统健康与功能分级端点"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.feature_tiers import FEATURE_TIERS, get_tier_summary, get_tier, FeatureTier
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("/system/feature-tiers", response_model=dict)
async def feature_tiers():
    """返回完整的功能分级注册表 + 统计摘要"""
    return ResponseBuilder.success({
        "summary": get_tier_summary(),
        "tiers": {path: tier.value for path, tier in sorted(FEATURE_TIERS.items())},
    })


@router.get("/system/health", response_model=dict)
async def health_check(db: AsyncSession = Depends(get_db)):
    """系统健康检查 — 数据库连通性 + 分级统计"""
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    summary = get_tier_summary()

    return ResponseBuilder.success({
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "feature_tiers": summary,
    })


@router.get("/system/audit", response_model=dict)
async def audit_logs(
    workspace_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """查询审计日志"""
    query = select(AuditLog).order_by(desc(AuditLog.created_at))
    if workspace_id:
        query = query.where(AuditLog.workspace_id == workspace_id)

    result = await db.execute(query.limit(limit))
    logs = result.scalars().all()

    return ResponseBuilder.success([
        {
            "id": l.id, "user_id": l.user_id, "workspace_id": l.workspace_id,
            "action": l.action, "resource_type": l.resource_type, "resource_id": l.resource_id,
            "summary": l.summary,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ])
