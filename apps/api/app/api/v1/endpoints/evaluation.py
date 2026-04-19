"""
评测系统 API 路由

提供PRD质量评测、A/B测试、用户反馈等功能
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from app.evaluation.metrics.prd_quality import PRDQualityEvaluator, PRDQualityScore
from app.evaluation.ab_testing.framework import (
    ABTestFramework, ABTest, TestTemplates, PromptABTestFactory, Variant
)
from app.evaluation.feedback.collector import (
    FeedbackCollector, UserFeedback, FeedbackRating, FeedbackType
)

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

# 全局实例
evaluator = PRDQualityEvaluator()
ab_framework = ABTestFramework()
feedback_collector = FeedbackCollector()


# ============ PRD 质量评测 ============

class EvaluatePRDRequest(BaseModel):
    """PRD评测请求"""
    prd_content: str = Field(description="PRD文档内容")
    prd_id: str = Field(default="", description="PRD标识")


class EvaluatePRDResponse(BaseModel):
    """PRD评测响应"""
    prd_id: str
    overall_score: float
    grade: str
    completeness_score: float
    accuracy_score: float
    usability_score: float
    compliance_score: float
    suggestions: List[str]


@router.post("/evaluate-prd", response_model=EvaluatePRDResponse)
async def evaluate_prd(request: EvaluatePRDRequest):
    """
    评测PRD质量

    返回完整性、准确性、可用性、合规性四个维度的评分和改进建议
    """
    if not request.prd_content or len(request.prd_content.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PRD内容太短，请提供完整的PRD文档"
        )

    try:
        score = evaluator.evaluate(request.prd_content, request.prd_id)

        return EvaluatePRDResponse(
            prd_id=score.prd_id,
            overall_score=round(score.overall_score, 1),
            grade=score.grade,
            completeness_score=round(score.completeness.score, 1),
            accuracy_score=round(score.accuracy.score, 1),
            usability_score=round(score.usability.score, 1),
            compliance_score=round(score.compliance.score, 1),
            suggestions=score.get_improvement_suggestions(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"评测失败: {str(e)}"
        )


# ============ A/B 测试 ============

class CreateABTestRequest(BaseModel):
    """创建A/B测试请求"""
    name: str = Field(description="测试名称")
    hypothesis: str = Field(description="测试假设")
    control_prompt: str = Field(description="对照组Prompt")
    treatment_prompt: str = Field(description="实验组Prompt")
    traffic_split: float = Field(default=0.5, ge=0.1, le=0.9, description="流量分配")


class ABTestResponse(BaseModel):
    """A/B测试响应"""
    test_id: str
    name: str
    status: str
    control_variant_id: str
    treatment_variant_id: str


@router.post("/ab-tests", response_model=ABTestResponse)
async def create_ab_test(request: CreateABTestRequest):
    """创建A/B测试"""
    try:
        test = PromptABTestFactory.create_prompt_test(
            name=request.name,
            hypothesis=request.hypothesis,
            control_prompt=request.control_prompt,
            treatment_prompt=request.treatment_prompt,
        )
        test.traffic_split = request.traffic_split

        test_id = ab_framework.create_test(test)

        return ABTestResponse(
            test_id=test_id,
            name=test.name,
            status=test.status.value,
            control_variant_id=test.control.id,
            treatment_variant_id=test.treatment.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建测试失败: {str(e)}"
        )


@router.post("/ab-tests/{test_id}/start")
async def start_ab_test(test_id: str):
    """启动A/B测试"""
    try:
        ab_framework.start_test(test_id)
        return {"message": "测试已启动", "test_id": test_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/ab-tests/{test_id}/results")
async def get_ab_test_results(test_id: str):
    """获取A/B测试结果"""
    results = ab_framework.get_results(test_id)
    if "error" in results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=results["error"]
        )
    return results


@router.get("/ab-tests")
async def list_ab_tests(status: Optional[str] = None):
    """列出A/B测试"""
    from app.evaluation.ab_testing.framework import TestStatus

    filter_status = None
    if status:
        try:
            filter_status = TestStatus(status)
        except ValueError:
            pass

    tests = ab_framework.list_tests(filter_status)
    return [
        {
            "test_id": t.id,
            "name": t.name,
            "status": t.status.value,
            "hypothesis": t.hypothesis,
            "created_at": t.created_at.isoformat(),
        }
        for t in tests
    ]


# ============ 用户反馈 ============

class SubmitFeedbackRequest(BaseModel):
    """提交反馈请求"""
    prd_id: str = Field(description="PRD标识")
    user_id: str = Field(description="用户标识")
    overall_rating: int = Field(ge=1, le=5, description="整体评分")
    accuracy_rating: int = Field(ge=1, le=5, description="准确度评分")
    usefulness_rating: int = Field(ge=1, le=5, description="有用性评分")
    what_worked: str = Field(default="", description="哪些部分好用")
    what_failed: str = Field(default="", description="哪些部分不对")
    suggestions: str = Field(default="", description="改进建议")
    feedback_type: str = Field(default="suggestion", description="反馈类型")


@router.post("/feedback")
async def submit_feedback(request: SubmitFeedbackRequest):
    """提交用户反馈"""
    try:
        feedback = UserFeedback(
            prd_id=request.prd_id,
            user_id=request.user_id,
            ratings=FeedbackRating(
                overall=request.overall_rating,
                accuracy=request.accuracy_rating,
                usefulness=request.usefulness_rating,
            ),
            what_worked=request.what_worked,
            what_failed=request.what_failed,
            suggestions=request.suggestions,
            feedback_type=FeedbackType(request.feedback_type),
        )

        feedback_id = feedback_collector.collect(feedback)

        return {
            "feedback_id": feedback_id,
            "message": "反馈已提交，感谢你的建议！",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交反馈失败: {str(e)}"
        )


@router.get("/feedback/statistics")
async def get_feedback_statistics():
    """获取反馈统计"""
    stats = feedback_collector.get_statistics()
    return {
        "total_feedbacks": stats.total_count,
        "avg_overall_rating": round(stats.avg_overall_rating, 1),
        "avg_accuracy_rating": round(stats.avg_accuracy_rating, 1),
        "avg_usefulness_rating": round(stats.avg_usefulness_rating, 1),
        "rating_distribution": stats.rating_distribution,
        "recent_trend": stats.recent_trend,
    }


@router.get("/feedback/insights")
async def get_feedback_insights():
    """获取反馈洞察"""
    return feedback_collector.get_insights()


# ============ 预置模板 ============

@router.get("/templates/ab-tests")
async def get_ab_test_templates():
    """获取A/B测试模板"""
    return [
        {
            "name": "PRD Prompt优化测试",
            "description": "测试优化后的Prompt模板是否能提升PRD生成质量",
            "template_id": "prd_prompt_enhancement",
        },
        {
            "name": "用户故事格式测试",
            "description": "测试结构化用户故事格式的效果",
            "template_id": "user_story_format",
        },
    ]


@router.post("/templates/ab-tests/{template_id}/create")
async def create_from_template(template_id: str):
    """从模板创建A/B测试"""
    try:
        if template_id == "prd_prompt_enhancement":
            test = TestTemplates.prd_prompt_enhancement()
        elif template_id == "user_story_format":
            test = TestTemplates.user_story_format()
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在"
            )

        test_id = ab_framework.create_test(test)

        return {
            "test_id": test_id,
            "name": test.name,
            "message": "测试已从模板创建",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建测试失败: {str(e)}"
        )
