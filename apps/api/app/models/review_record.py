"""Review record model — 评审历史独立持久化

替代 project.settings 中的临时 JSON 存储，支持:
  - 检查清单评审 (checklist)
  - AI 合规评审 (compliance)
  - 任务完成后再评审 (re_review)
  - 历史查询与趋势分析
"""

import enum

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey, Enum

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ReviewType(str, enum.Enum):
    CHECKLIST = "checklist"       # 手动检查清单评审
    COMPLIANCE = "compliance"     # AI 合规自动评审
    RE_REVIEW = "re_review"       # 任务完成触发的再评审


class ReviewStatus(str, enum.Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    FAILED = "failed"


class ReviewRecord(Base, TimestampMixin):
    """评审记录 — 每次评审提交/再评审生成一条记录"""

    __tablename__ = "review_records"

    # ── 关联 ──
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    prd_id = Column(String, ForeignKey("prds.id"), nullable=True, index=True)
    revision_task_id = Column(String, ForeignKey("prd_revision_tasks.id"), nullable=True, index=True)

    # ── 评审元数据 ──
    review_type = Column(Enum(ReviewType), nullable=False, default=ReviewType.CHECKLIST)
    status = Column(Enum(ReviewStatus), nullable=False, default=ReviewStatus.COMPLETED)
    industry = Column(String, default="default")
    trigger_source = Column(String, default="manual")  # manual | task_complete | auto

    # ── 检查清单结果 ──
    total_items = Column(Integer, default=0)
    checked_count = Column(Integer, default=0)
    required_items = Column(Integer, default=0)
    required_checked = Column(Integer, default=0)
    all_required_passed = Column(Integer, default=0)  # 0/1

    # ── 详细数据 ──
    items = Column(JSON, default=list)         # [{"item_id": "m1", "checked": true, "note": "..."}]
    score = Column(Float, nullable=True)        # 合规评审的综合得分 (0-100)
    result_summary = Column(Text, nullable=True)  # AI 生成的评审结论/整改建议

    # ── 提交信息 ──
    submitted_by = Column(String, ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
