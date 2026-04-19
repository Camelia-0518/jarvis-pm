"""
用户反馈收集器

建立PRD生成的用户反馈闭环，支持评分、文本反馈、改进追踪
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class FeedbackRating(BaseModel):
    """反馈评分"""
    overall: int = Field(ge=1, le=5, description="整体满意度 1-5")
    accuracy: int = Field(ge=1, le=5, description="准确度 1-5")
    usefulness: int = Field(ge=1, le=5, description="有用性 1-5")


class FeedbackType(str, Enum):
    """反馈类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    SUGGESTION = "suggestion"
    BUG = "bug"


class UserFeedback(BaseModel):
    """用户反馈"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])

    # 关联信息
    prd_id: str = Field(description="PRD标识")
    user_id: str = Field(description="用户标识")

    # 评分
    ratings: FeedbackRating = Field(description="评分")

    # 详细反馈
    feedback_type: FeedbackType = Field(default=FeedbackType.SUGGESTION)
    what_worked: str = Field(default="", description="哪些部分好用")
    what_failed: str = Field(default="", description="哪些部分不对")
    suggestions: str = Field(default="", description="改进建议")

    # 技术元数据
    generated_by: str = Field(default="", description="生成使用的模型版本")
    prompt_version: str = Field(default="", description="Prompt版本")
    generation_time: Optional[float] = Field(default=None, description="生成耗时(秒)")

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)


class FeedbackStatistics(BaseModel):
    """反馈统计"""
    total_count: int = Field(default=0, description="总反馈数")
    avg_overall_rating: float = Field(default=0.0, description="平均整体评分")
    avg_accuracy_rating: float = Field(default=0.0, description="平均准确度评分")
    avg_usefulness_rating: float = Field(default=0.0, description="平均有用性评分")

    # 分布
    rating_distribution: Dict[int, int] = Field(default_factory=dict, description="评分分布")
    type_distribution: Dict[str, int] = Field(default_factory=dict, description="类型分布")

    # 趋势
    recent_trend: str = Field(default="stable", description="近期趋势: improving/stable/declining")


class ImprovementTracker(BaseModel):
    """改进追踪器"""
    issue_id: str = Field(description="问题ID")
    description: str = Field(description="问题描述")
    category: str = Field(description="问题类别")

    # 状态
    status: str = Field(default="open", description="状态: open/in_progress/resolved")
    priority: str = Field(default="medium", description="优先级: high/medium/low")

    # 关联
    related_feedbacks: List[str] = Field(default_factory=list, description="关联反馈ID")

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = Field(default=None)

    # 解决方案
    solution: str = Field(default="", description="解决方案")
    resolved_by: str = Field(default="", description="解决人")


class FeedbackCollector:
    """反馈收集器"""

    def __init__(self):
        self.feedbacks: Dict[str, UserFeedback] = {}
        self.statistics_cache: Optional[FeedbackStatistics] = None
        self.improvement_trackers: Dict[str, ImprovementTracker] = {}

    def collect(self, feedback: UserFeedback) -> str:
        """
        收集用户反馈

        Returns:
            反馈ID
        """
        self.feedbacks[feedback.id] = feedback
        self.statistics_cache = None  # 清除缓存

        # 自动分析问题
        self._auto_analyze_issue(feedback)

        return feedback.id

    def get_feedback(self, feedback_id: str) -> Optional[UserFeedback]:
        """获取反馈"""
        return self.feedbacks.get(feedback_id)

    def get_feedbacks_by_prd(self, prd_id: str) -> List[UserFeedback]:
        """获取PRD相关的所有反馈"""
        return [f for f in self.feedbacks.values() if f.prd_id == prd_id]

    def get_statistics(self) -> FeedbackStatistics:
        """获取反馈统计"""
        if self.statistics_cache:
            return self.statistics_cache

        if not self.feedbacks:
            return FeedbackStatistics()

        stats = FeedbackStatistics()
        stats.total_count = len(self.feedbacks)

        ratings = [f.ratings for f in self.feedbacks.values()]
        stats.avg_overall_rating = sum(r.overall for r in ratings) / len(ratings)
        stats.avg_accuracy_rating = sum(r.accuracy for r in ratings) / len(ratings)
        stats.avg_usefulness_rating = sum(r.usefulness for r in ratings) / len(ratings)

        # 评分分布
        for r in ratings:
            stats.rating_distribution[r.overall] = stats.rating_distribution.get(r.overall, 0) + 1

        # 类型分布
        for f in self.feedbacks.values():
            stats.type_distribution[f.feedback_type.value] = stats.type_distribution.get(f.feedback_type.value, 0) + 1

        # 趋势判断（简化版）
        recent_feedbacks = sorted(
            self.feedbacks.values(),
            key=lambda x: x.created_at,
            reverse=True
        )[:20]

        if recent_feedbacks:
            recent_avg = sum(f.ratings.overall for f in recent_feedbacks) / len(recent_feedbacks)
            if recent_avg > stats.avg_overall_rating + 0.3:
                stats.recent_trend = "improving"
            elif recent_avg < stats.avg_overall_rating - 0.3:
                stats.recent_trend = "declining"
            else:
                stats.recent_trend = "stable"

        self.statistics_cache = stats
        return stats

    def _auto_analyze_issue(self, feedback: UserFeedback):
        """自动分析问题并创建改进追踪"""
        # 低评分自动创建问题
        if feedback.ratings.overall <= 2:
            issue = ImprovementTracker(
                issue_id=str(uuid.uuid4())[:8],
                description=feedback.what_failed or "用户反馈满意度低",
                category="quality_issue",
                priority="high",
                related_feedbacks=[feedback.id],
            )
            self.improvement_trackers[issue.issue_id] = issue

        # 特定问题关键词检测
        keywords_map = {
            "合规": "compliance_issue",
            "隐私": "privacy_issue",
            "安全": "security_issue",
            "医疗": "medical_accuracy",
            "病案": "medical_domain",
            "his": "medical_integration",
        }

        content = f"{feedback.what_failed} {feedback.suggestions}".lower()
        for keyword, category in keywords_map.items():
            if keyword in content:
                existing = self._find_similar_issue(category, feedback.what_failed)
                if existing:
                    existing.related_feedbacks.append(feedback.id)
                else:
                    issue = ImprovementTracker(
                        issue_id=str(uuid.uuid4())[:8],
                        description=feedback.what_failed or f"涉及{keyword}的问题",
                        category=category,
                        priority="medium",
                        related_feedbacks=[feedback.id],
                    )
                    self.improvement_trackers[issue.issue_id] = issue

    def _find_similar_issue(self, category: str, description: str) -> Optional[ImprovementTracker]:
        """查找相似问题（简化版）"""
        for issue in self.improvement_trackers.values():
            if issue.category == category and issue.status != "resolved":
                return issue
        return None

    def get_improvement_trackers(self, status: Optional[str] = None) -> List[ImprovementTracker]:
        """获取改进追踪列表"""
        trackers = list(self.improvement_trackers.values())
        if status:
            trackers = [t for t in trackers if t.status == status]
        return sorted(trackers, key=lambda x: x.created_at, reverse=True)

    def resolve_issue(self, issue_id: str, solution: str, resolved_by: str) -> bool:
        """解决问题"""
        if issue_id not in self.improvement_trackers:
            return False

        issue = self.improvement_trackers[issue_id]
        issue.status = "resolved"
        issue.resolved_at = datetime.now()
        issue.solution = solution
        issue.resolved_by = resolved_by

        return True

    def get_insights(self) -> Dict[str, Any]:
        """获取洞察分析"""
        stats = self.get_statistics()

        # 高频问题
        open_issues = [i for i in self.improvement_trackers.values() if i.status != "resolved"]
        category_counts = {}
        for issue in open_issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        top_issues = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "overall_satisfaction": f"{stats.avg_overall_rating:.1f}/5.0",
            "total_feedbacks": stats.total_count,
            "trend": stats.recent_trend,
            "top_issues": [
                {"category": cat, "count": count}
                for cat, count in top_issues
            ],
            "recommendations": self._generate_recommendations(stats, open_issues),
        }

    def _generate_recommendations(self, stats: FeedbackStatistics, open_issues: List[ImprovementTracker]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if stats.avg_overall_rating < 3.5:
            recommendations.append("整体满意度偏低，建议暂停新功能开发，优先解决质量问题")

        if stats.avg_accuracy_rating < 3.5:
            recommendations.append("准确度评分较低，建议优化需求理解Prompt和医疗术语库")

        category_map = {
            "compliance_issue": "合规相关问题较多，建议加强合规检查Agent",
            "medical_accuracy": "医疗准确性问题突出，建议增强医疗术语处理",
            "quality_issue": "质量问题反馈较多，建议优化生成质量",
        }

        for issue in open_issues[:3]:
            if issue.category in category_map:
                recommendations.append(category_map[issue.category])

        return recommendations[:5]
