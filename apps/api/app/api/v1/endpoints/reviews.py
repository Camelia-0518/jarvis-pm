"""Review checklist endpoints for PRD quality assurance

评审结果现在持久化到 ReviewRecord 模型（替代 project.settings 临时存储）。
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import get_current_user_id
from app.core.responses import ResponseBuilder
from app.core.permissions import require_project_owner
from app.models.project import Project
from app.models.review_record import ReviewRecord, ReviewType, ReviewStatus
from app.core.exceptions import AppException

router = APIRouter()


# ============== Checklist Data ==============

CHECKLISTS = {
    "medical": [
        {"id": "m1", "category": "数据安全", "text": "患者隐私信息是否脱敏展示？", "required": True},
        {"id": "m2", "category": "数据安全", "text": "敏感操作是否有审计日志？", "required": True},
        {"id": "m3", "category": "合规", "text": "是否满足等保三级要求？", "required": True},
        {"id": "m4", "category": "合规", "text": "是否需要患者知情同意/签字确认？", "required": True},
        {"id": "m5", "category": "合规", "text": "数据留存期限是否符合医疗法规？", "required": True},
        {"id": "m6", "category": "集成", "text": "是否需要对接 HIS/LIS/PACS 等现有系统？", "required": False},
        {"id": "m7", "category": "多院区", "text": "不同院区政策是否有差异需适配？", "required": False},
        {"id": "m8", "category": "通用", "text": "用户故事是否覆盖主流程和异常流程？", "required": True},
        {"id": "m9", "category": "通用", "text": "验收标准是否明确（Given-When-Then）？", "required": True},
        {"id": "m10", "category": "通用", "text": "是否定义了明确的性能/体验指标？", "required": False},
    ],
    "saas": [
        {"id": "s1", "category": "安全", "text": "用户认证和授权机制是否完善？", "required": True},
        {"id": "s2", "category": "安全", "text": "API 是否有速率限制和防滥用机制？", "required": True},
        {"id": "s3", "category": "商业", "text": "定价模式是否清晰？", "required": False},
        {"id": "s4", "category": "商业", "text": "是否考虑了多租户隔离？", "required": False},
        {"id": "s5", "category": "集成", "text": "是否提供标准 API 和 Webhook？", "required": False},
        {"id": "s6", "category": "通用", "text": "用户故事是否覆盖主流程和异常流程？", "required": True},
        {"id": "s7", "category": "通用", "text": "验收标准是否明确（Given-When-Then）？", "required": True},
        {"id": "s8", "category": "通用", "text": "是否定义了成功指标（北极星指标）？", "required": False},
    ],
    "ecommerce": [
        {"id": "e1", "category": "交易", "text": "支付流程是否安全（防篡改/防重放）？", "required": True},
        {"id": "e2", "category": "交易", "text": "退款/售后流程是否完整？", "required": True},
        {"id": "e3", "category": "库存", "text": "库存扣减是否考虑并发和超卖？", "required": True},
        {"id": "e4", "category": "物流", "text": "物流状态追踪是否完整？", "required": False},
        {"id": "e5", "category": "营销", "text": "优惠券/促销规则是否清晰？", "required": False},
        {"id": "e6", "category": "通用", "text": "用户故事是否覆盖主流程和异常流程？", "required": True},
        {"id": "e7", "category": "通用", "text": "验收标准是否明确（Given-When-Then）？", "required": True},
    ],
    "default": [
        {"id": "d1", "category": "需求", "text": "用户故事是否覆盖主流程和异常流程？", "required": True},
        {"id": "d2", "category": "需求", "text": "验收标准是否明确（Given-When-Then）？", "required": True},
        {"id": "d3", "category": "需求", "text": "P0 功能是否控制在合理范围（建议 ≤5）？", "required": False},
        {"id": "d4", "category": "设计", "text": "是否考虑了响应式/多端适配？", "required": False},
        {"id": "d5", "category": "设计", "text": "异常状态和空状态是否有处理？", "required": False},
        {"id": "d6", "category": "技术", "text": "关键接口性能指标是否定义（如响应时间）？", "required": False},
        {"id": "d7", "category": "安全", "text": "用户输入是否经过校验和防注入处理？", "required": True},
        {"id": "d8", "category": "安全", "text": "敏感数据是否加密存储和传输？", "required": True},
        {"id": "d9", "category": "风险", "text": "是否识别了 Top 3 风险并给出应对？", "required": False},
        {"id": "d10", "category": "指标", "text": "是否定义了可量化的成功指标？", "required": False},
    ],
}


# ============== Request/Response Models ==============

class ChecklistItemState(BaseModel):
    item_id: str
    checked: bool
    note: Optional[str] = None


class ChecklistSubmit(BaseModel):
    items: List[ChecklistItemState]


# ============== Endpoints ==============

@rate_limit(requests=100, window=60)
@router.get("/projects/{project_id}/reviews/checklist", response_model=dict)
async def get_checklist(
    project_id: str,
    prd_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get review checklist for a project (based on industry)"""
    project = await require_project_owner(db, project_id, user_id)

    industry = (project.industry or "default").lower()
    items = CHECKLISTS.get(industry, CHECKLISTS["default"])

    return ResponseBuilder.success({
        "project_id": project_id,
        "industry": industry,
        "items": items,
    })


@rate_limit(requests=30, window=60)
@router.post("/projects/{project_id}/reviews/checklist", response_model=dict)
async def submit_checklist(
    project_id: str,
    data: ChecklistSubmit,
    prd_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Submit checklist review results"""
    project = await require_project_owner(db, project_id, user_id)

    industry = (project.industry or "default").lower()
    items = CHECKLISTS.get(industry, CHECKLISTS["default"])
    item_map = {item["id"]: item for item in items}

    checked_count = sum(1 for i in data.items if i.checked)
    required_items = [item for item in items if item["required"]]
    required_checked = sum(
        1 for i in data.items
        if i.checked and i.item_id in {r["id"] for r in required_items}
    )
    all_required_passed = required_checked >= len(required_items)

    # 持久化到 ReviewRecord（替代 project.settings 临时存储）
    now = datetime.now(timezone.utc)
    record = ReviewRecord(
        project_id=project_id,
        prd_id=prd_id,
        review_type=ReviewType.CHECKLIST,
        status=ReviewStatus.COMPLETED,
        industry=industry,
        total_items=len(items),
        checked_count=checked_count,
        required_items=len(required_items),
        required_checked=required_checked,
        all_required_passed=1 if all_required_passed else 0,
        items=[{"item_id": i.item_id, "checked": i.checked, "note": i.note} for i in data.items],
        submitted_by=user_id,
        submitted_at=now,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    result_payload = {
        "id": record.id,
        "project_id": project_id,
        "prd_id": prd_id,
        "industry": industry,
        "total_items": len(items),
        "checked_count": checked_count,
        "required_items": len(required_items),
        "required_checked": required_checked,
        "all_required_passed": all_required_passed,
        "items": record.items,
        "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
        "submitted_by": user_id,
    }

    return ResponseBuilder.success(result_payload)


# ============== Review History ==============


@rate_limit(requests=100, window=60)
@router.get("/projects/{project_id}/reviews/history", response_model=dict)
async def get_review_history(
    project_id: str,
    prd_id: Optional[str] = None,
    review_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """查询评审历史记录"""
    await require_project_owner(db, project_id, user_id)

    query = select(ReviewRecord).where(
        ReviewRecord.project_id == project_id,
    ).order_by(desc(ReviewRecord.submitted_at))

    if prd_id:
        query = query.where(ReviewRecord.prd_id == prd_id)
    if review_type:
        query = query.where(ReviewRecord.review_type == ReviewType(review_type))

    # Total count
    count_query = select(ReviewRecord).where(ReviewRecord.project_id == project_id)
    if prd_id:
        count_query = count_query.where(ReviewRecord.prd_id == prd_id)
    if review_type:
        count_query = count_query.where(ReviewRecord.review_type == ReviewType(review_type))
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return ResponseBuilder.paginated(
        data=[{
            "id": r.id,
            "project_id": r.project_id,
            "prd_id": r.prd_id,
            "review_type": r.review_type.value if r.review_type else None,
            "status": r.status.value if r.status else None,
            "industry": r.industry,
            "total_items": r.total_items,
            "checked_count": r.checked_count,
            "required_items": r.required_items,
            "required_checked": r.required_checked,
            "all_required_passed": bool(r.all_required_passed),
            "items": r.items,
            "score": r.score,
            "result_summary": r.result_summary,
            "submitted_by": r.submitted_by,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )