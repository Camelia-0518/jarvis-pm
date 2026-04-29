#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能模板系统

自动检测行业类型并应用专用模板
"""

import json
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# 合规规则配置目录
COMPLIANCE_RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compliance_rules")


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

    # 内置模板库（医疗行业 2 个核心模板，其他行业由 compliance_rules/ 外部 JSON 扩展）
    TEMPLATES: Dict[str, IndustryTemplate] = {
        "medical_slide_lending": IndustryTemplate(
            id="medical_slide_lending",
            name="病理切片借阅平台",
            industry=IndustryType.MEDICAL,
            description="病理切片/玻片借阅与归还管理平台，覆盖申请、审批、出借、归还、数字切片全流程",
            keywords=[
                "切片", "病理", "玻片", "借阅", "归还", "数字切片",
                "病理科", "切片申请", "切片归还", "切片溯源",
                "数字病理", "切片扫描", "玻片管理", "切片库",
                "slide", "pathology", "lending"
            ],
            compliance_requirements=[
                ComplianceRequirement(
                    name="等保三级合规",
                    description="符合国家信息安全等级保护三级要求（GB/T 22239-2019），适用于病理切片借阅这类涉及医疗核心数据的系统",
                    category="security",
                    priority="critical",
                    checklist=[
                        "身份鉴别机制（双因素认证）",
                        "访问控制策略（RBAC权限模型）",
                        "安全审计功能（操作日志完整记录）",
                        "数据完整性保护（传输和存储加密）",
                        "数据备份恢复机制",
                    ],
                ),
                ComplianceRequirement(
                    name="患者隐私保护",
                    description="切片关联的患者身份信息必须严格脱敏，遵守《个人信息保护法》《数据安全法》和医疗数据隐私规定",
                    category="privacy",
                    priority="critical",
                    checklist=[
                        "切片标签去标识化（脱敏患者ID/姓名/身份证）",
                        "敏感操作二次确认（外借/归还/销毁）",
                        "数据最小化原则（仅展示必要的临床信息）",
                        "患者授权与撤销机制",
                        "隐私政策明确告知",
                    ],
                ),
                ComplianceRequirement(
                    name="医疗数据安全",
                    description="确保病理切片数字图像、临床诊断数据的机密性、完整性和可用性",
                    category="security",
                    priority="critical",
                    checklist=[
                        "数据分类分级管理（核心切片图像/临床诊断/一般元数据）",
                        "数字切片图像加密存储（AES-256）",
                        "切片数据传输TLS加密",
                        "切片访问日志记录",
                        "数据保留期限与销毁策略（符合《医疗机构病历管理规定》）",
                    ],
                ),
                ComplianceRequirement(
                    name="操作审计追踪",
                    description="完整的切片借阅、归还、扫描、查看操作审计，满足医疗行业监管和回溯调查要求",
                    category="audit",
                    priority="high",
                    checklist=[
                        "切片借阅全程记录（借阅人、时间、用途、归还期限）",
                        "切片状态变更留痕（在库/出借/归还/损坏/销毁）",
                        "审计日志防篡改保护（WORM存储）",
                        "异常行为告警（逾期未还、批量借阅、非常规时段访问）",
                        "定期审计报告生成",
                    ],
                ),
                ComplianceRequirement(
                    name="切片溯源管理",
                    description="病理切片实物与数字切片的全生命周期溯源，避免切片丢失、错配、损坏",
                    category="security",
                    priority="high",
                    checklist=[
                        "切片唯一编号与二维码/RFID绑定",
                        "切片入库/出借/归还自动登记",
                        "切片实物状态与数字记录一致性校验",
                        "多院区切片调阅授权链",
                        "切片销毁审批与监销流程",
                    ],
                ),
            ],
            workflow_enhancements={
                "mandatory_agents": ["compliance_checker"],
                "additional_context": {
                    "medical_specific": True,
                    "requires_privacy_review": True,
                    "slide_traceability": True,
                },
            },
            agent_prompts={
                "prd_generator": """你是医疗行业PRD专家，拥有10年以上三甲医院病理科信息系统设计经验，曾主导多家医院的病案复印平台经验、切片借阅平台、数字病理系统建设。

## 病理切片借阅平台PRD写作要点
- **流程导向**：以「病理科医生申请→主任审批→切片库管员出借→借阅人取片→使用→归还→入库」为主线
- **合规前置**：必须在「背景与目标」之后说明等保三级合规要求和患者隐私保护要求
- **角色细化**：必须区分「病理科医生」「切片库管员」「会诊专家」「教学使用者」「外院借阅人」
- **异常场景必须覆盖**：切片损坏、逾期未还、跨院区调阅、切片销毁等

## 必须覆盖的章节
1. 背景与目标（含政策依据：等保三级、《医疗机构病历管理规定》）
2. 用户故事（按角色分组，含业务规则和异常场景）
3. 业务流程（申请→审批→出借→归还→盘点）
4. 功能规格（切片管理、借阅管理、归还管理、数字切片、配置管理）
5. 数据需求（切片元数据模型、患者数据脱敏规则）
6. 合规要求（等保三级合规、患者隐私保护、医疗数据安全、切片溯源管理）
7. 数据埋点（借阅时长、逾期率、切片利用率）
8. 里程碑（含等保测评、UAT节点）

## 病理切片特殊要求
- 数字切片图像通常 GB 级，必须考虑「分块加载」和「带宽优化」
- 切片实物必须有「唯一物理标识」（二维码/RFID）与数字记录绑定
- 跨院区调阅必须有「双向授权链」和「数据回收机制」
- 教学/科研使用必须做「数据脱敏」并申请「专门授权」
""",
                "compliance_checker": """你是医疗行业合规专家。请对病理切片借阅平台进行合规检查：

强制检查项：
1. 等保三级合规
   - [ ] 身份鉴别机制（双因素认证）
   - [ ] 访问控制策略（RBAC）
   - [ ] 安全审计功能
   - [ ] 数据加密保护（传输+存储）
   - [ ] 备份恢复机制

2. 患者隐私保护
   - [ ] 切片标签去标识化
   - [ ] 敏感操作二次确认
   - [ ] 数据最小化原则
   - [ ] 患者授权与撤销机制

3. 医疗数据安全
   - [ ] 切片图像加密存储（AES-256）
   - [ ] 传输加密（TLS）
   - [ ] 访问日志记录
   - [ ] 保留期限与销毁策略

4. 操作审计追踪
   - [ ] 借阅全程记录
   - [ ] 状态变更留痕
   - [ ] 审计日志防篡改
   - [ ] 异常行为告警

5. 切片溯源管理
   - [ ] 切片唯一编号绑定
   - [ ] 出借/归还自动登记
   - [ ] 实物与数字记录一致性
   - [ ] 销毁审批与监销

输出格式：
- 合规状态：通过 / 需改进 / 不通过
- 各检查项详细结果
- 改进建议
""",
            },
            mandatory_checks=[
                "等保三级合规检查",
                "患者隐私保护检查",
                "医疗数据安全检查",
                "操作审计追踪检查",
                "切片溯源管理检查",
            ],
        ),

        "medical_admin_system": IndustryTemplate(
            id="medical_admin_system",
            name="医疗管理后台",
            industry=IndustryType.MEDICAL,
            description="医疗信息化管理后台系统，覆盖挂号、缴费、病案、对账、多院区等核心业务模块",
            keywords=[
                "医院管理", "医疗后台", "管理后台",
                "挂号", "缴费", "病案", "对账", "多院区",
                "HIS", "门诊", "住院", "科室管理",
                "权限", "角色", "审批", "运维",
                "admin", "hospital management",
            ],
            compliance_requirements=[
                ComplianceRequirement(
                    name="权限管理",
                    description="基于医疗业务场景的精细化权限管理，确保不同角色只能访问授权的业务模块和数据",
                    category="security",
                    priority="critical",
                    checklist=[
                        "基于角色的权限控制（RBAC）",
                        "最小权限原则",
                        "敏感操作审批流程",
                        "权限变更审计",
                        "离职人员权限自动回收",
                    ],
                ),
                ComplianceRequirement(
                    name="操作审计",
                    description="管理后台所有运维和业务操作必须可审计、可追溯",
                    category="audit",
                    priority="critical",
                    checklist=[
                        "用户操作全程记录（操作人、时间、内容、结果）",
                        "数据修改留痕（旧值/新值/修改人/时间）",
                        "审计日志防篡改保护",
                        "异常行为告警（高频访问、批量导出等）",
                        "定期审计报告生成",
                    ],
                ),
                ComplianceRequirement(
                    name="医疗数据安全",
                    description="管理后台访问的患者数据、财务数据必须满足医疗行业数据安全要求",
                    category="security",
                    priority="high",
                    checklist=[
                        "数据分类分级管理",
                        "敏感数据加密存储（AES-256）",
                        "数据传输TLS加密",
                        "数据导出脱敏",
                        "数据保留期限与销毁策略",
                    ],
                ),
                ComplianceRequirement(
                    name="跨院区数据管理",
                    description="多院区场景下的数据隔离、同步与协作管理",
                    category="security",
                    priority="high",
                    checklist=[
                        "院区之间数据隔离",
                        "跨院区授权与访问控制",
                        "数据同步冲突处理机制",
                        "离线模式与数据一致性校验",
                        "院区间协作流程规范",
                    ],
                ),
            ],
            workflow_enhancements={
                "mandatory_agents": ["compliance_checker"],
                "additional_context": {
                    "medical_specific": True,
                    "multi_hospital_support": True,
                    "admin_console": True,
                },
            },
            agent_prompts={
                "prd_generator": """你是医疗行业PRD专家，拥有10年以上医疗信息化管理后台设计经验。

## 医疗管理后台PRD写作要点
- 必须覆盖核心模块：挂号、缴费、病案、对账、多院区
- 必须区分「平台运维」「业务管理」「业务执行」三层角色
- 必须设计「权限矩阵」（角色 × 模块 × 操作）
- 必须设计「审计日志查询」与「合规报表」
- 必须考虑「跨院区」场景的数据隔离与协作

## 必须覆盖的章节
1. 背景与目标（含等保三级合规要求）
2. 用户故事（平台运维、医院管理员、业务执行）
3. 业务流程（挂号→缴费→病案→对账）
4. 功能规格（按模块拆解）
5. 数据需求（多院区数据模型）
6. 合规要求（权限管理、操作审计、医疗数据安全）
7. 数据埋点（运维健康度、业务效率）
8. 里程碑（含等保测评节点）
""",
                "compliance_checker": """你是医疗行业合规专家。请对医疗管理后台进行合规检查：

1. 权限管理
   - [ ] RBAC权限模型
   - [ ] 最小权限原则
   - [ ] 敏感操作审批
   - [ ] 离职人员权限回收

2. 操作审计
   - [ ] 全程操作记录
   - [ ] 数据修改留痕
   - [ ] 审计日志防篡改
   - [ ] 异常行为告警

3. 医疗数据安全
   - [ ] 数据加密存储
   - [ ] 传输加密
   - [ ] 数据导出脱敏

4. 跨院区数据管理
   - [ ] 院区数据隔离
   - [ ] 跨院区授权
   - [ ] 同步冲突处理
""",
            },
            mandatory_checks=[
                "权限管理检查",
                "操作审计检查",
                "医疗数据安全检查",
                "跨院区数据管理检查",
            ],
        ),
    }

    def __init__(self):
        """初始化模板系统"""
        self._custom_templates: Dict[str, IndustryTemplate] = {}
        self._external_rules: Dict[str, dict] = {}
        self._rules_load_time: float = 0.0
        self._load_external_rules()

    def _load_external_rules(self):
        """从 JSON 配置文件加载合规规则"""
        if not os.path.isdir(COMPLIANCE_RULES_DIR):
            return
        loaded = 0
        for filename in os.listdir(COMPLIANCE_RULES_DIR):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(COMPLIANCE_RULES_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                industry = data.get("industry")
                if industry:
                    self._external_rules[industry] = data
                    loaded += 1
            except Exception:
                continue
        self._rules_load_time = os.path.getmtime(COMPLIANCE_RULES_DIR) if os.path.exists(COMPLIANCE_RULES_DIR) else 0.0
        if loaded > 0:
            print(f"[TemplateSystem] 已加载 {loaded} 个外部合规规则配置")

    def _needs_reload(self) -> bool:
        """检查合规规则目录是否有更新，需要热重载"""
        if not os.path.isdir(COMPLIANCE_RULES_DIR):
            return False
        try:
            current_mtime = os.path.getmtime(COMPLIANCE_RULES_DIR)
            for filename in os.listdir(COMPLIANCE_RULES_DIR):
                if filename.endswith(".json"):
                    fpath = os.path.join(COMPLIANCE_RULES_DIR, filename)
                    current_mtime = max(current_mtime, os.path.getmtime(fpath))
            return current_mtime > self._rules_load_time
        except Exception:
            return False

    def _ensure_rules_loaded(self):
        """确保规则已加载（支持热更新）"""
        if self._needs_reload():
            self._external_rules.clear()
            self._load_external_rules()

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

        # 计算每个模板的匹配分数（包含外部配置模板）
        best_match = None
        best_score = 0

        all_templates = {**self.TEMPLATES, **self._custom_templates, **self._get_external_templates()}

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
        all_templates = {**self.TEMPLATES, **self._custom_templates, **self._get_external_templates()}

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

    def _build_template_from_external(self, rule_data: dict, template_def: dict) -> IndustryTemplate:
        """从外部 JSON 规则数据构建 IndustryTemplate"""
        industry_str = rule_data.get("industry", "unknown")
        try:
            industry = IndustryType(industry_str)
        except ValueError:
            industry = IndustryType.UNKNOWN

        reqs = template_def.get("compliance_requirements", [])
        compliance_requirements = [
            ComplianceRequirement(
                name=r.get("name", ""),
                description=r.get("description", ""),
                category=r.get("category", "security"),
                priority=r.get("priority", "medium"),
                checklist=r.get("checklist", []),
            )
            for r in reqs
        ]

        return IndustryTemplate(
            id=template_def.get("id", ""),
            name=template_def.get("name", ""),
            industry=industry,
            description=template_def.get("description", ""),
            keywords=template_def.get("keywords", []),
            compliance_requirements=compliance_requirements,
            workflow_enhancements={"from_external_config": True},
            agent_prompts=template_def.get("agent_prompts", {}),
            mandatory_checks=template_def.get("mandatory_checks", []),
        )

    def _get_external_templates(self) -> Dict[str, IndustryTemplate]:
        """获取所有外部配置模板（支持热更新）"""
        self._ensure_rules_loaded()
        external: Dict[str, IndustryTemplate] = {}
        for industry, rule_data in self._external_rules.items():
            for template_def in rule_data.get("templates", []):
                tid = template_def.get("id")
                if tid:
                    external[tid] = self._build_template_from_external(rule_data, template_def)
        return external

    def get_template(self, template_id: str) -> Optional[IndustryTemplate]:
        """
        获取指定模板（优先外部配置，支持热更新）

        Args:
            template_id: 模板ID

        Returns:
            模板或None
        """
        # 优先从外部配置查找（支持热更新覆盖内置模板）
        external = self._get_external_templates()
        if template_id in external:
            return external[template_id]
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
