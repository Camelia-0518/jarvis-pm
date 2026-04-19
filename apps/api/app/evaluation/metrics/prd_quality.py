"""
PRD质量评测系统

评估PRD生成的完整度、准确性、可用性、合规性
支持 LLM-as-Judge 和规则启发式 fallback
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import re
import json
import logging

from app.agents.llm_client import create_default_client, LLMClient

logger = logging.getLogger(__name__)


class CompletenessMetrics(BaseModel):
    """完整性指标"""
    has_background: bool = Field(default=False, description="是否有背景说明")
    has_user_stories: bool = Field(default=False, description="是否有用户故事")
    has_acceptance_criteria: bool = Field(default=False, description="是否有验收标准")
    has_success_metrics: bool = Field(default=False, description="是否有成功指标")
    has_compliance_section: bool = Field(default=False, description="是否有合规章节")
    has_multi_hospital_section: bool = Field(default=False, description="是否有多院区章节")
    score: float = Field(default=0.0, description="完整性得分 0-100")

    def calculate_score(self) -> float:
        """计算完整性得分"""
        weights = {
            "has_background": 15,
            "has_user_stories": 25,
            "has_acceptance_criteria": 20,
            "has_success_metrics": 15,
            "has_compliance_section": 15,
            "has_multi_hospital_section": 10,
        }

        total = 0
        if self.has_background:
            total += weights["has_background"]
        if self.has_user_stories:
            total += weights["has_user_stories"]
        if self.has_acceptance_criteria:
            total += weights["has_acceptance_criteria"]
        if self.has_success_metrics:
            total += weights["has_success_metrics"]
        if self.has_compliance_section:
            total += weights["has_compliance_section"]
        if self.has_multi_hospital_section:
            total += weights["has_multi_hospital_section"]

        self.score = total
        return total


class AccuracyMetrics(BaseModel):
    """准确性指标"""
    requirement_understanding: float = Field(default=0.0, description="需求理解准确度 0-100")
    logic_consistency: float = Field(default=0.0, description="逻辑一致性 0-100")
    industry_terminology: float = Field(default=0.0, description="行业术语准确性 0-100")
    medical_accuracy: float = Field(default=0.0, description="医疗术语准确性 0-100")
    score: float = Field(default=0.0, description="准确性得分 0-100")

    def calculate_score(self) -> float:
        """计算准确性得分"""
        weights = {
            "requirement_understanding": 30,
            "logic_consistency": 25,
            "industry_terminology": 25,
            "medical_accuracy": 20,
        }

        self.score = (
            self.requirement_understanding * weights["requirement_understanding"] / 100 +
            self.logic_consistency * weights["logic_consistency"] / 100 +
            self.industry_terminology * weights["industry_terminology"] / 100 +
            self.medical_accuracy * weights["medical_accuracy"] / 100
        )
        return self.score


class UsabilityMetrics(BaseModel):
    """可用性指标"""
    clarity: float = Field(default=0.0, description="清晰度 0-100")
    actionability: float = Field(default=0.0, description="可执行性 0-100")
    developer_friendly: float = Field(default=0.0, description="开发友好度 0-100")
    score: float = Field(default=0.0, description="可用性得分 0-100")

    def calculate_score(self) -> float:
        """计算可用性得分"""
        weights = {
            "clarity": 35,
            "actionability": 35,
            "developer_friendly": 30,
        }

        self.score = (
            self.clarity * weights["clarity"] / 100 +
            self.actionability * weights["actionability"] / 100 +
            self.developer_friendly * weights["developer_friendly"] / 100
        )
        return self.score


class ComplianceMetrics(BaseModel):
    """合规性指标（医疗行业专用）"""
    privacy_protection: bool = Field(default=False, description="隐私保护")
    data_security: bool = Field(default=False, description="数据安全")
    medical_regulations: bool = Field(default=False, description="医疗规范")
    audit_trail: bool = Field(default=False, description="审计追溯")
    score: float = Field(default=0.0, description="合规性得分 0-100")

    def calculate_score(self) -> float:
        """计算合规性得分"""
        weights = {
            "privacy_protection": 30,
            "data_security": 25,
            "medical_regulations": 30,
            "audit_trail": 15,
        }

        total = 0
        if self.privacy_protection:
            total += weights["privacy_protection"]
        if self.data_security:
            total += weights["data_security"]
        if self.medical_regulations:
            total += weights["medical_regulations"]
        if self.audit_trail:
            total += weights["audit_trail"]

        self.score = total
        return total


class PRDQualityScore(BaseModel):
    """PRD质量总评分"""
    prd_id: str = Field(description="PRD标识")
    version: str = Field(default="1.0", description="版本")

    # 各维度评分
    completeness: CompletenessMetrics = Field(default_factory=CompletenessMetrics)
    accuracy: AccuracyMetrics = Field(default_factory=AccuracyMetrics)
    usability: UsabilityMetrics = Field(default_factory=UsabilityMetrics)
    compliance: ComplianceMetrics = Field(default_factory=ComplianceMetrics)

    # 总评分
    overall_score: float = Field(default=0.0, description="总体得分 0-100")
    grade: str = Field(default="F", description="等级 A/B/C/D/F")

    # LLM 评测元数据
    used_llm: bool = Field(default=False, description="是否使用了 LLM 评测")
    llm_reasoning: Optional[str] = Field(default=None, description="LLM 评分 reasoning")

    # 元数据
    evaluated_at: datetime = Field(default_factory=datetime.now)
    evaluator_version: str = Field(default="1.0")

    def calculate_overall_score(self) -> float:
        """计算总体得分"""
        weights = {
            "completeness": 30,
            "accuracy": 25,
            "usability": 25,
            "compliance": 20,
        }

        # 确保各维度分数已计算
        self.completeness.calculate_score()
        self.accuracy.calculate_score()
        self.usability.calculate_score()
        self.compliance.calculate_score()

        self.overall_score = (
            self.completeness.score * weights["completeness"] / 100 +
            self.accuracy.score * weights["accuracy"] / 100 +
            self.usability.score * weights["usability"] / 100 +
            self.compliance.score * weights["compliance"] / 100
        )

        # 计算等级
        if self.overall_score >= 90:
            self.grade = "A"
        elif self.overall_score >= 80:
            self.grade = "B"
        elif self.overall_score >= 70:
            self.grade = "C"
        elif self.overall_score >= 60:
            self.grade = "D"
        else:
            self.grade = "F"

        return self.overall_score

    def get_improvement_suggestions(self) -> List[str]:
        """获取改进建议"""
        suggestions = []

        # 完整性建议
        if not self.completeness.has_user_stories:
            suggestions.append("❌ 缺失用户故事：建议补充用户故事，格式：作为[角色]，我想要[功能]，以便[价值]")
        if not self.completeness.has_acceptance_criteria:
            suggestions.append("❌ 缺失验收标准：建议补充Given-When-Then格式的验收条件")
        if not self.completeness.has_compliance_section:
            suggestions.append("🔒 缺失合规章节：医疗项目必须包含等保三级、隐私保护合规要求")

        # 准确性建议
        if self.accuracy.requirement_understanding < 70:
            suggestions.append("⚠️ 需求理解欠佳：建议重新澄清核心需求，避免理解偏差")
        if self.accuracy.medical_accuracy < 80:
            suggestions.append("🏥 医疗术语需优化：建议检查HIS/LIS/PACS等专业术语使用")

        # 可用性建议
        if self.usability.developer_friendly < 70:
            suggestions.append("💻 开发友好度不足：建议增加数据模型、接口定义等技术细节")

        # 合规性建议
        if not self.compliance.privacy_protection:
            suggestions.append("🔐 缺少隐私保护说明：必须说明患者数据如何脱敏和加密")
        if not self.compliance.audit_trail:
            suggestions.append("📝 缺少审计追溯设计：医疗系统需要完整的操作日志")

        return suggestions


LLM_EVALUATION_PROMPT = """你是一位资深的产品经理评审专家。请对以下产品需求文档（PRD）进行专业评审，从4个维度给出0-100的整数评分，并给出简要理由。

评分维度：
1. completeness（完整性）：是否包含背景、用户故事、验收标准、成功指标、合规要求、多院区适配等
2. accuracy（准确性）：需求理解是否准确、逻辑是否一致、行业术语（特别是医疗术语）是否准确
3. usability（可用性）：文档是否清晰、是否可执行、对开发团队是否友好
4. compliance（合规性）：医疗行业的隐私保护、数据安全、等保合规、审计追溯是否到位

请严格按以下JSON格式输出，不要添加任何额外说明：

{{
  "completeness": 75,
  "accuracy": 80,
  "usability": 70,
  "compliance": 65,
  "reasoning": "简要说明评分的核心依据，100字以内"
}}

以下是需要评审的PRD内容：

---
{content}
---
"""


class LLMQualityEvaluator:
    """LLM-as-Judge PRD 质量评测器"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or create_default_client()
        self.evaluator_version = "2.0.0"

    async def evaluate(self, prd_content: str, prd_id: str = "", use_llm: bool = True) -> PRDQualityScore:
        """
        评测PRD质量，优先使用 LLM，失败时自动 fallback 到规则评测器
        """
        if use_llm:
            try:
                return await self._evaluate_with_llm(prd_content, prd_id)
            except Exception as e:
                logger.warning("LLM evaluation failed: %s. Falling back to heuristic evaluator.", e)

        # Fallback to heuristic
        heuristic = PRDQualityEvaluator()
        score = heuristic.evaluate(prd_content, prd_id)
        score.evaluator_version = self.evaluator_version
        return score

    async def _evaluate_with_llm(self, prd_content: str, prd_id: str) -> PRDQualityScore:
        """调用 LLM 进行评分"""
        prompt = LLM_EVALUATION_PROMPT.format(content=prd_content[:12000])  # 限制长度避免超限

        response_text = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": "你是一位资深产品经理评审专家，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        parsed = self._parse_llm_json(response_text)

        score = PRDQualityScore(prd_id=prd_id)
        score.used_llm = True
        score.llm_reasoning = parsed.get("reasoning", "")
        score.evaluator_version = self.evaluator_version

        # Completeness
        completeness_score = float(parsed.get("completeness", 0))
        score.completeness.score = completeness_score
        score.completeness.has_background = completeness_score >= 50
        score.completeness.has_user_stories = completeness_score >= 60
        score.completeness.has_acceptance_criteria = completeness_score >= 60
        score.completeness.has_success_metrics = completeness_score >= 50
        score.completeness.has_compliance_section = completeness_score >= 60
        score.completeness.has_multi_hospital_section = completeness_score >= 50

        # Accuracy
        accuracy_score = float(parsed.get("accuracy", 0))
        score.accuracy.score = accuracy_score
        score.accuracy.requirement_understanding = accuracy_score
        score.accuracy.logic_consistency = accuracy_score
        score.accuracy.industry_terminology = accuracy_score
        score.accuracy.medical_accuracy = accuracy_score

        # Usability
        usability_score = float(parsed.get("usability", 0))
        score.usability.score = usability_score
        score.usability.clarity = usability_score
        score.usability.actionability = usability_score
        score.usability.developer_friendly = usability_score

        # Compliance
        compliance_score = float(parsed.get("compliance", 0))
        score.compliance.score = compliance_score
        score.compliance.privacy_protection = compliance_score >= 60
        score.compliance.data_security = compliance_score >= 60
        score.compliance.medical_regulations = compliance_score >= 60
        score.compliance.audit_trail = compliance_score >= 50

        # 计算总体得分（直接使用 LLM 子维度分数，避免 calculate_overall_score 覆盖）
        score.overall_score = (
            score.completeness.score * 30 / 100 +
            score.accuracy.score * 25 / 100 +
            score.usability.score * 25 / 100 +
            score.compliance.score * 20 / 100
        )

        if score.overall_score >= 90:
            score.grade = "A"
        elif score.overall_score >= 80:
            score.grade = "B"
        elif score.overall_score >= 70:
            score.grade = "C"
        elif score.overall_score >= 60:
            score.grade = "D"
        else:
            score.grade = "F"

        return score

    @staticmethod
    def _parse_llm_json(text: str) -> Dict[str, Any]:
        """ robustly parse JSON from LLM response, stripping markdown fences """
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            # drop first fence line (may include ```json)
            lines = lines[1:]
            # drop last fence line
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)
        return json.loads(text.strip())


class PRDQualityEvaluator:
    """规则启发式 PRD 质量评测器（作为 LLM 的 fallback）"""

    def __init__(self):
        self.evaluator_version = "1.0.0"

    def evaluate(self, prd_content: str, prd_id: str = "") -> PRDQualityScore:
        """
        评测PRD质量

        Args:
            prd_content: PRD文档内容
            prd_id: PRD标识

        Returns:
            PRD质量评分
        """
        score = PRDQualityScore(prd_id=prd_id)

        # 评测完整性
        score.completeness = self._evaluate_completeness(prd_content)

        # 评测准确性
        score.accuracy = self._evaluate_accuracy(prd_content)

        # 评测可用性
        score.usability = self._evaluate_usability(prd_content)

        # 评测合规性
        score.compliance = self._evaluate_compliance(prd_content)

        # 计算总评分
        score.calculate_overall_score()

        return score

    def _evaluate_completeness(self, content: str) -> CompletenessMetrics:
        """评测完整性"""
        metrics = CompletenessMetrics()
        content_lower = content.lower()

        # 检查背景说明
        metrics.has_background = any(
            keyword in content_lower
            for keyword in ["背景", "background", "业务背景", "现状"]
        )

        # 检查用户故事
        metrics.has_user_stories = any(
            keyword in content_lower
            for keyword in ["用户故事", "user story", "作为", "我想要"]
        )

        # 检查验收标准
        metrics.has_acceptance_criteria = any(
            keyword in content_lower
            for keyword in ["验收标准", "acceptance criteria", "given", "when", "then"]
        )

        # 检查成功指标
        metrics.has_success_metrics = any(
            keyword in content_lower
            for keyword in ["成功指标", "指标", "metrics", "kpi"]
        )

        # 检查合规章节
        metrics.has_compliance_section = any(
            keyword in content_lower
            for keyword in ["合规", "等保", "隐私", "compliance", "安全"]
        )

        # 检查多院区章节
        metrics.has_multi_hospital_section = any(
            keyword in content_lower
            for keyword in ["多院区", "江西", "临夏", "分院", "院区适配"]
        )

        metrics.calculate_score()
        return metrics

    def _evaluate_accuracy(self, content: str) -> AccuracyMetrics:
        """评测准确性（基于规则启发式）"""
        metrics = AccuracyMetrics()
        content_lower = content.lower()

        # 需求理解准确度：检查是否有明确的问题定义
        if any(kw in content_lower for kw in ["问题", "痛点", "需求"]) and \
           any(kw in content_lower for kw in ["解决方案", "功能", "实现"]):
            metrics.requirement_understanding = 75
        else:
            metrics.requirement_understanding = 50

        # 逻辑一致性：检查流程完整性
        if "流程" in content or "flow" in content_lower:
            metrics.logic_consistency = 80
        else:
            metrics.logic_consistency = 60

        # 行业术语准确性
        medical_terms = ["his", "lis", "pacs", "emr", "电子病历", "医嘱", "处方"]
        found_terms = sum(1 for term in medical_terms if term in content_lower)
        metrics.industry_terminology = min(100, 50 + found_terms * 10)

        # 医疗术语准确性
        metrics.medical_accuracy = min(100, 50 + found_terms * 12)

        metrics.calculate_score()
        return metrics

    def _evaluate_usability(self, content: str) -> UsabilityMetrics:
        """评测可用性"""
        metrics = UsabilityMetrics()

        # 清晰度：基于文档结构和格式
        headers = len(re.findall(r'^#{1,6}\s', content, re.MULTILINE))
        if headers >= 5:
            metrics.clarity = 85
        elif headers >= 3:
            metrics.clarity = 70
        else:
            metrics.clarity = 50

        # 可执行性：检查是否有具体实现细节
        implementation_keywords = ["接口", "api", "数据库", "字段", "参数"]
        found_impl = sum(1 for kw in implementation_keywords if kw in content.lower())
        metrics.actionability = min(100, 40 + found_impl * 15)

        # 开发友好度
        if any(kw in content.lower() for kw in ["数据模型", "接口定义", "状态机"]):
            metrics.developer_friendly = 80
        else:
            metrics.developer_friendly = 60

        metrics.calculate_score()
        return metrics

    def _evaluate_compliance(self, content: str) -> ComplianceMetrics:
        """评测合规性（医疗行业）"""
        metrics = ComplianceMetrics()
        content_lower = content.lower()

        # 隐私保护
        metrics.privacy_protection = any(
            kw in content_lower
            for kw in ["隐私", "脱敏", "加密", "个人信息保护", "患者隐私"]
        )

        # 数据安全
        metrics.data_security = any(
            kw in content_lower
            for kw in ["数据安全", "加密存储", "传输加密", "权限控制"]
        )

        # 医疗规范
        metrics.medical_regulations = any(
            kw in content_lower
            for kw in ["等保三级", "医疗规范", "医疗法规", "行业标准"]
        )

        # 审计追溯
        metrics.audit_trail = any(
            kw in content_lower
            for kw in ["审计", "日志", "操作记录", "可追溯"]
        )

        metrics.calculate_score()
        return metrics
