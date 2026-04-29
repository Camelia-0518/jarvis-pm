"""
A/B测试框架

支持Prompt策略、模型参数、功能特性的A/B测试
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid
import hashlib


class TestStatus(str, Enum):
    """测试状态"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Variant(BaseModel):
    """测试变体"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(description="变体名称")
    description: str = Field(default="", description="变体描述")

    # 变体配置
    prompt_template: Optional[str] = Field(default=None, description="Prompt模板")
    llm_params: Dict[str, Any] = Field(default_factory=dict, description="模型参数")
    feature_flags: Dict[str, bool] = Field(default_factory=dict, description="功能开关")

    # 统计数据
    impressions: int = Field(default=0, description="曝光次数")
    conversions: int = Field(default=0, description="转化次数")

    @property
    def conversion_rate(self) -> float:
        """转化率"""
        if self.impressions == 0:
            return 0.0
        return self.conversions / self.impressions * 100


class MetricDefinition(BaseModel):
    """指标定义"""
    name: str = Field(description="指标名称")
    description: str = Field(description="指标描述")
    metric_type: str = Field(default="rate", description="指标类型: rate/count/duration/score")
    is_primary: bool = Field(default=False, description="是否主要指标")
    target_value: Optional[float] = Field(default=None, description="目标值")


class ABTest(BaseModel):
    """A/B测试定义"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(description="测试名称")
    hypothesis: str = Field(description="测试假设")

    # 变体
    control: Variant = Field(description="对照组")
    treatment: Variant = Field(description="实验组")

    # 指标
    primary_metric: MetricDefinition = Field(description="主要指标")
    secondary_metrics: List[MetricDefinition] = Field(default_factory=list, description="次要指标")

    # 配置
    traffic_split: float = Field(default=0.5, description="流量分配比例(实验组)")
    min_sample_size: int = Field(default=100, description="最小样本量")
    duration_days: int = Field(default=14, description="测试持续时间(天)")

    # 状态
    status: TestStatus = Field(default=TestStatus.DRAFT)

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)

    def assign_variant(self, user_id: str) -> str:
        """
        为用户分配变体

        使用一致性哈希确保同一用户始终分配到同一变体
        """
        # 生成一致性哈希
        hash_input = f"{self.id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        # 根据流量分配决定变体
        if (hash_value % 100) < (self.traffic_split * 100):
            return "treatment"
        return "control"

    def record_event(self, user_id: str, event_type: str, value: Any = None):
        """记录测试事件"""
        variant_id = self.assign_variant(user_id)
        variant = self.treatment if variant_id == "treatment" else self.control

        if event_type == "impression":
            variant.impressions += 1
        elif event_type == "conversion":
            variant.conversions += 1

    def get_results(self) -> Dict[str, Any]:
        """获取测试结果"""
        control_rate = self.control.conversion_rate
        treatment_rate = self.treatment.conversion_rate

        # 计算提升率
        if control_rate > 0:
            lift = (treatment_rate - control_rate) / control_rate * 100
        else:
            lift = 0.0

        # 统计显著性（简化计算）
        is_significant = self._check_significance()

        return {
            "test_id": self.id,
            "status": self.status.value,
            "control": {
                "variant_id": self.control.id,
                "impressions": self.control.impressions,
                "conversions": self.control.conversions,
                "conversion_rate": round(control_rate, 2),
            },
            "treatment": {
                "variant_id": self.treatment.id,
                "impressions": self.treatment.impressions,
                "conversions": self.treatment.conversions,
                "conversion_rate": round(treatment_rate, 2),
            },
            "lift": round(lift, 2),
            "is_statistically_significant": is_significant,
            "recommendation": self._get_recommendation(lift, is_significant),
        }

    def _check_significance(self) -> bool:
        """检查统计显著性（简化版）"""
        # 需要足够的样本量
        if self.control.impressions < self.min_sample_size or \
           self.treatment.impressions < self.min_sample_size:
            return False

        # 简化的显著性判断：差异超过5%且样本量足够
        diff = abs(self.control.conversion_rate - self.treatment.conversion_rate)
        return diff > 5.0

    def _get_recommendation(self, lift: float, is_significant: bool) -> str:
        """获取建议"""
        if not is_significant:
            return "需要更多数据或测试时间"

        if lift > 10:
            return f"实验组表现显著优于对照组（+{lift:.1f}%），建议全量发布"
        elif lift > 5:
            return f"实验组表现较好（+{lift:.1f}%），建议扩大流量测试"
        elif lift > -5:
            return "两组表现相近，可继续观察或终止测试"
        else:
            return f"实验组表现较差（{lift:.1f}%），建议保留对照组"


class PromptABTestFactory:
    """Prompt A/B测试工厂"""

    @staticmethod
    def create_prompt_test(
        name: str,
        hypothesis: str,
        control_prompt: str,
        treatment_prompt: str,
        metric_name: str = "prd_quality_score"
    ) -> ABTest:
        """创建Prompt A/B测试"""

        control = Variant(
            name="Control",
            description="当前Prompt版本",
            prompt_template=control_prompt,
        )

        treatment = Variant(
            name="Treatment",
            description="优化后的Prompt版本",
            prompt_template=treatment_prompt,
        )

        primary_metric = MetricDefinition(
            name=metric_name,
            description="PRD生成质量评分",
            metric_type="score",
            is_primary=True,
            target_value=80.0,
        )

        return ABTest(
            name=name,
            hypothesis=hypothesis,
            control=control,
            treatment=treatment,
            primary_metric=primary_metric,
        )


class ABTestFramework:
    """A/B测试框架主类"""

    def __init__(self):
        self.tests: Dict[str, ABTest] = {}

    def create_test(self, test: ABTest) -> str:
        """创建测试"""
        self.tests[test.id] = test
        return test.id

    def start_test(self, test_id: str):
        """启动测试"""
        if test_id not in self.tests:
            raise ValueError(f"测试不存在: {test_id}")

        test = self.tests[test_id]
        test.status = TestStatus.RUNNING
        test.started_at = datetime.now()

    def get_test(self, test_id: str) -> Optional[ABTest]:
        """获取测试"""
        return self.tests.get(test_id)

    def list_tests(self, status: Optional[TestStatus] = None) -> List[ABTest]:
        """列出测试"""
        tests = list(self.tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        return tests

    def record_event(self, test_id: str, user_id: str, event_type: str, value: Any = None):
        """记录事件"""
        test = self.get_test(test_id)
        if test and test.status == TestStatus.RUNNING:
            test.record_event(user_id, event_type, value)

    def get_results(self, test_id: str) -> Dict[str, Any]:
        """获取测试结果"""
        test = self.get_test(test_id)
        if not test:
            return {"error": "测试不存在"}
        return test.get_results()

    def complete_test(self, test_id: str):
        """完成测试"""
        if test_id not in self.tests:
            raise ValueError(f"测试不存在: {test_id}")

        test = self.tests[test_id]
        test.status = TestStatus.COMPLETED
        test.ended_at = datetime.now()

        return test.get_results()


# 常用测试模板
class TestTemplates:
    """A/B测试模板"""

    @staticmethod
    def prd_prompt_enhancement() -> ABTest:
        """PRD Prompt增强测试"""
        control_prompt = """你是一个产品经理，请根据需求生成PRD文档。"""

        treatment_prompt = """你是一位资深医疗信息化产品经理，拥有10年行业经验。

请根据以下需求生成完整的PRD文档，要求：
1. 包含业务背景和用户画像
2. 编写清晰的用户故事（格式：作为[角色]，我想要[功能]，以便[价值]）
3. 定义明确的验收标准（格式：Given-When-Then）
4. 补充合规要求（等保三级、患者隐私保护）
5. 考虑多院区政策差异（江西/临夏/浙江）

请按以下结构输出：
- 文档信息
- 业务背景
- 用户角色
- 核心流程
- 功能模块
- 合规要求
- 验收标准
"""

        return PromptABTestFactory.create_prompt_test(
            name="PRD Prompt优化测试",
            hypothesis="详细的Prompt模板可以提升PRD生成质量20%以上",
            control_prompt=control_prompt,
            treatment_prompt=treatment_prompt,
            metric_name="prd_overall_score",
        )

    @staticmethod
    def user_story_format() -> ABTest:
        """用户故事格式测试"""
        control = Variant(
            name="Simple Format",
            description="简单格式：用户需要XX功能",
        )

        treatment = Variant(
            name="Structured Format",
            description="结构格式：作为[角色]，我想要[功能]，以便[价值]",
        )

        primary_metric = MetricDefinition(
            name="user_story_clarity",
            description="用户故事清晰度评分",
            metric_type="score",
            is_primary=True,
            target_value=85.0,
        )

        return ABTest(
            name="用户故事格式测试",
            hypothesis="结构化用户故事格式能提升开发理解度",
            control=control,
            treatment=treatment,
            primary_metric=primary_metric,
        )
