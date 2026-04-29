"""技能处理器

提供技能定义管理和执行功能。
"""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.services.skill_processor_enhanced import SkillProcessorEnhanced


class SkillProcessor:
    """技能处理器 - 管理技能定义和执行（兼容层，执行时委托给增强版处理器）"""

    def __init__(self):
        # 技能定义注册表
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._init_skills()
        # 增强版处理器（负责真实 LLM 调用、缓存、Schema 验证、医疗术语增强）
        self._enhanced = SkillProcessorEnhanced(enable_cache=True)

    # 技能输出 Schema 和示例（与前端共享，消除重复定义）
    _OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
        "requirement-analysis": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "productOneLiner": {"type": "string"},
                    "userPersona": {
                        "type": "object",
                        "properties": {
                            "who": {"type": "string"},
                            "painPoints": {"type": "string"},
                            "currentSolutions": {"type": "string"},
                            "whyNewProduct": {"type": "string"},
                        },
                    },
                    "featureList": {
                        "type": "object",
                        "properties": {
                            "p0": {"type": "array", "items": {"type": "string"}},
                            "p1": {"type": "array", "items": {"type": "string"}},
                            "p2": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "userStories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "role": {"type": "string"},
                                "action": {"type": "string"},
                                "benefit": {"type": "string"},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            },
                        },
                    },
                    "successMetrics": {
                        "type": "object",
                        "properties": {
                            "northStar": {"type": "string"},
                            "metrics": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "target": {"type": "string"},
                                        "timeFrame": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
                "required": ["productOneLiner", "userPersona", "featureList", "userStories", "successMetrics"],
            },
            "examples": [
                {
                    "id": "medical-record-copy",
                    "name": "病案复印系统",
                    "description": "医院病历在线申请复印系统",
                    "inputs": {
                        "idea": "一个帮助患者在线申请病历复印并快递到家的系统",
                        "targetUsers": "医院患者、病案室工作人员",
                        "industry": "medical",
                    },
                    "outputPreview": "产品一句话描述：一个帮助患者在线申请病案复印并快递到家的医疗服务平台...",
                }
            ],
        },
        "write-prd": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "version": {"type": "string"},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "priority": {"type": "string"},
                            },
                        },
                    },
                    "markdown": {"type": "string"},
                },
            },
            "examples": [],
        },
        "medical-review": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "medicalRationality": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "assessment": {"type": "string"},
                            "concerns": {"type": "array", "items": {"type": "string"}},
                            "recommendations": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "complianceAnalysis": {
                        "type": "object",
                        "properties": {
                            "applicableRegulations": {"type": "array", "items": {"type": "string"}},
                            "complianceStatus": {"type": "string", "enum": ["compliant", "partial", "non-compliant"]},
                            "gaps": {"type": "array", "items": {"type": "string"}},
                            "actions": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "riskAssessment": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "risk": {"type": "string"},
                                "level": {"type": "string", "enum": ["high", "medium", "low"]},
                                "impact": {"type": "string"},
                                "mitigation": {"type": "string"},
                            },
                        },
                    },
                    "approvalRecommendation": {"type": "string", "enum": ["approve", "approve-with-conditions", "reject"]},
                },
            },
            "examples": [],
        },
        "compliance-check": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "overallStatus": {"type": "string", "enum": ["pass", "fail", "partial"]},
                    "score": {"type": "number"},
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "status": {"type": "string", "enum": ["pass", "fail", "partial"]},
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "requirement": {"type": "string"},
                                            "status": {"type": "string", "enum": ["pass", "fail", "na"]},
                                            "evidence": {"type": "string"},
                                            "remediation": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "criticalIssues": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                    "checklist": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item": {"type": "string"},
                                "checked": {"type": "boolean"},
                                "category": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "examples": [],
        },
        "multi-branch-analysis": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "standardFeatures": {"type": "array", "items": {"type": "string"}},
                    "branchSpecific": {"type": "object"},
                    "policyDifferences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "aspect": {"type": "string"},
                                "standard": {"type": "string"},
                                "branches": {"type": "object"},
                            },
                        },
                    },
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
            },
            "examples": [],
        },
    }

    def reload_skills(self):
        """重新加载所有技能定义（支持热更新，无需重启进程）"""
        self._skills.clear()
        self._init_skills()
        return {"reloaded_at": datetime.now().isoformat(), "skill_count": len(self._skills)}

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
                "prompt_template": """你是专业的产品经理，擅长需求分析。

请根据以下产品想法进行深度需求分析：

**产品想法**：{idea}
**目标用户**：{targetUsers}
**所属行业**：{industry}
**约束条件**：{constraints}

重要提示：请确保输出简洁、结构完整，避免过长导致 JSON 截断。每个字段控制在 2-3 句话以内，用户故事只写 2 条最核心的。

请按以下 JSON 格式输出分析结果：
{{
  "productOneLiner": "产品一句话描述（20字以内）",
  "userPersona": {{
    "who": "用户是谁（一句话）",
    "painPoints": "核心痛点（一句话）",
    "currentSolutions": "当前解决方案（一句话）",
    "whyNewProduct": "为什么需要新产品（一句话）"
  }},
  "featureList": {{
    "p0": ["核心功能1", "核心功能2"],
    "p1": ["重要功能1"],
    "p2": ["扩展功能1"]
  }},
  "userStories": [
    {{"id": "1", "role": "用户角色", "action": "想要做什么", "benefit": "期望获得的价值", "priority": "high"}},
    {{"id": "2", "role": "用户角色", "action": "想要做什么", "benefit": "期望获得的价值", "priority": "medium"}}
  ],
  "successMetrics": {{
    "northStar": "北极星指标",
    "metrics": [
      {{"name": "指标名称", "target": "目标值", "timeFrame": "时间范围"}}
    ]
  }},
  "requirementDoc": "用一段话（100字左右）总结需求分析结果，包含产品定位、核心用户、主要功能和成功标准"
}}""",
            },

            "write-prd": {
                "id": "write-prd",
                "name": "撰写 PRD",
                "description": "根据需求分析结果生成完整的产品需求文档",
                "agentRole": "ceo",
                "category": "design",
                "icon": "📝",
                "tags": ["PRD", "文档", "需求"],
                "parameters": [
                    {
                        "name": "requirementAnalysis",
                        "label": "需求分析结果",
                        "type": "textarea",
                        "description": "需求分析的输出内容",
                        "required": True,
                    },
                    {
                        "name": "template",
                        "label": "PRD 模板",
                        "type": "select",
                        "description": "选择PRD模板风格",
                        "required": True,
                        "options": [
                            {"label": "标准PRD", "value": "standard"},
                            {"label": "敏捷用户故事", "value": "agile"},
                            {"label": "医疗行业专用", "value": "medical"},
                        ],
                        "defaultValue": "standard",
                    },
                    {
                        "name": "detailLevel",
                        "label": "详细程度",
                        "type": "select",
                        "description": "PRD 的详细程度",
                        "required": True,
                        "options": [
                            {"label": "精简版", "value": "concise"},
                            {"label": "标准版", "value": "standard"},
                            {"label": "详细版", "value": "detailed"},
                        ],
                        "defaultValue": "standard",
                    },
                ],
                "prompt_template": """你是专业的产品经理，擅长撰写产品需求文档（PRD）。

请根据以下需求分析结果生成一份完整、可直接用于评审的 PRD：

**需求分析结果**：
{requirementAnalysis}

**模板风格**：{template}
**详细程度**：{detailLevel}

要求：
1. 生成内容充实，PRD 总字数不少于 500 字，各章节描述具体、完整
2. 必须包含以下章节：产品概述、用户画像、功能需求、非功能需求
3. 每个章节内容要详细，不能只是标题或一句话
4. 直接输出 Markdown 格式的 PRD 正文，不要添加额外说明

请按以下 JSON 格式返回，markdown 字段包含完整 PRD 内容：
{{
  "title": "产品名称",
  "version": "1.0",
  "sections": [
    {{"title": "产品概述", "content": "详细描述产品定位、目标用户和核心价值", "priority": "high"}},
    {{"title": "用户画像", "content": "详细描述核心用户群体、使用场景和痛点分析", "priority": "high"}},
    {{"title": "功能需求", "content": "详细的功能列表和优先级说明", "priority": "high"}},
    {{"title": "非功能需求", "content": "性能、安全、合规、可用性等方面的要求", "priority": "normal"}}
  ],
  "markdown": "# PRD\\n\\n## 产品概述\\n...\\n\\n## 用户画像\\n...\\n\\n## 功能需求\\n...\\n\\n## 非功能需求\\n..."
}}""",
            },

            "business-model": {
                "id": "business-model",
                "name": "商业模式设计",
                "description": "分析并设计产品的商业模式",
                "agentRole": "ceo",
                "category": "analysis",
                "icon": "💼",
                "tags": ["商业", "模式", "战略"],
                "parameters": [
                    {
                        "name": "productDescription",
                        "label": "产品描述",
                        "type": "textarea",
                        "description": "产品或服务的详细描述",
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
                        "type": "textarea",
                        "description": "主要竞争对手及其优劣势",
                        "required": False,
                    },
                ],
                "prompt_template": """你是商业模式专家，擅长设计和分析商业模式。

请分析以下产品的商业模式：

**产品描述**：{productDescription}
**目标市场**：{market}
**竞争对手**：{competitors}

重要提示：请确保输出简洁、结构完整，每个字段只写2-3句话，避免 JSON 截断。

请按以下 JSON 格式输出分析结果：
{{
  "valueProposition": "核心价值主张（一句话）",
  "customerSegments": ["客户细分1", "客户细分2"],
  "revenueStreams": ["收入来源1", "收入来源2"],
  "costStructure": ["主要成本1", "主要成本2"],
  "channels": ["渠道1", "渠道2"],
  "keyMetrics": ["关键指标1", "关键指标2"],
  "competitiveAdvantages": ["竞争优势1", "竞争优势2"]
}}""",
            },

            # ========== 工程经理技能 ==========
            "tech-architecture": {
                "id": "tech-architecture",
                "name": "技术架构设计",
                "description": "根据PRD生成完整的技术架构方案",
                "agentRole": "engManager",
                "category": "development",
                "icon": "🏗️",
                "tags": ["架构", "技术", "设计"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档内容",
                        "required": True,
                    },
                    {
                        "name": "techStackPreference",
                        "label": "技术栈偏好",
                        "type": "select",
                        "description": "偏好的技术栈",
                        "required": False,
                        "options": [
                            {"label": "React + Node.js", "value": "react-node"},
                            {"label": "Vue + Spring Boot", "value": "vue-java"},
                            {"label": "Next.js + Python", "value": "next-python"},
                            {"label": "不限", "value": "flexible"},
                        ],
                        "defaultValue": "flexible",
                    },
                    {
                        "name": "scalability",
                        "label": "可扩展性要求",
                        "type": "select",
                        "description": "系统的可扩展性要求",
                        "required": True,
                        "options": [
                            {"label": "小规模（<1000用户）", "value": "small"},
                            {"label": "中等规模（1万-10万用户）", "value": "medium"},
                            {"label": "大规模（>10万用户）", "value": "large"},
                        ],
                        "defaultValue": "medium",
                    },
                ],
                "prompt_template": """你是资深架构师，擅长设计可扩展的技术架构。

请根据以下 PRD 设计技术架构：

**PRD 文档**：
{prd}

**技术栈偏好**：{techStackPreference}
**可扩展性要求**：{scalability}

请输出以下内容：
1. 架构概述
2. 技术栈选型（前端、后端、数据库、基础设施）
3. 系统架构图（Mermaid 格式）
4. 核心组件设计
5. 数据模型设计
6. API 设计
7. 安全考虑
8. 部署架构

请按 JSON 格式输出。""",
            },

            "milestone-plan": {
                "id": "milestone-plan",
                "name": "里程碑规划",
                "description": "根据PRD和技术架构制定详细的项目里程碑计划",
                "agentRole": "engManager",
                "category": "planning",
                "icon": "📅",
                "tags": ["规划", "里程碑", "项目管理"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档",
                        "required": True,
                    },
                    {
                        "name": "architecture",
                        "label": "技术架构",
                        "type": "textarea",
                        "description": "技术架构设计文档（可选）",
                        "required": False,
                    },
                    {
                        "name": "teamSize",
                        "label": "团队规模",
                        "type": "select",
                        "description": "项目团队规模",
                        "required": True,
                        "options": [
                            {"label": "小型团队（2-3人）", "value": "small"},
                            {"label": "中型团队（4-7人）", "value": "medium"},
                            {"label": "大型团队（8-15人）", "value": "large"},
                        ],
                        "defaultValue": "medium",
                    },
                ],
                "prompt_template": """你是项目管理专家，擅长制定项目里程碑计划。

请根据以下信息制定里程碑计划：

**PRD 文档**：
{prd}

**技术架构**：
{architecture}

**团队规模**：{teamSize}

请输出：
1. 项目概述
2. 阶段划分（每个阶段的目标、交付物、时间估算）
3. 资源配置（团队角色、工具）
4. 关键路径
5. 里程碑节点
6. 风险评估和缓解措施

请按 JSON 格式输出。""",
            },

            # ========== 设计师技能 ==========
            "ux-design": {
                "id": "ux-design",
                "name": "UX 设计",
                "description": "生成完整的UX设计方案",
                "agentRole": "designer",
                "category": "design",
                "icon": "🎨",
                "tags": ["UX", "设计", "用户体验"],
                "parameters": [
                    {
                        "name": "prd",
                        "label": "PRD 文档",
                        "type": "textarea",
                        "description": "产品需求文档",
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

请根据以下 PRD 生成 UX 设计方案：

**PRD 文档**：
{prd}

**目标平台**：{platform}
**设计风格**：{designStyle}

请输出：
1. 设计概述
2. 用户流程图（关键用户旅程的详细步骤）
3. 线框图描述（关键页面的布局、元素）
4. 设计系统（颜色、字体、组件规范）
5. 交互模式

请按 JSON 格式输出。""",
            },

            # ========== 医疗行业专用技能 ==========
            "medical-review": {
                "id": "medical-review",
                "name": "医疗业务评审",
                "description": "从医疗业务角度评审需求的合理性、合规性和可行性",
                "agentRole": "medical-officer",
                "category": "medical",
                "icon": "🏥",
                "tags": ["医疗", "评审", "业务"],
                "parameters": [
                    {
                        "name": "requirement",
                        "label": "需求内容",
                        "type": "textarea",
                        "description": "需求标题和详细描述",
                        "required": True,
                    },
                    {
                        "name": "featureType",
                        "label": "功能类型",
                        "type": "select",
                        "description": "医疗功能类型",
                        "required": True,
                        "options": [
                            {"label": "病案管理", "value": "medical-record"},
                            {"label": "预约挂号", "value": "appointment"},
                            {"label": "门诊缴费", "value": "payment"},
                            {"label": "检查检验", "value": "lab"},
                            {"label": "处方管理", "value": "prescription"},
                            {"label": "消息推送", "value": "notification"},
                            {"label": "其他", "value": "other"},
                        ],
                        "defaultValue": "other",
                    },
                    {
                        "name": "patientData",
                        "label": "是否涉及患者数据",
                        "type": "boolean",
                        "description": "功能是否涉及患者隐私数据",
                        "required": True,
                        "defaultValue": True,
                    },
                ],
                "prompt_template": """你是医疗业务专家，精通医院业务流程和医疗信息化。

请评审以下医疗信息化需求：

**需求内容**：
{requirement}

**功能类型**：{featureType}
**涉及患者数据**：{patientData}

请从以下维度进行评审：
1. 医疗业务合理性评分（0-100）及评估说明
2. 合规性分析（适用法规、合规状态、差距、改进措施）
3. 风险评估（识别风险点、评估等级、缓解措施）
4. 审批建议（approve/approve-with-conditions/reject）

请按 JSON 格式输出。""",
            },

            "compliance-check": {
                "id": "compliance-check",
                "name": "合规检查",
                "description": "检查产品设计是否符合医疗行业法规和合规要求",
                "agentRole": "compliance-officer",
                "category": "medical",
                "icon": "✅",
                "tags": ["合规", "法规", "安全"],
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
                        "description": "需要满足的合规等级",
                        "required": True,
                        "options": [
                            {"label": "等保二级", "value": "level2"},
                            {"label": "等保三级", "value": "level3"},
                            {"label": "三甲医院标准", "value": "class3-hospital"},
                        ],
                        "defaultValue": "level3",
                    },
                ],
                "prompt_template": """你是医疗合规专家，精通等保、医疗数据安全等法规。

请检查以下 PRD 的合规性：

**PRD 文档**：
{prd}

**合规等级要求**：{complianceLevel}

请按以下维度检查合规性：
1. 总体评估（通过/不通过/部分通过，评分）
2. 各分类检查项（身份鉴别、访问控制、数据安全、日志审计等）
3. 关键问题列表
4. 改进建议
5. 合规检查清单

请按 JSON 格式输出。""",
            },

            "multi-branch-analysis": {
                "id": "multi-branch-analysis",
                "name": "多院区需求分析",
                "description": "分析多院区场景下的需求适配性",
                "agentRole": "multi-branch-pm",
                "category": "medical",
                "icon": "🏢",
                "tags": ["多院区", "适配", "分析"],
                "parameters": [
                    {
                        "name": "requirement",
                        "label": "需求内容",
                        "type": "textarea",
                        "description": "需求详细描述",
                        "required": True,
                    },
                    {
                        "name": "branches",
                        "label": "涉及院区",
                        "type": "textarea",
                        "description": "涉及的院区列表及其地区",
                        "required": True,
                    },
                    {
                        "name": "standardFeatures",
                        "label": "预期标准功能",
                        "type": "textarea",
                        "description": "预期作为标准功能的部分",
                        "required": False,
                    },
                ],
                "prompt_template": """你是多院区医疗信息化专家，擅长处理标准功能与地方特性的平衡。

请分析以下多院区需求：

**需求内容**：
{requirement}

**涉及院区**：
{branches}

**预期标准功能**：
{standardFeatures}

请输出分析结果：
1. 标准功能列表（适用于所有院区）
2. 各院区特定需求及适配工作量
3. 数据同步策略
4. 部署策略建议
5. 风险评估

请按 JSON 格式输出。""",
            },
        }

    def _enrich_skill_metadata(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        """丰富技能元数据，合并 outputSchema 和 examples"""
        result = {k: v for k, v in skill.items() if k != "prompt_template"}
        extra = self._OUTPUT_SCHEMAS.get(skill.get("id", ""), {})
        result.setdefault("outputSchema", extra.get("outputSchema", {}))
        result.setdefault("examples", extra.get("examples", []))
        return result

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """获取所有技能定义"""
        return [
            self._enrich_skill_metadata(skill)
            for skill in self._skills.values()
        ]

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取技能定义"""
        skill = self._skills.get(skill_id)
        if skill:
            return self._enrich_skill_metadata(skill)
        return None

    def get_skill_prompt(self, skill_id: str) -> Optional[str]:
        """获取技能的提示词模板"""
        skill = self._skills.get(skill_id)
        return skill.get("prompt_template") if skill else None

    def get_skills_by_role(self, role: str) -> List[Dict[str, Any]]:
        """根据Agent角色获取技能"""
        return [
            self._enrich_skill_metadata(skill)
            for skill in self._skills.values()
            if skill.get("agentRole") == role
        ]

    def get_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根据分类获取技能"""
        return [
            self._enrich_skill_metadata(skill)
            for skill in self._skills.values()
            if skill.get("category") == category
        ]

    def validate_inputs(self, skill_id: str, inputs: Dict[str, Any]) -> List[str]:
        """验证技能输入"""
        errors = []
        skill = self._skills.get(skill_id)

        if not skill:
            return [f"技能 {skill_id} 不存在"]

        parameters = skill.get("parameters", [])
        for param in parameters:
            if param.get("required"):
                param_name = param.get("name")
                value = inputs.get(param_name)
                if value is None or value == "":
                    errors.append(f"参数 '{param.get('label', param_name)}' 是必填项")

        return errors

    async def execute_skill(
        self,
        skill_id: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行技能

        Args:
            skill_id: 技能ID
            inputs: 输入参数
            context: 执行上下文
            options: 执行选项

        Returns:
            执行结果
        """
        start_time = time.time()

        # 验证技能存在
        skill = self._skills.get(skill_id)
        if not skill:
            return {
                "success": False,
                "error": f"技能 {skill_id} 不存在",
                "output": {},
            }

        # 获取提示词模板
        prompt_template = skill.get("prompt_template", "")

        # 为可选参数设置默认值（必须在验证前完成）
        parameters = skill.get("parameters", [])
        for param in parameters:
            param_name = param.get("name")
            if param_name not in inputs:
                if param.get("type") == "textarea":
                    inputs[param_name] = ""
                elif param.get("type") == "string":
                    inputs[param_name] = ""
                elif param.get("type") == "array":
                    inputs[param_name] = []
                elif param.get("type") == "boolean":
                    inputs[param_name] = param.get("defaultValue", False)
                elif param.get("type") == "number":
                    inputs[param_name] = param.get("defaultValue", 0)
                elif param.get("type") == "select":
                    inputs[param_name] = param.get("defaultValue", "")

        # 验证输入
        validation_errors = self.validate_inputs(skill_id, inputs)
        if validation_errors:
            return {
                "success": False,
                "error": "; ".join(validation_errors),
                "output": {},
            }

        try:
            # 优先委托给增强版处理器（支持真实 LLM、缓存、Schema 验证、医疗术语增强）
            if skill_id in self._enhanced._skills:
                # 使用新的 provider 重新创建 enhanced 实例，避免缓存旧的 mock provider
                from app.core.config import settings
                provider = settings.DEFAULT_AI_PROVIDER
                enhanced = SkillProcessorEnhanced(llm_provider=provider, enable_cache=True)
                enhanced_result = await enhanced.execute_skill(
                    skill_id=skill_id,
                    inputs=inputs,
                    context=context or {},
                    skip_cache=True
                )
                # 保持与旧接口兼容的字段映射
                return {
                    "success": enhanced_result.get("success", False),
                    "output": enhanced_result.get("output", {}),
                    "formatted_output": enhanced_result.get("formatted_output", "")
                                    or enhanced_result.get("formattedOutput", ""),
                    "execution_time": enhanced_result.get("execution_time", 0),
                    "token_usage": enhanced_result.get("token_usage", {}),
                    "error": enhanced_result.get("error"),
                }

            # 回退：使用旧版 AI 调用逻辑（用于增强版未注册的技能）
            prompt = prompt_template.format(**inputs)
            output = await self._call_ai_for_skill(skill, prompt, options)

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "output": output,
                "formatted_output": self._format_output_as_markdown(skill, output),
                "execution_time": execution_time,
                "token_usage": {
                    "prompt": len(prompt) // 4,
                    "completion": len(json.dumps(output)) // 4,
                    "total": (len(prompt) + len(json.dumps(output))) // 4,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": {},
            }

    def _repair_truncated_json(self, raw: str) -> str:
        """尝试修复被截断的 JSON 字符串"""
        # 1. 找到最后一个完整的字符串闭合位置
        # 从末尾向前搜索，找到最后一个未被转义的引号
        cleaned = raw.rstrip()
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

        # 如果还在字符串里，截断到 last_safe_pos
        if in_string and last_safe_pos >= 0:
            cleaned = cleaned[:last_safe_pos + 1]

        # 2. 补齐缺失的闭合括号/花括号
        open_braces = cleaned.count('{') - cleaned.count('}')
        open_brackets = cleaned.count('[') - cleaned.count(']')

        # 去掉末尾的逗号
        cleaned = cleaned.rstrip().rstrip(',')

        # 补齐闭合
        cleaned += ']' * max(0, open_brackets)
        cleaned += '}' * max(0, open_braces)

        return cleaned

    async def _call_ai_for_skill(
        self,
        skill: Dict[str, Any],
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """调用真实 AI 服务执行技能"""
        from app.services.ai_service import ai_service

        skill_id = skill.get("id")
        skill_name = skill.get("name", "")

        try:
            # write-prd 使用更宽松的 system prompt，允许 markdown 回退
            if skill_id == "write-prd":
                system_prompt = f"""你是{skill_name}专家。请根据用户输入生成完整的产品需求文档。
优先以合法 JSON 格式返回，包含 title、version、sections、markdown 字段。
如果 JSON 输出会被截断，请确保 markdown 字段的内容完整且可用。
也可以直接输出 Markdown 格式的 PRD 正文。"""

                content = await ai_service.chat(
                    prompt,
                    context={"system_prompt": system_prompt, "max_tokens": 8000}
                )

                if not content or not content.strip():
                    raise Exception("AI 返回了空内容，请检查模型参数或稍后重试")

                raw = content.strip()

                # 如果以 { 开头，尝试 JSON 解析
                if raw.startswith("{"):
                    try:
                        # 尝试从 markdown 代码块中提取
                        json_raw = raw
                        if "```json" in json_raw:
                            json_raw = json_raw.split("```json")[1].split("```")[0]
                        elif "```" in json_raw:
                            json_raw = json_raw.split("```")[1].split("```")[0]
                        json_raw = json_raw.strip()
                        result = json.loads(json_raw)
                        if "markdown" in result:
                            return result
                    except (json.JSONDecodeError, Exception):
                        pass

                # 回退：将原始内容包装为 markdown
                return {
                    "title": "产品需求文档",
                    "version": "1.0",
                    "sections": [
                        {"title": "产品概述", "content": "详见 markdown 正文", "priority": "high"},
                        {"title": "用户画像", "content": "详见 markdown 正文", "priority": "high"},
                        {"title": "功能需求", "content": "详见 markdown 正文", "priority": "high"},
                        {"title": "非功能需求", "content": "详见 markdown 正文", "priority": "normal"},
                    ],
                    "markdown": raw,
                }

            # 其他 skill 保持严格的 JSON 解析
            system_prompt = f"""你是{skill_name}专家。请根据用户输入生成结构化结果。
必须以合法、完整的 JSON 格式返回，确保 JSON 结构闭合完整，不要截断。
只输出 JSON，不要添加 markdown 代码块标记或其他说明文字。"""

            content = await ai_service.chat(
                prompt,
                context={"system_prompt": system_prompt, "max_tokens": 8000}
            )

            if not content or not content.strip():
                raise Exception("AI 返回了空内容，请检查模型参数或稍后重试")

            # 尝试从 markdown 代码块中提取 JSON
            raw = content
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]

            raw = raw.strip()
            if not raw:
                raise Exception(f"AI 返回内容经清理后为空。原始内容: {repr(content[:200])}")

            try:
                result = json.loads(raw)
                return result
            except json.JSONDecodeError:
                # 尝试修复截断 JSON
                repaired = self._repair_truncated_json(raw)
                result = json.loads(repaired)
                return result
        except Exception as e:
            # 如果解析失败，抛出异常让上层感知技能执行失败
            error_detail = f"JSON解析失败: {str(e)}"
            if 'content' in locals() and content:
                # 记录原始内容的前500字符用于调试
                error_detail += f" | 原始内容预览: {content[:500]}"
            raise Exception(error_detail)

    def _format_output_as_markdown(self, skill: Dict[str, Any], output: Dict[str, Any]) -> str:
        """将输出格式化为 Markdown"""
        skill_name = skill.get("name", "")
        skill_id = skill.get("id", "")

        if skill_id == "requirement-analysis":
            return f"""## 需求分析结果

### 产品一句话描述
{output.get('productOneLiner', '')}

### 用户画像
- **用户是谁**: {output.get('userPersona', {}).get('who', '')}
- **痛点是什么**: {output.get('userPersona', {}).get('painPoints', '')}
- **当前解决方案**: {output.get('userPersona', {}).get('currentSolutions', '')}
- **为什么需要新产品**: {output.get('userPersona', {}).get('whyNewProduct', '')}

### 功能列表
**P0（必须有）:**
{chr(10).join(['- ' + f for f in output.get('featureList', {}).get('p0', [])])}

**P1（应该有）:**
{chr(10).join(['- ' + f for f in output.get('featureList', {}).get('p1', [])])}

**P2（可以有）:**
{chr(10).join(['- ' + f for f in output.get('featureList', {}).get('p2', [])])}
"""

        elif skill_id == "medical-review":
            return f"""## 医疗业务评审结果

### 评审结论
{output.get('approvalRecommendation', '')}

### 业务合理性评分
**{output.get('medicalRationality', {}).get('score', 0)}/100**

{output.get('medicalRationality', {}).get('assessment', '')}

### 合规性分析
**状态**: {output.get('complianceAnalysis', {}).get('complianceStatus', '')}

**适用法规**:
{chr(10).join(['- ' + r for r in output.get('complianceAnalysis', {}).get('applicableRegulations', [])])}
"""

        else:
            # 通用 Markdown 格式
            return f"## {skill_name} 执行结果\n\n```json\n{json.dumps(output, indent=2, ensure_ascii=False)}\n```"


# 导入 asyncio 用于模拟延迟
import asyncio

# 导出单例实例
skill_processor = SkillProcessor()
