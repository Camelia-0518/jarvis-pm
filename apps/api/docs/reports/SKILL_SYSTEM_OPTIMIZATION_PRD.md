# Jarvis PM Skill系统优化方案

> 版本: 1.0  
> 日期: 2026-04-11  
> 状态: 待实施

---

## 1. 问题诊断

### 1.1 当前系统问题清单

| 问题ID | 问题描述 | 严重级别 | 影响范围 |
|--------|----------|----------|----------|
| P0-001 | 4个核心技能返回占位符 | 🔴 高 | 商业模式/PRD/架构/里程碑 |
| P0-002 | 术语理解偏差 | 🔴 高 | 需求分析技能 |
| P1-001 | 输出格式不统一 | 🟡 中 | 所有技能 |
| P1-002 | 缺少UX设计环节 | 🟡 中 | 完整工作流 |
| P2-001 | 技能链缺少自动化 | 🟢 低 | 工作流编排 |

---

## 2. 优化方案

### 2.1 问题P0-001: 技能输出为空修复方案

#### 根因分析
```python
# 当前skill_processor.py中的实现
async def execute_skill(self, skill_id: str, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    # ... 参数处理 ...
    
    # ❌ 问题: 只是返回mock结果，没有调用真实LLM
    return {
        "success": True,
        "output": {"result": f"技能 {skill_id} 的执行结果", "timestamp": datetime.now().isoformat()},
        "formatted_output": f"## {skill['name']} 执行结果",
        "execution_time": 500,
        "token_usage": {"prompt": len(prompt), "completion": 28, "total": len(prompt) + 28}
    }
```

#### 解决方案

**A. 创建LLM Provider抽象层**

```python
# app/services/llm_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator
import httpx
import os

class LLMProvider(ABC):
    """LLM Provider抽象基类"""
    
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """同步完成"""
        pass
    
    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式输出"""
        pass

class KimiProvider(LLMProvider):
    """Kimi API Provider"""
    
    def __init__(self, api_key: str = None, model: str = "kimi-k2.5"):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        self.model = model
        self.base_url = "https://api.kimi.com/v1"
    
    async def complete(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

class OpenAIProvider(LLMProvider):
    """OpenAI API Provider"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    async def complete(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    **kwargs
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

class LLMProviderFactory:
    """LLM Provider工厂"""
    
    _providers = {
        "kimi": KimiProvider,
        "openai": OpenAIProvider,
    }
    
    @classmethod
    def create(cls, provider_name: str = None, **kwargs) -> LLMProvider:
        provider_name = provider_name or os.getenv("DEFAULT_LLM_PROVIDER", "kimi")
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class(**kwargs)
```

**B. 重构SkillProcessor使用真实LLM**

```python
# app/services/skill_processor.py
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from app.core.config import settings
from app.services.llm_provider import LLMProviderFactory


class SkillProcessor:
    """增强版技能处理器 - 支持真实LLM调用"""

    def __init__(self, llm_provider: str = None):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._llm = LLMProviderFactory.create(llm_provider)
        self._init_skills()

    async def execute_skill(
        self,
        skill_id: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行技能（接入真实LLM）"""
        skill = self._skills.get(skill_id)
        if not skill:
            return {"success": False, "error": f"技能 {skill_id} 不存在"}

        # 验证输入
        errors = self._validate_inputs(skill, inputs)
        if errors:
            return {"success": False, "error": "; ".join(errors)}

        # 构建prompt
        prompt = self._build_prompt(skill, inputs, context)

        # 调用LLM
        start_time = time.time()
        try:
            response_text = await self._llm.complete(
                prompt,
                temperature=0.7,
                max_tokens=4000
            )
            
            # 解析JSON输出
            output = self._parse_json_output(response_text)
            
            # 生成格式化输出
            formatted_output = self._format_output(skill, output)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "output": output,
                "formatted_output": formatted_output,
                "execution_time": execution_time,
                "token_usage": {
                    "prompt": len(prompt),
                    "completion": len(response_text),
                    "total": len(prompt) + len(response_text)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM调用失败: {str(e)}",
                "output": {}
            }

    def _parse_json_output(self, text: str) -> Dict[str, Any]:
        """从LLM响应中提取JSON"""
        # 尝试提取代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个文本
            json_str = text
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 如果解析失败，返回文本内容
            return {"raw_response": text}

    def _format_output(self, skill: Dict[str, Any], output: Dict[str, Any]) -> str:
        """生成格式化的markdown输出"""
        lines = [f"## {skill['name']} 执行结果\n"]
        
        # 根据技能类型生成不同的格式化输出
        if skill['id'] == 'requirement-analysis':
            lines.append(f"### 产品描述\n{output.get('productOneLiner', 'N/A')}\n")
            lines.append(f"### 功能列表\n")
            feature_list = output.get('featureList', {})
            for priority in ['p0', 'p1', 'p2']:
                features = feature_list.get(priority, [])
                if features:
                    lines.append(f"**{priority.upper()}:**")
                    for f in features:
                        lines.append(f"- {f}")
                    lines.append("")
        
        elif skill['id'] == 'write-prd':
            # PRD技能直接返回markdown内容
            return output.get('markdown', output.get('raw_response', 'N/A'))
        
        elif skill['id'] == 'tech-architecture':
            lines.append(f"### 技术栈\n{output.get('techStack', 'N/A')}\n")
            lines.append(f"### 系统架构\n")
            for component in output.get('components', []):
                lines.append(f"- **{component.get('name')}**: {component.get('description')}")
        
        else:
            # 默认格式
            lines.append("```json")
            lines.append(json.dumps(output, indent=2, ensure_ascii=False))
            lines.append("```")
        
        return "\n".join(lines)
```

**C. 更新requirements.txt**

```
# LLM Providers
httpx>=0.25.0
openai>=1.3.0
anthropic>=0.8.0
```

---

### 2.2 问题P0-002: 术语理解优化方案

#### 根因分析
- prompt模板使用通用描述，没有医疗专业术语支持
- 缺少术语澄清机制

#### 解决方案

**A. 创建医疗术语词典**

```python
# app/services/medical_terminology.py

MEDICAL_TERMS = {
    "切片借阅": {
        "definition": "患者或第三方机构申请借阅医院病理科保存的组织切片进行会诊或检测",
        "synonyms": ["玻片借阅", "病理切片外借", "切片外送"],
        "related_terms": ["病理科", "会诊", "免疫组化", "HE染色"],
        "context": "病理科业务流程"
    },
    "病历复印": {
        "definition": "患者申请复印住院病历、门诊病历等医疗文书",
        "synonyms": ["病历复制", "病案复印"],
        "related_terms": ["病案室", "出院病历", "病程记录"],
        "context": "病案管理业务"
    },
    "病理科": {
        "definition": "医院中负责疾病病理诊断的科室，处理组织切片、细胞学检查等",
        "synonyms": ["病理诊断中心"],
        "related_terms": ["病理医生", "病理技术员", "切片", "蜡块"],
        "context": "临床科室"
    },
    "免疫组化": {
        "definition": "免疫组织化学检测，用于病理诊断和肿瘤分型",
        "synonyms": ["IHC", "免疫染色"],
        "related_terms": ["病理诊断", "肿瘤标志物", "切片"],
        "context": "病理检测"
    }
}


def enrich_prompt_with_terminology(prompt: str, detected_terms: List[str]) -> str:
    """
    根据检测到的术语丰富prompt
    
    示例:
    输入: "设计一个切片借阅系统"
    输出: 在prompt中添加术语定义，帮助LLM理解
    """
    enrichment = []
    for term in detected_terms:
        if term in MEDICAL_TERMS:
            info = MEDICAL_TERMS[term]
            enrichment.append(f"术语'{term}'定义: {info['definition']}")
            enrichment.append(f"同义词: {', '.join(info['synonyms'])}")
            enrichment.append(f"相关术语: {', '.join(info['related_terms'])}")
    
    if enrichment:
        terminology_section = "\n\n【术语说明】\n" + "\n".join(enrichment)
        return prompt + terminology_section
    
    return prompt


def detect_medical_terms(text: str) -> List[str]:
    """检测文本中的医疗专业术语"""
    detected = []
    text_lower = text.lower()
    
    for term in MEDICAL_TERMS.keys():
        if term in text or term in text_lower:
            detected.append(term)
        else:
            # 检查同义词
            for synonym in MEDICAL_TERMS[term].get("synonyms", []):
                if synonym in text or synonym in text_lower:
                    detected.append(term)
                    break
    
    return detected
```

**B. 更新需求分析技能prompt**

```python
# 在_init_skills中更新requirement-analysis的prompt_template
"requirement-analysis": {
    # ... 其他配置 ...
    "prompt_template": """你是专业的产品经理，擅长医疗信息化产品的需求分析。

【术语词典】
如果输入中包含以下术语，请参考其定义：
- 切片借阅: 患者或第三方机构申请借阅医院病理科保存的组织切片进行会诊或检测
- 病理科: 医院中负责疾病病理诊断的科室
- 免疫组化: 用于病理诊断的免疫组织化学检测

请根据以下产品想法进行深度需求分析：

**产品想法**：{idea}
**目标用户**：{targetUsers}
**所属行业**：{industry}
**约束条件**：{constraints}

请按以下 JSON 格式输出分析结果：
{{
  "productOneLiner": "产品一句话描述（请严格基于输入的产品想法，不要改变原意）",
  "userPersona": {{
    "who": "用户是谁",
    "painPoints": "痛点是什么",
    "currentSolutions": "当前解决方案",
    "whyNewProduct": "为什么需要新产品"
  }},
  "featureList": {{
    "p0": ["必须有功能1", "必须有功能2"],
    "p1": ["应该有功能1"],
    "p2": ["可以有功能1"]
  }},
  "userStories": [
    {{"id": "1", "role": "用户角色", "action": "想要做什么", "benefit": "期望获得的价值", "priority": "high"}}
  ],
  "successMetrics": {{
    "northStar": "北极星指标",
    "metrics": [
      {{"name": "指标名", "target": "目标值", "timeFrame": "时间框架"}}
    ]
  }}
}}

重要提示：请严格基于用户输入的产品想法进行分析，不要将其理解为其他类似概念。""",
}
```

**C. 在SkillProcessor中集成术语处理**

```python
def _build_prompt(self, skill: Dict[str, Any], inputs: Dict[str, Any], context: Dict[str, Any]) -> str:
    """构建prompt，支持术语增强"""
    template = skill["prompt_template"]
    
    # 基本变量替换
    prompt = template.format(**inputs)
    
    # 医疗术语检测和增强
    if skill.get("category") == "medical" or skill["id"] in ["requirement-analysis", "medical-review"]:
        from app.services.medical_terminology import detect_medical_terms, enrich_prompt_with_terminology
        
        # 从所有输入中检测术语
        all_text = " ".join(str(v) for v in inputs.values() if isinstance(v, str))
        detected_terms = detect_medical_terms(all_text)
        
        if detected_terms:
            prompt = enrich_prompt_with_terminology(prompt, detected_terms)
    
    return prompt
```

---

### 2.3 问题P1-001: 输出格式统一方案

#### 解决方案

**A. 创建标准输出Schema**

```python
# app/schemas/skill_output.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


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
    priority: str = Field(..., pattern="^(high|medium|low)$")


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


# ===== 需求分析输出 =====
class RequirementAnalysisOutput(BaseModel):
    """需求分析标准输出"""
    productOneLiner: str
    userPersona: UserPersona
    featureList: FeatureList
    userStories: List[UserStory]
    successMetrics: Dict[str, Any]


# ===== PRD输出 =====
class PRDSection(BaseModel):
    """PRD章节"""
    title: str
    content: str
    priority: str = "normal"


class PRDOutput(BaseModel):
    """PRD标准输出"""
    title: str
    version: str
    sections: List[PRDSection]
    markdown: str  # 完整markdown格式


# ===== 技术架构输出 =====
class TechComponent(BaseModel):
    """技术组件"""
    name: str
    description: str
    techStack: List[str]
    responsibilities: List[str]


class TechArchitectureOutput(BaseModel):
    """技术架构标准输出"""
    overview: str
    techStack: str
    components: List[TechComponent]
    dataFlow: str
    deployment: str
    security: str


# ===== 里程碑输出 =====
class MilestonePhase(BaseModel):
    """里程碑阶段"""
    name: str
    duration: str
    startDate: str
    endDate: str
    deliverables: List[str]
    resources: List[str]


class MilestonePlanOutput(BaseModel):
    """里程碑规划标准输出"""
    phases: List[MilestonePhase]
    totalDuration: str
    criticalPath: List[str]
    risks: List[Dict[str, str]]


# ===== 统一技能输出Schema =====
class SkillOutputSchema(BaseModel):
    """统一的技能输出Schema"""
    success: bool
    output: Dict[str, Any]
    formatted_output: str
    execution_time: int  # milliseconds
    token_usage: Dict[str, int]
    error: Optional[str] = None
```

**B. 创建输出验证器**

```python
# app/services/output_validator.py
from typing import Dict, Any, Type
from pydantic import BaseModel, ValidationError
import json

from app.schemas.skill_output import (
    RequirementAnalysisOutput,
    PRDOutput,
    TechArchitectureOutput,
    MilestonePlanOutput,
)


# 技能ID到输出Schema的映射
SKILL_OUTPUT_SCHEMAS = {
    "requirement-analysis": RequirementAnalysisOutput,
    "write-prd": PRDOutput,
    "tech-architecture": TechArchitectureOutput,
    "milestone-plan": MilestonePlanOutput,
}


class OutputValidator:
    """技能输出验证器"""
    
    @classmethod
    def validate(cls, skill_id: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证技能输出是否符合标准Schema
        
        返回: {"valid": bool, "data": dict, "errors": list}
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
        """修复常见的输出问题"""
        fixed = output.copy()
        
        if skill_id == "requirement-analysis":
            # 确保featureList有p0/p1/p2
            if "featureList" not in fixed:
                fixed["featureList"] = {"p0": [], "p1": [], "p2": []}
            else:
                fl = fixed["featureList"]
                for key in ["p0", "p1", "p2"]:
                    if key not in fl:
                        fl[key] = []
            
            # 确保userStories是列表
            if "userStories" not in fixed:
                fixed["userStories"] = []
        
        elif skill_id == "write-prd":
            # 确保有markdown字段
            if "markdown" not in fixed:
                fixed["markdown"] = json.dumps(fixed, indent=2, ensure_ascii=False)
        
        return fixed
```

**C. 在SkillProcessor中集成验证**

```python
async def execute_skill(self, skill_id: str, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    # ... LLM调用 ...
    
    # 解析输出后验证
    output = self._parse_json_output(response_text)
    
    # 修复常见问题
    output = OutputValidator.fix_common_issues(skill_id, output)
    
    # 验证Schema
    validation = OutputValidator.validate(skill_id, output)
    
    if not validation["valid"]:
        # 记录验证错误，但 still 返回结果
        print(f"Warning: Output validation failed for {skill_id}: {validation['errors']}")
    
    # 使用验证后的数据
    output = validation["data"]
    
    # ... 生成formatted_output ...
```

---

### 2.4 问题P1-002: UX设计技能补全方案

#### 解决方案

**A. 添加UX设计技能定义**

```python
# 在_init_skills中添加
"ux-design": {
    "id": "ux-design",
    "name": "UX设计",
    "description": "生成产品原型设计和交互流程",
    "agentRole": "designer",
    "category": "design",
    "icon": "🎨",
    "tags": ["UX", "设计", "原型"],
    "parameters": [
        {
            "name": "prd",
            "label": "PRD文档",
            "type": "textarea",
            "description": "产品需求文档内容",
            "required": True,
        },
        {
            "name": "platform",
            "label": "目标平台",
            "type": "select",
            "description": "产品设计的目标平台",
            "required": True,
            "options": [
                {"label": "Web端", "value": "web"},
                {"label": "移动端", "value": "mobile"},
                {"label": "桌面端", "value": "desktop"},
                {"label": "小程序", "value": "miniprogram"},
            ],
        },
        {
            "name": "designSystem",
            "label": "设计规范",
            "type": "select",
            "description": "遵循的设计规范",
            "required": False,
            "options": [
                {"label": "Ant Design", "value": "ant_design"},
                {"label": "Element UI", "value": "element_ui"},
                {"label": "Material Design", "value": "material"},
                {"label": "自定义", "value": "custom"},
            ],
            "defaultValue": "ant_design",
        },
    ],
    "prompt_template": """你是专业的UX设计师，擅长医疗信息化产品的界面设计。

请根据以下PRD生成详细的UX设计方案：

**PRD内容**：{prd}
**目标平台**：{platform}
**设计规范**：{designSystem}

请按以下 JSON 格式输出：
{{
  "userFlows": [
    {{
      "name": "流程名称",
      "steps": ["步骤1", "步骤2", "步骤3"],
      "participants": ["参与者1", "参与者2"]
    }}
  ],
  "wireframes": [
    {{
      "screen": "页面名称",
      "description": "页面描述",
      "elements": ["元素1", "元素2"],
      "layout": "布局描述"
    }}
  ],
  "interactions": [
    {{
      "action": "用户操作",
      "trigger": "触发条件",
      "feedback": "系统反馈",
      "nextState": "下一步状态"
    }}
  ],
  "designTokens": {{
    "colors": ["#主色", "#辅助色"],
    "typography": "字体规范",
    "spacing": "间距规范"
  }}
}}

要求：
1. 考虑医疗场景的特殊性（如无障碍访问、高对比度）
2. 遵循{designSystem}设计规范
3. 输出可直接用于开发的详细说明""",
    "outputSchema": {
        "type": "object",
        "properties": {
            "userFlows": {"type": "array"},
            "wireframes": {"type": "array"},
            "interactions": {"type": "array"},
            "designTokens": {"type": "object"}
        },
        "required": ["userFlows", "wireframes"]
    }
}
```

---

### 2.5 问题P2-001: 技能链自动化方案

#### 解决方案

**A. 创建工作流引擎**

```python
# app/services/workflow_engine.py
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio


class WorkflowTriggerType(Enum):
    """工作流触发类型"""
    MANUAL = "manual"           # 手动触发
    AUTO_CHAIN = "auto_chain"   # 自动链式触发
    CONDITIONAL = "conditional" # 条件触发


@dataclass
class WorkflowStep:
    """工作流步骤"""
    skill_id: str
    step_name: str
    inputs_mapping: Dict[str, str]  # 如何从前一步获取输入
    condition: Optional[str] = None  # 执行条件
    timeout: int = 120  # 超时秒数


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    name: str
    description: str
    steps: List[WorkflowStep]
    trigger_type: WorkflowTriggerType


# 预定义的标准工作流
STANDARD_WORKFLOWS = {
    "product-design": WorkflowDefinition(
        name="产品设计工作流",
        description="从需求到设计的完整产品工作流",
        steps=[
            WorkflowStep(
                skill_id="requirement-analysis",
                step_name="需求分析",
                inputs_mapping={"idea": "$.initial.idea", "targetUsers": "$.initial.targetUsers"}
            ),
            WorkflowStep(
                skill_id="business-model",
                step_name="商业模式",
                inputs_mapping={"productDescription": "$.steps.requirement-analysis.output.productOneLiner"}
            ),
            WorkflowStep(
                skill_id="write-prd",
                step_name="撰写PRD",
                inputs_mapping={"requirementAnalysis": "$.steps.requirement-analysis.output"}
            ),
            WorkflowStep(
                skill_id="tech-architecture",
                step_name="技术架构",
                inputs_mapping={"prd": "$.steps.write-prd.output"}
            ),
            WorkflowStep(
                skill_id="ux-design",
                step_name="UX设计",
                inputs_mapping={"prd": "$.steps.write-prd.output"},
                condition="$.config.includeUX == true"
            ),
            WorkflowStep(
                skill_id="milestone-plan",
                step_name="里程碑规划",
                inputs_mapping={"prd": "$.steps.write-prd.output", "architecture": "$.steps.tech-architecture.output"}
            ),
        ],
        trigger_type=WorkflowTriggerType.MANUAL
    ),
    
    "medical-product-review": WorkflowDefinition(
        name="医疗产品审查工作流",
        description="医疗产品的专业审查流程",
        steps=[
            WorkflowStep(
                skill_id="medical-review",
                step_name="医疗审查",
                inputs_mapping={"requirement": "$.prd.requirementAnalysis"}
            ),
            WorkflowStep(
                skill_id="compliance-check",
                step_name="合规检查",
                inputs_mapping={"prd": "$.prd"}
            ),
            WorkflowStep(
                skill_id="multi-branch-analysis",
                step_name="多院区分析",
                inputs_mapping={"requirement": "$.prd.requirementAnalysis"},
                condition="$.config.multiBranch == true"
            ),
        ],
        trigger_type=WorkflowTriggerType.AUTO_CHAIN
    ),
}


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, skill_processor):
        self.skill_processor = skill_processor
        self.workflows = STANDARD_WORKFLOWS
    
    async def execute_workflow(
        self,
        workflow_name: str,
        initial_inputs: Dict[str, Any],
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行工作流"""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        context = {
            "initial": initial_inputs,
            "config": config or {},
            "steps": {},
        }
        
        results = []
        
        for step in workflow.steps:
            # 检查条件
            if step.condition and not self._evaluate_condition(step.condition, context):
                continue
            
            # 准备输入
            step_inputs = self._prepare_inputs(step.inputs_mapping, context)
            
            # 执行技能
            try:
                result = await asyncio.wait_for(
                    self.skill_processor.execute_skill(step.skill_id, step_inputs),
                    timeout=step.timeout
                )
                
                context["steps"][step.step_name] = result
                results.append({
                    "step": step.step_name,
                    "skill_id": step.skill_id,
                    "success": result.get("success"),
                    "output": result.get("output") if result.get("success") else None,
                    "error": result.get("error") if not result.get("success") else None,
                })
                
                # 如果失败，中断工作流
                if not result.get("success"):
                    break
                    
            except asyncio.TimeoutError:
                results.append({
                    "step": step.step_name,
                    "skill_id": step.skill_id,
                    "success": False,
                    "error": f"Timeout after {step.timeout}s"
                })
                break
        
        return {
            "workflow": workflow_name,
            "completed": all(r["success"] for r in results),
            "results": results,
            "context": context,
        }
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        try:
            # 简单的条件评估，实际可以使用更强大的表达式引擎
            # 例如: $.config.includeUX == true
            parts = condition.replace("$.", "").split(" == ")
            if len(parts) == 2:
                path, expected = parts
                expected = expected.strip().lower() == "true"
                
                # 从context中获取值
                value = context
                for key in path.split("."):
                    value = value.get(key, {})
                
                return bool(value) == expected
            return True
        except:
            return True
    
    def _prepare_inputs(self, mapping: Dict[str, str], context: Dict[str, Any]) -> Dict[str, Any]:
        """根据mapping从context中准备输入"""
        inputs = {}
        
        for key, path in mapping.items():
            if path.startswith("$."):
                # 从context中提取
                path_parts = path[2:].split(".")
                value = context
                for part in path_parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                inputs[key] = value
            else:
                # 直接值
                inputs[key] = path
        
        return inputs
```

**B. 添加工作流API端点**

```python
# app/api/v1/endpoints/workflows.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from app.services.workflow_engine import WorkflowEngine, STANDARD_WORKFLOWS
from app.services.skill_processor import SkillProcessor

router = APIRouter()


class WorkflowExecuteRequest(BaseModel):
    """工作流执行请求"""
    workflow_name: str = Field(..., description="工作流名称")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="初始输入")
    config: Dict[str, Any] = Field(default_factory=dict, description="工作流配置")


class WorkflowExecuteResponse(BaseModel):
    """工作流执行响应"""
    workflow: str
    completed: bool
    results: List[Dict[str, Any]]
    total_steps: int
    completed_steps: int


@router.get("/definitions", response_model=Dict[str, Any])
async def list_workflows():
    """列出所有可用工作流"""
    workflows = {}
    for name, definition in STANDARD_WORKFLOWS.items():
        workflows[name] = {
            "name": definition.name,
            "description": definition.description,
            "steps": [step.step_name for step in definition.steps],
            "trigger_type": definition.trigger_type.value,
        }
    return {"data": workflows}


@router.post("/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(request: WorkflowExecuteRequest):
    """执行工作流"""
    processor = SkillProcessor()
    engine = WorkflowEngine(processor)
    
    try:
        result = await engine.execute_workflow(
            request.workflow_name,
            request.inputs,
            request.config
        )
        
        return WorkflowExecuteResponse(
            workflow=result["workflow"],
            completed=result["completed"],
            results=result["results"],
            total_steps=len(result["results"]),
            completed_steps=sum(1 for r in result["results"] if r["success"])
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")
```

---

## 3. 实施计划

### 3.1 里程碑规划

| 阶段 | 时间 | 任务 | 交付物 |
|------|------|------|--------|
| **Phase 1** | Week 1-2 | P0问题修复 | LLM Provider + SkillProcessor重构 |
| **Phase 2** | Week 3 | 术语优化 | 医疗术语词典 + 增强Prompt |
| **Phase 3** | Week 4 | 输出标准化 | Schema定义 + 验证器 |
| **Phase 4** | Week 5 | UX补全 | UX设计技能 + 原型 |
| **Phase 5** | Week 6 | 自动化 | 工作流引擎 + API |

### 3.2 依赖关系

```
Phase 1 (LLM Provider)
    ↓
Phase 2 (术语优化) → Phase 3 (输出标准)
    ↓                    ↓
Phase 4 (UX设计) ←──────┘
    ↓
Phase 5 (工作流)
```

### 3.3 资源需求

| 资源 | 数量 | 说明 |
|------|------|------|
| LLM API Key | 1-2 | Kimi/OpenAI |
| Redis实例 | 1 | 结果缓存 |
| 开发人力 | 1人 | 全职2周 |

### 3.4 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LLM API不稳定 | 中 | 高 | 实现fallback机制，支持多provider |
| Token成本过高 | 中 | 中 | 添加缓存，Prompt优化 |
| 输出质量不稳定 | 高 | 高 | 增加验证层，质量问题自动重试 |

---

## 4. 预期收益

### 4.1 量化指标

| 指标 | 当前 | 目标 | 提升 |
|------|------|------|------|
| 技能输出完整度 | 42% (3/7) | 100% | +138% |
| 术语理解准确率 | ~60% | >95% | +58% |
| 工作流自动化率 | 0% | 80% | +80% |
| 输出格式一致性 | 30% | >90% | +200% |

### 4.2 业务价值

1. **提升用户体验** - 用户获得完整、准确的产品设计输出
2. **减少人工干预** - 自动化工作流减少80%的手动操作
3. **支持医疗场景** - 专业术语理解支持医疗信息化产品
4. **可扩展架构** - LLM Provider抽象支持未来接入更多模型

---

## 5. 附录

### 5.1 环境变量配置

```bash
# .env
# LLM配置
DEFAULT_LLM_PROVIDER=kimi
KIMI_API_KEY=your_kimi_api_key
OPENAI_API_KEY=your_openai_api_key

# 缓存配置
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# 功能开关
ENABLE_LLM_CACHE=true
ENABLE_OUTPUT_VALIDATION=true
ENABLE_WORKFLOW_ENGINE=true
```

### 5.2 数据库迁移

```sql
-- 添加技能执行记录表
CREATE TABLE skill_executions (
    id VARCHAR(36) PRIMARY KEY,
    skill_id VARCHAR(50) NOT NULL,
    workflow_id VARCHAR(36),
    inputs JSON,
    output JSON,
    success BOOLEAN,
    execution_time_ms INTEGER,
    token_usage JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加索引
CREATE INDEX idx_skill_executions_skill ON skill_executions(skill_id);
CREATE INDEX idx_skill_executions_workflow ON skill_executions(workflow_id);
CREATE INDEX idx_skill_executions_created ON skill_executions(created_at);
```

---

*文档版本: 1.0*  
*最后更新: 2026-04-11*  
*状态: 待评审*
