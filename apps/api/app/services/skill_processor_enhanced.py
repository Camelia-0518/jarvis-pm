"""增强版技能处理器

特性:
1. 真实LLM调用 (Kimi/OpenAI)
2. 医疗术语增强
3. 输出Schema验证
4. 结果缓存
5. 详细日志
"""

import json
import logging
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.core.cache import cache_manager
from app.agents.llm_client import LLMClient, LLMClientFactory, create_default_client
from app.services.medical_terminology import (
    detect_medical_terms,
    enrich_prompt_with_terminology,
    add_medical_context,
)
from app.services.output_validator import OutputValidator

# Lazy import to avoid circular dependencies at module load time
_retrieval_engine = None

def _get_retrieval_engine():
    global _retrieval_engine
    if _retrieval_engine is None:
        try:
            from app.api.v1.endpoints.rag import retrieval_engine
            _retrieval_engine = retrieval_engine
        except Exception:
            _retrieval_engine = False
    return _retrieval_engine if _retrieval_engine is not False else None


class SkillProcessorEnhanced:
    """增强版技能处理器"""

    def __init__(self, llm_provider: str = None, enable_cache: bool = True):
        self._skills: Dict[str, Dict[str, Any]] = {}
        # 统一使用 llm_client 体系的 FallbackLLMClient（支持真实 AI 自动降级）
        if llm_provider and llm_provider != "fallback":
            self._llm: LLMClient = LLMClientFactory.create(llm_provider)
        else:
            self._llm: LLMClient = create_default_client()
        self._enable_cache = enable_cache
        self._init_skills()

    def _init_skills(self):
        """初始化所有技能定义"""
        self._skills = {
            # ========== PM 技能 ==========
            "requirement-analysis": {
                "id": "requirement-analysis",
                "name": "需求分析",
                "description": "深度分析产品需求，输出用户画像、功能列表、用户故事和成功指标",
                "agentRole": "ceo",
                "category": "analysis",
                "icon": "🔍",
                "tags": ["需求", "分析", "产品"],
                "parameters": [
                    {
                        "name": "idea",
                        "label": "产品想法",
                        "type": "textarea",
                        "description": "描述你的产品想法，包括要解决什么问题、目标用户是谁",
                        "required": True,
                    },
                    {
                        "name": "targetUsers",
                        "label": "目标用户",
                        "type": "string",
                        "description": "目标用户群体描述",
                        "required": True,
                    },
                    {
                        "name": "industry",
                        "label": "所属行业",
                        "type": "select",
                        "description": "产品所属行业",
                        "required": True,
                        "options": [
                            {"label": "医疗信息化", "value": "medical"},
                            {"label": "金融科技", "value": "fintech"},
                            {"label": "电子商务", "value": "ecommerce"},
                            {"label": "教育科技", "value": "edtech"},
                            {"label": "企业服务", "value": "enterprise"},
                            {"label": "其他", "value": "other"},
                        ],
                        "defaultValue": "medical",
                    },
                    {
                        "name": "constraints",
                        "label": "约束条件",
                        "type": "textarea",
                        "description": "任何已知的约束条件（预算、时间、技术限制等）",
                        "required": False,
                    },
                ],
                "prompt_template": """你是专业的产品经理，擅长{industry}产品的需求分析。

请根据以下产品想法进行深度需求分析：

**产品想法**：{idea}
**目标用户**：{targetUsers}
**约束条件**：{constraints}

请按以下 JSON 格式输出分析结果：
{{
  "productOneLiner": "产品一句话描述（简洁有力）",
  "userPersona": {{
    "who": "用户是谁",
    "painPoints": "痛点是什么",
    "currentSolutions": "当前解决方案",
    "whyNewProduct": "为什么需要新产品"
  }},
  "featureList": {{
    "p0": ["必须有功能1", "必须有功能2", "必须有功能3"],
    "p1": ["应该有功能1", "应该有功能2"],
    "p2": ["可以有功能1"]
  }},
  "userStories": [
    {{"id": "1", "role": "用户角色", "action": "想要做什么", "benefit": "期望获得的价值", "priority": "high"}},
    {{"id": "2", "role": "用户角色", "action": "想要做什么", "benefit": "期望获得的价值", "priority": "medium"}},
    {{"id": "3", "role": "用户角色", "action": "想要做什么", "benefit": "期望获得的价值", "priority": "low"}}
  ],
  "successMetrics": {{
    "northStar": "北极星指标",
    "metrics": [
      {{"name": "指标名", "target": "目标值", "timeFrame": "时间框架"}}
    ]
  }}
}}

要求：
1. 基于输入的产品想法，不要改变原意
2. 功能列表要具体可落地
3. 用户故事要遵循"作为...我想要...以便..."格式
4. 指标要可量化、可衡量""",
            },

            "write-prd": {
                "id": "write-prd",
                "name": "撰写 PRD",
                "description": "根据需求分析结果撰写详细的产品需求文档",
                "agentRole": "ceo",
                "category": "analysis",
                "icon": "📝",
                "tags": ["PRD", "文档", "需求"],
                "parameters": [
                    {
                        "name": "requirementAnalysis",
                        "label": "需求分析结果",
                        "type": "textarea",
                        "description": "需求分析的JSON结果",
                        "required": True,
                    },
                    {
                        "name": "template",
                        "label": "PRD 模板",
                        "type": "select",
                        "description": "选择PRD模板类型",
                        "required": True,
                        "options": [
                            {"label": "标准模板", "value": "standard"},
                            {"label": "医疗行业", "value": "medical"},
                            {"label": "敏捷开发", "value": "agile"},
                            {"label": "精简版", "value": "minimal"},
                        ],
                    },
                    {
                        "name": "detailLevel",
                        "label": "详细程度",
                        "type": "select",
                        "description": "PRD的详细程度",
                        "required": True,
                        "options": [
                            {"label": "详细", "value": "detailed"},
                            {"label": "适中", "value": "moderate"},
                            {"label": "精简", "value": "concise"},
                        ],
                    },
                ],
                "prompt_template": """你是资深产品经理，擅长撰写高质量的PRD文档。

请根据以下需求分析结果撰写PRD：

**需求分析**：{requirementAnalysis}
**模板类型**：{template}
**详细程度**：{detailLevel}

请根据需求分析结果撰写PRD，按以下 JSON 格式返回：
{{
  "title": "文档标题（简洁）",
  "version": "1.0",
  "sections": [
    {{"title": "1. 文档信息", "content": "版本历史、作者...", "priority": "high"}},
    {{"title": "2. 项目背景与目标", "content": "...", "priority": "high"}},
    {{"title": "3. 用户画像", "content": "...", "priority": "high"}},
    {{"title": "4. 功能需求", "content": "...", "priority": "high"}},
    {{"title": "5. 非功能需求", "content": "...", "priority": "normal"}},
    {{"title": "6. 数据埋点", "content": "...", "priority": "normal"}},
    {{"title": "7. 里程碑", "content": "...", "priority": "normal"}},
    {{"title": "8. 附录", "content": "...", "priority": "low"}}
  ],
  "markdown": "# 文档标题\n\n> 版本: 1.0\n\n## 1. 文档信息\n...\n\n## 2. 项目背景与目标\n...\n\n（每个章节写2-3段详细内容，总字数不少于500字）"
}}

重要要求：
1. 必须返回合法 JSON
2. title 必须是完整的字符串，不要截断
3. markdown 字段放完整的 PRD 正文（用 \n 换行）
4. sections 的 content 也要充实详细，不要只写一句话
5. 使用中文撰写""",
            },

            "tech-architecture": {
                "id": "tech-architecture",
                "name": "技术架构设计",
                "description": "根据PRD设计技术架构方案",
                "agentRole": "engManager",
                "category": "development",
                "icon": "🏗️",
                "tags": ["架构", "技术", "设计"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档",
                        "required": True,
                    },
                    {
                        "name": "scalability",
                        "label": "可扩展性要求",
                        "type": "select",
                        "description": "系统的可扩展性要求",
                        "required": True,
                        "options": [
                            {"label": "小型", "value": "small"},
                            {"label": "中型", "value": "medium"},
                            {"label": "大型", "value": "large"},
                            {"label": "超大规模", "value": "xlarge"},
                        ],
                    },
                    {
                        "name": "techStackPreference",
                        "label": "技术栈偏好",
                        "type": "string",
                        "description": "技术栈偏好（可选）",
                        "required": False,
                    },
                ],
                "prompt_template": """你是资深架构师，擅长设计高可用、可扩展的技术架构。

请根据以下PRD设计技术架构：

**PRD**：{prd}
**可扩展性要求**：{scalability}
**技术栈偏好**：{techStackPreference}

请按以下 JSON 格式输出：
{{
  "overview": "架构概述",
  "techStack": "推荐技术栈",
  "components": [
    {{"name": "组件名", "description": "组件描述", "techStack": ["技术1", "技术2"], "responsibilities": ["职责1", "职责2"]}}
  ],
  "dataFlow": "数据流描述",
  "deployment": "部署方案",
  "security": "安全设计"
}}""",
            },

            "business-model": {
                "id": "business-model",
                "name": "商业模式设计",
                "description": "分析并设计产品的商业模式",
                "agentRole": "ceo",
                "category": "planning",
                "icon": "💰",
                "tags": ["商业", "模式", "盈利"],
                "parameters": [
                    {
                        "name": "productDescription",
                        "label": "产品描述",
                        "type": "textarea",
                        "description": "产品一句话描述",
                        "required": True,
                    },
                    {
                        "name": "market",
                        "label": "目标市场",
                        "type": "string",
                        "description": "目标市场描述",
                        "required": True,
                    },
                    {
                        "name": "competitors",
                        "label": "主要竞争对手",
                        "type": "string",
                        "description": "竞争对手分析（可选）",
                        "required": False,
                    },
                ],
                "prompt_template": """你是商业战略专家，擅长设计创新的商业模式。

请为以下产品设计商业模式：

**产品**：{productDescription}
**目标市场**：{market}
**竞争对手**：{competitors}

请按以下 JSON 格式输出：
{{
  "valueProposition": "价值主张",
  "targetCustomer": "目标客户",
  "revenueStreams": [
    {{"name": "收入来源", "description": "描述", "pricing": "定价策略"}}
  ],
  "costStructure": ["成本项1", "成本项2"],
  "keyMetrics": ["关键指标1", "关键指标2"]
}}""",
            },

            "milestone-plan": {
                "id": "milestone-plan",
                "name": "里程碑规划",
                "description": "根据PRD制定项目里程碑和排期",
                "agentRole": "engManager",
                "category": "planning",
                "icon": "📅",
                "tags": ["规划", "里程碑", "排期"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档",
                        "required": True,
                    },
                    {
                        "name": "teamSize",
                        "label": "团队规模",
                        "type": "number",
                        "description": "团队人数",
                        "required": True,
                    },
                    {
                        "name": "architecture",
                        "label": "技术架构",
                        "type": "textarea",
                        "description": "技术架构方案（可选）",
                        "required": False,
                    },
                ],
                "prompt_template": """你是项目管理专家，擅长制定合理的项目里程碑。

请根据以下信息制定里程碑规划：

**PRD**：{prd}
**技术架构**：{architecture}
**团队规模**：{teamSize}人

请按以下 JSON 格式输出：
{{
  "phases": [
    {{
      "name": "阶段名称",
      "duration": "持续时间",
      "startDate": "开始日期",
      "endDate": "结束日期",
      "deliverables": ["交付物1", "交付物2"],
      "resources": ["所需资源1", "所需资源2"]
    }}
  ],
  "totalDuration": "总工期",
  "criticalPath": ["关键路径1", "关键路径2"],
  "risks": [{{"risk": "风险描述", "mitigation": "缓解措施"}}]
}}""",
            },

            "medical-review": {
                "id": "medical-review",
                "name": "医疗专业审查",
                "description": "从医疗专业角度审查产品需求",
                "agentRole": "medical",
                "category": "medical",
                "icon": "⚕️",
                "tags": ["医疗", "审查", "专业"],
                "parameters": [
                    {
                        "name": "requirement",
                        "label": "需求内容",
                        "type": "textarea",
                        "description": "需求描述或PRD",
                        "required": True,
                    },
                    {
                        "name": "featureType",
                        "label": "功能类型",
                        "type": "select",
                        "description": "功能类型",
                        "required": True,
                        "options": [
                            {"label": "临床工作流", "value": "clinical_workflow"},
                            {"label": "患者管理", "value": "patient_management"},
                            {"label": "医嘱系统", "value": "order_system"},
                            {"label": "数据分析", "value": "data_analysis"},
                            {"label": "其他", "value": "other"},
                        ],
                    },
                    {
                        "name": "patientData",
                        "label": "是否涉及患者数据",
                        "type": "boolean",
                        "description": "是否涉及患者敏感数据",
                        "required": True,
                    },
                ],
                "prompt_template": """你是医疗信息化专家，熟悉医疗业务流程和合规要求。

请审查以下需求：

**需求**：{requirement}
**功能类型**：{featureType}
**涉及患者数据**：{patientData}

请按以下 JSON 格式输出审查结果：
{{
  "summary": "审查结论摘要",
  "medicalRationality": {{
    "score": 85,
    "assessment": "业务合理性评估",
    "concerns": ["关注点1"],
    "recommendations": ["建议1"]
  }},
  "complianceAnalysis": {{
    "applicableRegulations": ["适用法规1"],
    "complianceStatus": "compliant",
    "gaps": [],
    "actions": []
  }},
  "riskAssessment": [
    {{"risk": "风险描述", "level": "medium", "impact": "高", "mitigation": "缓解措施"}}
  ],
  "approvalRecommendation": "approve"
}}

评分标准：
- 80-100: 优秀，建议通过
- 60-79: 良好，需要小幅修改
- 40-59: 一般，需要较大修改
- 0-39: 不建议通过""",
            },

            "compliance-check": {
                "id": "compliance-check",
                "name": "合规检查",
                "description": "检查产品是否符合医疗行业合规要求",
                "agentRole": "medical",
                "category": "medical",
                "icon": "✅",
                "tags": ["合规", "检查", "法规"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档",
                        "required": True,
                    },
                    {
                        "name": "complianceLevel",
                        "label": "合规等级要求",
                        "type": "select",
                        "description": "需要的合规等级",
                        "required": True,
                        "options": [
                            {"label": "等保二级", "value": "level2"},
                            {"label": "等保三级", "value": "level3"},
                            {"label": "HIPAA", "value": "hipaa"},
                            {"label": "通用", "value": "general"},
                        ],
                    },
                ],
                "prompt_template": """你是医疗合规专家，熟悉等保、HIPAA等医疗行业合规要求。

请检查以下PRD的合规性：

**PRD**：{prd}
**合规等级要求**：{complianceLevel}

请按以下 JSON 格式输出检查结果：
{{
  "summary": "整体评估摘要",
  "overallStatus": "partial",
  "score": 78,
  "categories": [
    {{
      "name": "身份鉴别",
      "status": "pass",
      "items": [
        {{"requirement": "多因素认证", "status": "pass"}}
      ]
    }}
  ],
  "criticalIssues": [],
  "recommendations": ["建议1", "建议2"],
  "checklist": [
    {{"item": "检查项", "checked": true, "category": "类别"}}
  ]
}}

状态说明：
- pass: 完全合规
- partial: 部分合规，需要改进
- fail: 不合规""",
            },

            "ux-design": {
                "id": "ux-design",
                "name": "UX 设计",
                "description": "生成完整的UX设计方案，包括用户流程、线框图、交互设计和设计系统",
                "agentRole": "designer",
                "category": "design",
                "icon": "🎨",
                "tags": ["UX", "设计", "用户体验"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档内容",
                        "required": True,
                    },
                    {
                        "name": "platform",
                        "label": "目标平台",
                        "type": "select",
                        "description": "设计的目标平台",
                        "required": True,
                        "options": [
                            {"label": "Web 应用", "value": "web"},
                            {"label": "移动端 App", "value": "mobile-app"},
                            {"label": "响应式 Web", "value": "responsive"},
                            {"label": "小程序", "value": "miniprogram"},
                        ],
                        "defaultValue": "web",
                    },
                    {
                        "name": "designStyle",
                        "label": "设计风格",
                        "type": "select",
                        "description": "UI设计风格偏好",
                        "required": False,
                        "options": [
                            {"label": "简洁现代", "value": "modern"},
                            {"label": "专业商务", "value": "professional"},
                            {"label": "活泼友好", "value": "friendly"},
                            {"label": "医疗专业", "value": "medical"},
                        ],
                        "defaultValue": "modern",
                    },
                ],
                "prompt_template": """你是资深UX设计师，擅长用户流程设计和交互设计。

请根据以下 PRD 生成完整的 UX 设计方案：

**PRD 文档**：
{prd}

**目标平台**：{platform}
**设计风格**：{designStyle}

请按以下 JSON 格式输出设计结果：
{{
  "userFlows": [
    {{
      "name": "用户流程名称",
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
      "nextState": "下一状态"
    }}
  ],
  "designTokens": {{
    "colors": {{"primary": "#xxx", "secondary": "#xxx"}},
    "typography": {{"heading": "字体", "body": "字体"}},
    "spacing": {{"unit": "8px"}}
  }}
}}

要求：
1. 用户流程要覆盖核心使用场景
2. 线框图描述要具体到每个元素的布局
3. 交互设计要说明状态变化和反馈
4. 设计系统要包含颜色、字体、间距规范""",
            },

            "multi-branch-analysis": {
                "id": "multi-branch-analysis",
                "name": "多院区需求分析",
                "description": "分析多院区场景下的需求差异",
                "agentRole": "medical",
                "category": "medical",
                "icon": "🏥",
                "tags": ["多院区", "需求", "分析"],
                "parameters": [
                    {
                        "name": "requirement",
                        "label": "需求描述",
                        "type": "textarea",
                        "description": "基础需求描述",
                        "required": True,
                    },
                    {
                        "name": "branches",
                        "label": "涉及院区",
                        "type": "string",
                        "description": "涉及的院区列表",
                        "required": True,
                    },
                    {
                        "name": "standardFeatures",
                        "label": "预期标准功能",
                        "type": "string",
                        "description": "预期在各院区通用的功能",
                        "required": False,
                    },
                ],
                "prompt_template": """你是医疗信息化专家，熟悉多院区医院的业务差异。

请分析以下需求在多院区场景下的差异：

**需求**：{requirement}
**涉及院区**：{branches}
**预期标准功能**：{standardFeatures}

请按以下 JSON 格式输出分析结果：
{{
  "standardFeatures": ["标准化功能1"],
  "branchSpecific": {{
    "院区A": ["特定功能1"]
  }},
  "policyDifferences": [
    {{"aspect": "方面", "standard": "标准", "branches": {{"院区A": "差异"}}}}
  ],
  "recommendations": ["建议1"]
}}""",
            },
        }

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        return [
            {
                "id": skill["id"],
                "name": skill["name"],
                "description": skill["description"],
                "agentRole": skill["agentRole"],
                "category": skill["category"],
                "icon": skill.get("icon", ""),
                "tags": skill.get("tags", []),
            }
            for skill in self._skills.values()
        ]

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能详情"""
        skill = self._skills.get(skill_id)
        if skill:
            return {
                **skill,
                "outputSchema": skill.get("outputSchema", {}),
            }
        return None

    def _validate_inputs(self, skill: Dict[str, Any], inputs: Dict[str, Any]) -> List[str]:
        """验证输入参数"""
        errors = []
        for param in skill["parameters"]:
            if param.get("required") and not inputs.get(param["name"]):
                errors.append(f"参数 '{param['label']}' 是必填项")
        return errors

    def _build_prompt(self, skill: Dict[str, Any], inputs: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建prompt，支持术语增强"""
        template = skill["prompt_template"]

        # 基本变量替换
        try:
            prompt = template.format(**inputs)
        except KeyError as e:
            # 如果有缺失的变量，使用空字符串填充
            missing_key = str(e).strip("'")
            inputs[missing_key] = ""
            prompt = template.format(**inputs)

        # 医疗术语检测和增强
        if skill.get("category") == "medical" or skill["id"] in ["requirement-analysis", "medical-review"]:
            # 从所有输入中检测术语
            all_text = " ".join(str(v) for v in inputs.values() if isinstance(v, (str, int, float)))
            detected_terms = detect_medical_terms(all_text)

            if detected_terms:
                prompt = enrich_prompt_with_terminology(prompt, detected_terms)

        # RAG 检索增强：将相关 Obsidian 知识库内容注入 prompt
        # 按行业过滤检索结果，避免非医疗请求被医疗知识库污染
        try:
            engine = _get_retrieval_engine()
            if engine and engine.documents:
                all_text = " ".join(str(v) for v in inputs.values() if isinstance(v, (str, int, float)))
                query = all_text[:200]

                # 推断请求的行业：先查 inputs 中的 industry/template，再关键词检测
                industry_filter = None
                if inputs.get("industry") and inputs["industry"] != "other":
                    industry_filter = inputs["industry"]
                elif inputs.get("template") and inputs["template"] != "default":
                    industry_map = {
                        "medical": "medical",
                        "saas": "saas",
                        "ecommerce": "ecommerce",
                        "agile": None,
                        "standard": None,
                        "minimal": None,
                    }
                    industry_filter = industry_map.get(inputs["template"])
                # 如果仍无法确定，通过关键词检测 fallback
                if not industry_filter:
                    medical_keywords = [
                        "医疗", "医院", "病理", "切片", "患者", "医生", "护士", "医护",
                        "挂号", "就诊", "病历", "病案", "HIS", "医保", "药品",
                        "检验", "检查", "处方", "住院", "门诊", "科室", "急诊",
                        "medical", "hospital", "pathology", "patient", "doctor", "nurse",
                        "healthcare", "clinical", "diagnosis", "prescription", "emr", "lis"
                    ]
                    if any(kw in all_text.lower() for kw in medical_keywords):
                        industry_filter = "medical"

                # 只有确定行业时才进行过滤检索；general/unknown 不过滤，让检索自然排序
                rag_results = engine.search(query, top_k=3, industry_filter=industry_filter)
                if rag_results:
                    rag_context = "\n\n【相关知识库参考】\n"
                    for i, res in enumerate(rag_results, 1):
                        snippet = res.content.replace("\n", " ")[:400]
                        rag_context += f"[{i}] {snippet}\n"
                    prompt = prompt + "\n" + rag_context
        except Exception:
            pass  # RAG 失败不应阻塞主流程

        return prompt

    def _parse_json_output(self, text: str, skill_id: str = None) -> Dict[str, Any]:
        """从LLM响应中提取JSON，支持截断修复"""
        # 尝试提取代码块中的JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个文本
            json_str = text.strip()

        try:
            parsed = json.loads(json_str)
            # 对 write-prd，验证解析结果是否合理
            if skill_id == "write-prd":
                title = parsed.get("title", "")
                if not title or len(title) < 3 or title in ("{", "[", ""):
                    return {"raw_response": text}
            return parsed
        except json.JSONDecodeError:
            # 尝试修复被截断的JSON
            try:
                fixed = self._repair_truncated_json(json_str)
                parsed = json.loads(fixed)
                # 修复后也要验证 write-prd 的 title
                if skill_id == "write-prd":
                    title = parsed.get("title", "")
                    if not title or len(title) < 3 or title in ("{", "[", ""):
                        return {"raw_response": text}
                return parsed
            except json.JSONDecodeError:
                # 如果解析失败，返回文本内容
                return {"raw_response": text}

    def _repair_truncated_json(self, raw: str) -> str:
        """尝试修复被截断的JSON字符串"""
        cleaned = raw.rstrip()

        # 如果还在字符串中，找到最后一个完整的字符串闭合
        last_safe_pos = -1
        i = 0
        in_string = False
        escape_next = False
        while i < len(cleaned):
            ch = cleaned[i]
            if escape_next:
                escape_next = False
                i += 1
                continue
            if ch == '\\':
                escape_next = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
                if not in_string:
                    last_safe_pos = i
                i += 1
                continue
            i += 1

        if in_string and last_safe_pos >= 0:
            cleaned = cleaned[:last_safe_pos + 1]

        # 去掉末尾的逗号
        cleaned = cleaned.rstrip().rstrip(',')

        # 补齐缺失的闭合括号/花括号（忽略字符串内部）
        brace_depth = 0
        bracket_depth = 0
        in_str = False
        escape = False
        for ch in cleaned:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if not in_str:
                if ch == '{':
                    brace_depth += 1
                elif ch == '}':
                    brace_depth -= 1
                elif ch == '[':
                    bracket_depth += 1
                elif ch == ']':
                    bracket_depth -= 1

        cleaned += ']' * max(0, bracket_depth)
        cleaned += '}' * max(0, brace_depth)

        return cleaned

    def _format_output(self, skill: Dict[str, Any], output: Dict[str, Any]) -> str:
        """生成格式化的markdown输出"""
        lines = [f"## {skill['name']} 执行结果\n"]

        # 根据技能类型生成不同的格式化输出
        if skill['id'] == 'requirement-analysis':
            lines.append(f"### 产品描述\n{output.get('productOneLiner', 'N/A')}\n")
            lines.append(f"### 用户画像\n")
            persona = output.get('userPersona', {})
            lines.append(f"- **用户是谁**: {persona.get('who', 'N/A')}")
            lines.append(f"- **痛点**: {persona.get('painPoints', 'N/A')}")
            lines.append(f"- **当前解决方案**: {persona.get('currentSolutions', 'N/A')}")
            lines.append(f"- **为什么需要新产品**: {persona.get('whyNewProduct', 'N/A')}")
            lines.append("")
            lines.append(f"### 功能列表\n")
            feature_list = output.get('featureList', {})
            for priority, label in [('p0', 'P0（必须有）'), ('p1', 'P1（应该有）'), ('p2', 'P2（可以有）')]:
                features = feature_list.get(priority, [])
                if features:
                    lines.append(f"**{label}:**")
                    for f in features:
                        lines.append(f"- {f}")
                    lines.append("")

        elif skill['id'] == 'write-prd':
            # LLM 直接返回 markdown，直接使用
            return output.get('markdown', output.get('raw_response', 'N/A'))

        elif skill['id'] == 'tech-architecture':
            lines.append(f"### 技术栈\n{output.get('techStack', 'N/A')}\n")
            lines.append(f"### 系统组件\n")
            for component in output.get('components', []):
                lines.append(f"- **{component.get('name')}**: {component.get('description')}")

        elif skill['id'] == 'ux-design':
            lines.append(f"### 用户流程\n")
            for flow in output.get('userFlows', []):
                lines.append(f"**{flow.get('name', '未命名')}**")
                for step in flow.get('steps', []):
                    lines.append(f"- {step}")
                lines.append("")
            lines.append(f"### 线框图\n")
            for wf in output.get('wireframes', []):
                lines.append(f"**{wf.get('screen', '未命名')}**: {wf.get('description', '')}")
                lines.append(f"- 布局: {wf.get('layout', 'N/A')}")
                lines.append("")
            lines.append(f"### 交互设计\n")
            for inter in output.get('interactions', []):
                lines.append(f"- **{inter.get('action', '操作')}**: {inter.get('trigger', '')} → {inter.get('feedback', '')}")
            lines.append("")
            tokens = output.get('designTokens', {})
            if tokens:
                lines.append(f"### 设计系统\n")
                colors = tokens.get('colors', {})
                if colors:
                    lines.append(f"- 主色: {colors.get('primary', 'N/A')}")
                typography = tokens.get('typography', {})
                if typography:
                    lines.append(f"- 字体: {typography.get('heading', 'N/A')}")

        else:
            # 默认格式
            lines.append("```json")
            lines.append(json.dumps(output, indent=2, ensure_ascii=False))
            lines.append("```")

        return "\n".join(lines)

    def _get_cache_key(self, skill_id: str, inputs: Dict[str, Any]) -> str:
        """生成缓存key"""
        import hashlib
        key_data = f"{skill_id}:{json.dumps(inputs, sort_keys=True)}"
        return f"skill:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def execute_skill(
        self,
        skill_id: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        执行技能（增强版）

        Args:
            skill_id: 技能ID
            inputs: 输入参数
            context: 上下文信息
            skip_cache: 是否跳过缓存

        Returns:
            技能执行结果
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return {"success": False, "error": f"技能 {skill_id} 不存在", "output": {}}

        # 验证输入
        errors = self._validate_inputs(skill, inputs)
        if errors:
            return {"success": False, "error": "; ".join(errors), "output": {}}

        # 检查缓存
        if self._enable_cache and not skip_cache:
            cache_key = self._get_cache_key(skill_id, inputs)
            try:
                cached = await cache_manager.get(cache_key)
                if cached:
                    cached["from_cache"] = True
                    return cached
            except:
                pass  # 缓存失败继续执行

        # 构建prompt
        prompt = self._build_prompt(skill, inputs, context or {})

        # 调用LLM
        start_time = time.time()
        try:
            # write-prd needs more tokens for full markdown output
            max_tokens = 8000 if skill_id == "write-prd" else 4000
            response_text = await self._llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_tokens
            )

            # 解析JSON输出
            output = self._parse_json_output(response_text, skill_id=skill_id)

            # 修复常见问题
            output = OutputValidator.fix_common_issues(skill_id, output)

            # 验证Schema
            validation = OutputValidator.validate(skill_id, output)

            if not validation["valid"]:
                # 记录验证错误，但仍然返回结果
                logger.warning(f"Output validation failed for {skill_id}: {validation['errors']}")

            # 使用验证后的数据
            output = validation["data"]

            # 生成格式化输出
            formatted_output = self._format_output(skill, output)

            execution_time = int((time.time() - start_time) * 1000)

            result = {
                "success": True,
                "output": output,
                "formatted_output": formatted_output,
                "execution_time": execution_time,
                "token_usage": {
                    "prompt": len(prompt),
                    "completion": len(response_text),
                    "total": len(prompt) + len(response_text)
                },
                "from_cache": False
            }

            # 缓存结果
            if self._enable_cache:
                try:
                    await cache_manager.set(cache_key, result, ttl=3600)
                except:
                    pass

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"LLM调用失败: {str(e)}",
                "output": {},
                "formatted_output": f"## 执行失败\n\n错误: {str(e)}"
            }
