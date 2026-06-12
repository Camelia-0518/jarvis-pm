"""技能输出验证器

提供标准输出Schema定义和验证功能
确保所有技能输出格式统一
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field, ValidationError



# ============ 需求分析输出Schema ============

class SuccessMetric(BaseModel):
    """成功指标"""
    name: str
    target: str
    timeFrame: str


class UserStory(BaseModel):
    """用户故事"""
    id: str
    role: str
    action: str
    benefit: str
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")


class FeatureList(BaseModel):
    """功能列表"""
    p0: List[str] = Field(default_factory=list)
    p1: List[str] = Field(default_factory=list)
    p2: List[str] = Field(default_factory=list)


class UserPersona(BaseModel):
    """用户画像"""
    who: str
    painPoints: str
    currentSolutions: str
    whyNewProduct: str


class RequirementAnalysisOutput(BaseModel):
    """需求分析标准输出"""
    productOneLiner: str = Field(default="", description="产品一句话描述")
    userPersona: UserPersona = Field(default_factory=lambda: UserPersona(
        who="", painPoints="", currentSolutions="", whyNewProduct=""
    ))
    featureList: FeatureList = Field(default_factory=FeatureList)
    userStories: List[UserStory] = Field(default_factory=list)
    successMetrics: Dict[str, Any] = Field(default_factory=dict)


# ============ PRD输出Schema ============

class PRDSection(BaseModel):
    """PRD章节"""
    title: str
    content: str
    priority: str = Field(default="normal", pattern="^(high|normal|low)$")


class PRDOutput(BaseModel):
    """PRD标准输出"""
    title: str = Field(default="")
    version: str = Field(default="1.0")
    sections: List[PRDSection] = Field(default_factory=list)
    markdown: str = Field(default="")


# ============ 商业模式输出Schema ============

class RevenueStream(BaseModel):
    """收入来源"""
    name: str
    description: str
    pricing: str


class BusinessModelOutput(BaseModel):
    """商业模式标准输出"""
    valueProposition: str = Field(default="")
    targetCustomer: str = Field(default="")
    revenueStreams: List[RevenueStream] = Field(default_factory=list)
    costStructure: List[str] = Field(default_factory=list)
    keyMetrics: List[str] = Field(default_factory=list)


# ============ 技术架构输出Schema ============

class TechComponent(BaseModel):
    """技术组件"""
    name: str
    description: str
    techStack: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)


class TechArchitectureOutput(BaseModel):
    """技术架构标准输出"""
    overview: str = Field(default="")
    techStack: str = Field(default="")
    components: List[TechComponent] = Field(default_factory=list)
    dataFlow: str = Field(default="")
    deployment: str = Field(default="")
    security: str = Field(default="")


# ============ 里程碑输出Schema ============

class MilestonePhase(BaseModel):
    """里程碑阶段"""
    name: str
    duration: str
    startDate: str = Field(default="")
    endDate: str = Field(default="")
    deliverables: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)


class MilestonePlanOutput(BaseModel):
    """里程碑规划标准输出"""
    phases: List[MilestonePhase] = Field(default_factory=list)
    totalDuration: str = Field(default="")
    criticalPath: List[str] = Field(default_factory=list)
    risks: List[Dict[str, str]] = Field(default_factory=list)


# ============ UX设计输出Schema ============

class UserFlow(BaseModel):
    """用户流程"""
    name: str
    steps: List[str] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)


class Wireframe(BaseModel):
    """线框图"""
    screen: str
    description: str
    elements: List[str] = Field(default_factory=list)
    layout: str = Field(default="")


class Interaction(BaseModel):
    """交互设计"""
    action: str
    trigger: str
    feedback: str
    nextState: str = Field(default="")


class UXDesignOutput(BaseModel):
    """UX设计标准输出"""
    userFlows: List[UserFlow] = Field(default_factory=list)
    wireframes: List[Wireframe] = Field(default_factory=list)
    interactions: List[Interaction] = Field(default_factory=list)
    designTokens: Dict[str, Any] = Field(default_factory=dict)


# ============ 医疗审查输出Schema ============

class MedicalRationality(BaseModel):
    """医疗合理性评估"""
    score: int = Field(default=0, ge=0, le=100)
    assessment: str = Field(default="")
    concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ComplianceItem(BaseModel):
    """合规项"""
    requirement: str
    status: str = Field(pattern="^(pass|fail|partial)$")


class ComplianceCategory(BaseModel):
    """合规类别"""
    name: str
    status: str = Field(pattern="^(pass|fail|partial)$")
    items: List[ComplianceItem] = Field(default_factory=list)


class RiskItem(BaseModel):
    """风险项"""
    risk: str
    level: str = Field(pattern="^(high|medium|low)$")
    impact: str = Field(default="")
    mitigation: str = Field(default="")


class MedicalReviewOutput(BaseModel):
    """医疗审查标准输出"""
    summary: str = Field(default="")
    medicalRationality: MedicalRationality = Field(default_factory=MedicalRationality)
    complianceAnalysis: Dict[str, Any] = Field(default_factory=dict)
    riskAssessment: List[RiskItem] = Field(default_factory=list)
    approvalRecommendation: str = Field(default="pending", pattern="^(approve|reject|pending|conditional)$")


# ============ 合规检查输出Schema ============

class ChecklistItem(BaseModel):
    """检查项"""
    item: str
    checked: bool = Field(default=False)
    category: str = Field(default="")


class ComplianceCheckOutput(BaseModel):
    """合规检查标准输出"""
    summary: str = Field(default="")
    overallStatus: str = Field(default="pending", pattern="^(pass|fail|partial|pending)$")
    score: int = Field(default=0, ge=0, le=100)
    categories: List[ComplianceCategory] = Field(default_factory=list)
    criticalIssues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    checklist: List[ChecklistItem] = Field(default_factory=list)


# ============ 技能ID到Schema映射 ============

SKILL_OUTPUT_SCHEMAS = {
    "requirement-analysis": RequirementAnalysisOutput,
    "write-prd": PRDOutput,
    "business-model": BusinessModelOutput,
    "tech-architecture": TechArchitectureOutput,
    "milestone-plan": MilestonePlanOutput,
    "ux-design": UXDesignOutput,
    "medical-review": MedicalReviewOutput,
    "compliance-check": ComplianceCheckOutput,
}


class OutputValidator:
    """技能输出验证器"""

    @classmethod
    def validate(cls, skill_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证技能输出是否符合标准Schema

        Args:
            skill_id: 技能ID
            output: 技能输出

        Returns:
            {"valid": bool, "data": dict, "errors": list}
        """
        schema_class = SKILL_OUTPUT_SCHEMAS.get(skill_id)

        if not schema_class:
            # 没有定义schema的技能，直接返回
            return {"valid": True, "data": output, "errors": []}

        try:
            validated = schema_class(**output)
            return {
                "valid": True,
                "data": validated.model_dump(),
                "errors": []
            }
        except ValidationError as e:
            errors = []
            for error in e.errors():
                errors.append({
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"]
                })

            return {
                "valid": False,
                "data": output,
                "errors": errors
            }

    @classmethod
    def fix_common_issues(cls, skill_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        修复常见的输出问题

        Args:
            skill_id: 技能ID
            output: 原始输出

        Returns:
            修复后的输出
        """
        fixed = output.copy()

        if skill_id == "requirement-analysis":
            # 确保featureList有p0/p1/p2
            if "featureList" not in fixed:
                fixed["featureList"] = {"p0": [], "p1": [], "p2": []}
            else:
                fl = fixed["featureList"]
                if not isinstance(fl, dict):
                    fixed["featureList"] = {"p0": [], "p1": [], "p2": []}
                else:
                    for key in ["p0", "p1", "p2"]:
                        if key not in fl or not isinstance(fl[key], list):
                            fl[key] = []

            # 确保userStories是列表
            if "userStories" not in fixed or not isinstance(fixed["userStories"], list):
                fixed["userStories"] = []

            # 确保userPersona存在
            if "userPersona" not in fixed:
                fixed["userPersona"] = {
                    "who": "",
                    "painPoints": "",
                    "currentSolutions": "",
                    "whyNewProduct": ""
                }

        elif skill_id == "write-prd":
            # 确保 markdown 字段存在（write-prd 现在直接返回 markdown）
            if "markdown" not in fixed or not fixed["markdown"]:
                # 尝试从 raw_response 回退提取
                raw = fixed.get("raw_response", "")
                if raw:
                    import re
                    md_match = re.search(r'```markdown\s*([\s\S]*?)```', raw)
                    if md_match:
                        fixed["markdown"] = md_match.group(1).strip()
                    else:
                        code_match = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', raw)
                        if code_match:
                            fixed["markdown"] = code_match.group(1).strip()
                        else:
                            fixed["markdown"] = raw.strip()
                else:
                    fixed["markdown"] = ""

            # 确保 title 存在
            if "title" not in fixed or not fixed["title"]:
                import re
                title_match = re.search(r'^#\s+(.+)$', fixed.get("markdown", ""), re.MULTILINE)
                if title_match:
                    fixed["title"] = title_match.group(1).strip()
                else:
                    fixed["title"] = "PRD Document"

            # 确保 version 存在
            if "version" not in fixed:
                fixed["version"] = "1.0"

            # 确保 sections 存在
            if "sections" not in fixed or not isinstance(fixed["sections"], list):
                fixed["sections"] = []

        elif skill_id == "tech-architecture":
            # 确保components是列表
            if "components" not in fixed or not isinstance(fixed["components"], list):
                fixed["components"] = []

        elif skill_id == "milestone-plan":
            # 确保phases是列表
            if "phases" not in fixed or not isinstance(fixed["phases"], list):
                fixed["phases"] = []

        return fixed

    @classmethod
    def get_schema_description(cls, skill_id: str) -> str:
        """获取Schema的描述信息"""
        schema_class = SKILL_OUTPUT_SCHEMAS.get(skill_id)
        if schema_class:
            return schema_class.__doc__ or "No description"
        return "Unknown skill"

    @classmethod
    def list_supported_skills(cls) -> List[str]:
        """列出所有支持验证的技能"""
        return list(SKILL_OUTPUT_SCHEMAS.keys())