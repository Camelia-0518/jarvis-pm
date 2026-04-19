"""
Jarvis PM 评测系统 - AI产品经理核心能力

提供PRD生成质量评测、A/B测试、用户反馈闭环等能力
"""

from .metrics.prd_quality import PRDQualityEvaluator
from .ab_testing.framework import ABTestFramework
from .feedback.collector import FeedbackCollector

__all__ = [
    "PRDQualityEvaluator",
    "ABTestFramework",
    "FeedbackCollector",
]
