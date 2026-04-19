#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能模板系统

自动检测行业类型并应用专用模板
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class IndustryType(Enum):
    """行业类型"""
    MEDICAL = "medical"
    FINANCE = "finance"
    EDUCATION = "education"
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    UNKNOWN = "unknown"


@dataclass
class ComplianceRequirement:
    """合规要求"""
    name: str
    description: str
    category: str  # security, privacy, audit, legal
    priority: str  # critical, high, medium, low
    checklist: List[str] = field(default_factory=list)


@dataclass
class IndustryTemplate:
    """行业模板"""
    id: str
    name: str
    industry: IndustryType
    description: str
    keywords: List[str]
    compliance_requirements: List[ComplianceRequirement]
    workflow_enhancements: Dict[str, Any]
    agent_prompts: Dict[str, str]
    mandatory_checks: List[str]


class TemplateSystem:
    """
    智能模板系统

    自动检测行业类型并应用专用模板
    """

    # 行业关键词映射
    INDUSTRY_KEYWORDS = {
        IndustryType.MEDICAL: [
            "医疗", "医院", "病理", "切片", "患者", "医生", "护士",
            "挂号", "就诊", "病历", "病案", "HIS", "医保", "药品",
            "检验", "检查", "处方", "住院", "门诊", "科室",
            "medical", "hospital", "pathology", "patient", "doctor",
            "healthcare", "clinical", "diagnosis", "prescription"
        ],
        IndustryType.FINANCE: [
            "金融", "银行", "支付", "理财", "保险", "证券", "投资",
            "贷款", "信用卡", "转账", "风控", "合规", "反洗钱",
            "finance", "bank", "payment", "insurance", "investment",
            "trading", "risk", "compliance", "aml"
        ],
        IndustryType.EDUCATION: [
            "教育", "学校", "学生", "教师", "课程", "考试", "学习",
            "培训", "在线", "课堂", "作业", "成绩", "校园",
            "education", "school", "student", "teacher", "course",
            "learning", "training", "classroom", "academic"
        ],
        IndustryType.ECOMMERCE: [
            "电商", "商品", "订单", "购物车", "支付", "物流", "库存",
            "促销", "优惠券", "会员", "商家", "平台", "SKU",
            "ecommerce", "shop", "product", "order", "cart",
            "payment", "shipping", "inventory", "merchant"
        ]
    }

    # 内置模板库
    TEMPLATES: Dict[str, IndustryTemplate] = {
        "medical_slide_lending": IndustryTemplate(
            id="medical_slide_lending",
            name="病理切片借阅平台",
            industry=IndustryType.MEDICAL,
            description="医疗病理切片借阅管理系统",
            keywords=["切片", "病理", "玻片", "借阅", "归还", "数字切片"],
            compliance_requirements=[
                ComplianceRequirement(
                    name="等保三级合规",
                    description="符合国家信息安全等级保护三级要求",
                    category="security",
                    priority="critical",
                    checklist=[
                        "身份鉴别机制（双因素认证）",
                        "访问控制策略（RBAC权限模型）",
                        "安全审计功能（操作日志完整记录）",
                        "数据完整性保护（传输和存储加密）",
                        "数据备份恢复机制"
                    ]
                ),
                ComplianceRequirement(
                    name="患者隐私保护",
                    description="遵守《个人信息保护法》和医疗数据隐私规定",
                    category="privacy",
                    priority="critical",
                    checklist=[
                        "患者身份信息脱敏处理",
                        "敏感操作二次确认",
                        "数据最小化原则（只收集必要信息）",
                        "隐私政策明确告知",
                        "患者授权机制"
                    ]
                ),
                ComplianceRequirement(
                    name="医疗数据安全",
                    description="确保医疗数据的机密性、完整性和可用性",
                    category="security",
                    priority="critical",
                    checklist=[
                        "数据分类分级管理",
                        "敏感数据加密存储（AES-256）",
                        "数据传输TLS加密",
                        "数据访问日志记录",
                        "数据保留期限管理"
                    ]
                ),
                ComplianceRequirement(
                    name="操作审计追踪",
                    description="完整的操作审计和追踪机制",
                    category="audit",
                    priority="high",
                    checklist=[
                        "用户操作全程记录",
                        "数据修改留痕",
                        "审计日志不可篡改",
                        "异常行为告警",
                        "定期审计报告"
                    ]
                ),
                ComplianceRequirement(
                    name="跨院区数据同步",
                    description="多院区场景下的数据一致性",
                    category="security",
                    priority="high",
                    checklist=[
                        "院区间数据隔离",
                        "跨院区授权机制",
                        "数据同步冲突处理",
                        "离线模式支持",
                        "数据一致性校验"
                    ]
                )
            ],
            workflow_enhancements={
                "mandatory_agents": ["compliance_checker"],
                "agent_order": {
                    "compliance_checker": 0  # 在PRD生成前执行合规检查
                },
                "additional_context": {
                    "medical_specific": True,
                    "requires_privacy_review": True,
                    "multi_hospital_support": True
                }
            },
            agent_prompts={
                "prd_generator": """
你是医疗行业PRD专家。生成PRD时必须包含以下医疗合规章节：

## 7. 合规与安全要求

### 7.1 等保三级合规
- 身份鉴别：双因素认证机制
- 访问控制：基于角色的权限管理（RBAC）
- 安全审计：完整的操作日志和审计追踪
- 数据安全：传输和存储加密

### 7.2 患者隐私保护
- 患者身份信息脱敏显示
- 敏感操作二次确认机制
- 数据最小化原则
- 患者授权和撤销机制

### 7.3 数据安全
- 敏感数据AES-256加密存储
- 数据传输TLS 1.3加密
- 数据分类分级管理
- 数据保留和销毁策略

### 7.4 审计要求
- 用户操作全程记录
- 审计日志不可篡改
- 定期合规检查
- 异常行为告警

参考文档：
- 病案复印平台经验（线上申请-审核-快递流程）
- 医疗产品合规检查清单
""",
                "compliance_checker": """
你是医疗行业合规专家。检查以下内容是否符合医疗行业要求：

强制检查项：
1. 等保三级合规
   - [ ] 身份鉴别机制
   - [ ] 访问控制策略
   - [ ] 安全审计功能
   - [ ] 数据加密保护

2. 患者隐私保护
   - [ ] 身份信息脱敏
   - [ ] 敏感操作确认
   - [ ] 数据最小化
   - [ ] 患者授权机制

3. 数据安全
   - [ ] 加密存储
   - [ ] 传输加密
   - [ ] 访问控制
   - [ ] 日志记录

4. 多院区适配（如适用）
   - [ ] 院区数据隔离
   - [ ] 跨院区授权
   - [ ] 数据同步机制

5. 操作审计
   - [ ] 全程操作记录
   - [ ] 修改留痕
   - [ ] 日志保护

输出格式：
- 合规状态：通过/需改进/不通过
- 详细检查项及结果
- 改进建议（如有）
"""
            },
            mandatory_checks=[
                "等保三级合规检查",
                "患者隐私保护检查",
                "数据安全检查",
                "操作审计检查",
                "跨院区适配检查（如适用）"
            ]
        ),

        "medical_admin_system": IndustryTemplate(
            id="medical_admin_system",
            name="医疗管理后台",
            industry=IndustryType.MEDICAL,
            description="医院管理后台系统",
            keywords=["管理后台", "医院管理", "科室管理", "医生管理", "权限管理"],
            compliance_requirements=[
                ComplianceRequirement(
                    name="权限管理",
                    description="严格的RBAC权限管理体系",
                    category="security",
                    priority="critical",
                    checklist=[
                        "基于角色的权限控制（RBAC）",
                        "最小权限原则",
                        "权限继承和委派",
                        "敏感操作审批流程",
                        "权限变更审计"
                    ]
                ),
                ComplianceRequirement(
                    name="操作审计",
                    description="完整的操作审计机制",
                    category="audit",
                    priority="critical",
                    checklist=[
                        "用户登录登出记录",
                        "数据增删改查记录",
                        "配置变更记录",
                        "异常操作告警",
                        "审计日志定期归档"
                    ]
                ),
                ComplianceRequirement(
                    name="数据报表",
                    description="医疗数据统计和报表",
                    category="security",
                    priority="high",
                    checklist=[
                        "数据统计脱敏",
                        "报表访问权限控制",
                        "敏感数据导出审批",
                        "报表水印保护",
                        "数据使用追踪"
                    ]
                ),
                ComplianceRequirement(
                    name="多院区管理",
                    description="多院区场景下的管理",
                    category="security",
                    priority="high",
                    checklist=[
                        "院区数据隔离",
                        "跨院区权限控制",
                        "统一管理和分院自治",
                        "数据同步机制",
                        "院区间协作流程"
                    ]
                )
            ],
            workflow_enhancements={
                "mandatory_agents": ["compliance_checker"],
                "additional_context": {
                    "medical_specific": True,
                    "focus_on_permissions": True,
                    "multi_hospital_support": True
                }
            },
            agent_prompts={
                "prd_generator": """
你是医疗管理后台PRD专家。生成PRD时必须重点关注：

## 核心模块

### 1. 权限管理模块
- RBAC权限模型设计
- 角色定义（超级管理员、院区管理员、科室管理员、普通用户）
- 权限粒度控制（菜单、按钮、数据字段）
- 权限审批流程

### 2. 操作审计模块
- 操作日志记录（谁、何时、做了什么）
- 日志查询和筛选
- 异常操作告警
- 审计报告生成

### 3. 数据报表模块
- 医疗数据统计
- 运营数据分析
- 报表权限控制
- 数据导出管理

### 4. 多院区管理（如适用）
- 院区基础信息管理
- 跨院区数据查看权限
- 院区间数据同步
- 统一配置管理

## 合规要求
- 等保三级合规
- 操作全程可审计
- 敏感数据保护
- 权限最小化原则
""",
                "compliance_checker": """
你是医疗管理后台合规专家。重点检查：

1. 权限管理
   - [ ] RBAC模型实现
   - [ ] 最小权限原则
   - [ ] 权限审批流程
   - [ ] 权限变更审计

2. 操作审计
   - [ ] 全操作记录
   - [ ] 审计日志保护
   - [ ] 异常告警机制
   - [ ] 定期审计报告

3. 数据安全
   - [ ] 敏感数据保护
   - [ ] 数据导出控制
   - [ ] 报表权限管理
   - [ ] 数据使用追踪

4. 多院区管理（如适用）
   - [ ] 院区数据隔离
   - [ ] 跨院区权限控制
   - [ ] 数据同步安全
"""
            },
            mandatory_checks=[
                "权限管理检查",
                "操作审计检查",
                "数据报表安全检查",
                "多院区管理检查（如适用）"
            ]
        )
    }

    def __init__(self):
        """初始化模板系统"""
        self._custom_templates: Dict[str, IndustryTemplate] = {}

    def detect_industry(self, text: str) -> IndustryType:
        """
        检测文本所属行业

        Args:
            text: 输入文本

        Returns:
            检测到的行业类型
        """
        text_lower = text.lower()
        scores = {}

        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[industry] = score

        if not scores:
            return IndustryType.UNKNOWN

        return max(scores, key=scores.get)

    def match_template(
        self,
        text: str,
        industry: Optional[IndustryType] = None
    ) -> Optional[IndustryTemplate]:
        """
        匹配最合适的模板

        Args:
            text: 输入文本
            industry: 已知行业类型（可选）

        Returns:
            匹配的模板或None
        """
        if industry is None:
            industry = self.detect_industry(text)

        if industry == IndustryType.UNKNOWN:
            return None

        # 计算每个模板的匹配分数
        best_match = None
        best_score = 0

        all_templates = {**self.TEMPLATES, **self._custom_templates}

        for template in all_templates.values():
            if template.industry != industry:
                continue

            score = sum(1 for kw in template.keywords if kw.lower() in text.lower())

            if score > best_score:
                best_score = score
                best_match = template

        # 如果指定了行业但没有匹配到关键词，返回该行业的第一个模板
        if best_match is None and industry != IndustryType.UNKNOWN:
            for template in all_templates.values():
                if template.industry == industry:
                    return template

        return best_match

    def apply_template_to_plan(
        self,
        template: IndustryTemplate,
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将模板应用到任务计划

        Args:
            template: 行业模板
            plan: 原始任务计划

        Returns:
            增强后的任务计划
        """
        enhanced_plan = plan.copy()

        # 添加合规要求
        enhanced_plan["compliance_requirements"] = [
            {
                "name": req.name,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "checklist": req.checklist
            }
            for req in template.compliance_requirements
        ]

        # 添加强制检查项
        enhanced_plan["mandatory_checks"] = template.mandatory_checks

        # 添加工作流增强
        enhanced_plan["workflow_enhancements"] = template.workflow_enhancements

        # 添加Agent提示词增强
        enhanced_plan["agent_prompts"] = template.agent_prompts

        # 添加模板元数据
        enhanced_plan["template_info"] = {
            "id": template.id,
            "name": template.name,
            "industry": template.industry.value,
            "description": template.description
        }

        return enhanced_plan

    def enhance_agent_prompt(
        self,
        template: IndustryTemplate,
        agent_name: str,
        base_prompt: str
    ) -> str:
        """
        增强Agent提示词

        Args:
            template: 行业模板
            agent_name: Agent名称
            base_prompt: 基础提示词

        Returns:
            增强后的提示词
        """
        if agent_name not in template.agent_prompts:
            return base_prompt

        industry_prompt = template.agent_prompts[agent_name]

        return f"""{base_prompt}

=== 行业特定要求 ===
{industry_prompt}
"""

    def get_compliance_checklist(
        self,
        template: IndustryTemplate,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取合规检查清单

        Args:
            template: 行业模板
            category: 按类别筛选（可选）

        Returns:
            检查清单列表
        """
        requirements = template.compliance_requirements

        if category:
            requirements = [r for r in requirements if r.category == category]

        return [
            {
                "name": req.name,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "checklist": req.checklist
            }
            for req in requirements
        ]

    def register_custom_template(self, template: IndustryTemplate):
        """
        注册自定义模板

        Args:
            template: 自定义模板
        """
        self._custom_templates[template.id] = template

    def list_templates(
        self,
        industry: Optional[IndustryType] = None
    ) -> List[Dict[str, Any]]:
        """
        列出所有模板

        Args:
            industry: 按行业筛选（可选）

        Returns:
            模板列表
        """
        all_templates = {**self.TEMPLATES, **self._custom_templates}

        templates = list(all_templates.values())
        if industry:
            templates = [t for t in templates if t.industry == industry]

        return [
            {
                "id": t.id,
                "name": t.name,
                "industry": t.industry.value,
                "description": t.description,
                "keywords": t.keywords
            }
            for t in templates
        ]

    def get_template(self, template_id: str) -> Optional[IndustryTemplate]:
        """
        获取指定模板

        Args:
            template_id: 模板ID

        Returns:
            模板或None
        """
        all_templates = {**self.TEMPLATES, **self._custom_templates}
        return all_templates.get(template_id)


# 全局模板系统实例
_template_system: Optional[TemplateSystem] = None


def get_template_system() -> TemplateSystem:
    """获取全局模板系统实例"""
    global _template_system
    if _template_system is None:
        _template_system = TemplateSystem()
    return _template_system
