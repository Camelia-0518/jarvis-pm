#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能模板系统

自动检测行业类型并应用专用模板
"""

import json
import logging
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

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

    # PRD 通用输出规范（自动注入所有模板的 prd_generator）
    DEFAULT_PRD_GUIDELINES = """## PRD 通用输出规范（所有模板必须严格遵守）

### 章节编号格式
- 文档主标题：`# 产品名称`（不带编号）
- 一级章节标题：`## N. 标题`（如 `## 1. 背景与目标`）
- 二级章节标题：`### N.N 标题`（如 `### 1.1 市场背景`）
- 三级章节标题：`#### N.N.N 标题`（如 `#### 1.1.1 子模块`）
- **严禁出现重复编号**（如 `## 1. 1. 背景与目标`、`### 2. 2. 用户故事` 这种格式绝对禁止）

### MVP 边界定义（必须）
- 每个 PRD 必须明确区分「一期（MVP）」和「二期（迭代）」
- 每个功能点必须标注「一期」或「二期」
- 严禁模糊表述（如"后续再考虑"）

### 状态机定义（必须）
- 必须包含**状态转换图**（Mermaid 语法，使用 `stateDiagram-v2` 或 `graph TD`）
- 必须包含**状态转换表**（Markdown 表格，列：当前状态 | 目标状态 | 触发条件 | 操作人 | 时限）
- 必须定义每个状态的触发条件、操作人、时限要求

### 流程图格式（必须）
- 核心业务流程必须使用 Mermaid 或 PlantUML 泳道图
- 禁止纯文本流程描述

### 信息架构与页面设计（必须）
- 功能规格章节必须包含**信息架构图(IA)**（树状结构或层级列表）
- 必须包含**核心页面字段清单**（Markdown 表格：页面名称 | 字段名 | 类型 | 必填 | 说明）

### 用户故事验收标准（必须）
- 每个用户故事必须包含验收标准
- 优先使用 Given-When-Then 格式

### 对账规则（如涉及支付/财务，必须）
- 必须明确对账差异处理规则：长款、短款、单边账
- 必须定义每种差异的触发条件和处理流程
"""

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
                "prd_generator": """你是医疗行业PRD专家，拥有10年以上三甲医院病理科信息系统设计经验，曾主导多家医院的病案复印平台、切片借阅平台、数字病理系统建设。

## 病理切片借阅平台PRD写作要点
- **流程导向**：以「病理科医生申请→主任审批→切片库管员出借→借阅人取片→使用→归还→入库」为主线
- **合规前置**：必须在「背景与目标」之后说明等保三级合规要求和患者隐私保护要求
- **角色细化**：必须区分「病理科医生」「切片库管员」「会诊专家」「教学使用者」「外院借阅人」
- **异常场景必须覆盖**：切片损坏、逾期未还、跨院区调阅、切片销毁等

## MVP边界定义（必须明确区分一期/二期）
- **一期（MVP）**：切片管理 + 院内借阅 + 基础审批 + EMPI对接
- **二期（迭代）**：AI辅助诊断 + 患者端自助查询 + 跨院联邦查询
- 严禁模糊表述，每个功能点必须标注「一期」或「二期」

## 核心状态机定义（必须包含状态转换图+状态转换表）
1. **切片状态流转**：在库 → 已借出 → 已数字化 → 已归档
2. **借阅单状态流转**：草稿 → 待审批 → 已借出 → 已归还 → 已逾期
- 必须定义每个状态的触发条件、操作人、时限要求

## 急诊授权机制（严禁"破窗机制"）
- 急诊场景必须采用「绿色通道自动授权 + 即时审计」模式
- 严禁设计「未授权先查看、24小时内补授权」的先斩后奏流程
- 必须定义急诊授权的触发条件、自动授权范围、事后审计要求

## 费用结算规则
- 必须明确计费单元和价格锚点：
  - 数字化扫描费：按张计费
  - 会诊费：按次计费
  - 存储费：按容量计费

## 审计日志技术规范
- 审计日志必须使用 WORM存储 + 数字签名
- **严禁使用区块链技术**（与患者更正权冲突）

## 流程图格式要求
- 核心业务流程必须使用 Mermaid 或 PlantUML 泳道图
- 禁止纯文本流程描述

## 页面设计深度要求
- 功能规格章节必须包含：信息架构图(IA) + 核心页面字段清单

## 跨院区联邦查询架构
- 优先使用 API聚合 + 按需缓存 方案
- 联邦查询 + 分布式事务补偿 标记为「远期规划」

## 竞品定位分析
- 背景章节必须分析现有病理系统（朗珈/滨浦/安必平）与本系统的关系
- 明确是替代、互补还是升级关系

## 用户故事格式规范
- 每个用户故事必须包含验收标准，使用 Given-When-Then 格式

## 必须覆盖的章节
1. 背景与目标（含政策依据：等保三级 GB/T 22239-2019、《医疗机构病历管理规定》、竞品定位）
2. 用户故事（按角色分组，含业务规则、异常场景、Given-When-Then验收标准）
3. 业务流程（申请→审批→出借→归还→盘点，必须用Mermaid/PlantUML泳道图）
4. 功能规格（切片管理、借阅管理、归还管理、数字切片、配置管理；含信息架构图+核心页面字段清单）
5. 状态机定义（切片状态流转 + 借阅单状态流转，含状态转换图和转换表）
6. 数据需求（切片元数据模型、患者数据脱敏规则）
7. 费用结算（计费单元、价格锚点、结算流程）
8. 合规要求（等保三级合规、患者隐私保护、医疗数据安全、切片溯源管理、审计日志WORM+数字签名）
9. 数据埋点（借阅时长、逾期率、切片利用率）
10. 里程碑（含等保测评、UAT节点，明确一期/二期边界）

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

6. 急诊授权合规（新增）
   - [ ] 不存在"破窗机制"（未授权先查看、事后补授权）
   - [ ] 采用绿色通道自动授权 + 即时审计模式
   - [ ] 明确急诊触发条件和授权范围

7. MVP边界检查（新增）
   - [ ] 明确定义一期（切片管理+院内借阅+基础审批+EMPI）边界
   - [ ] 明确定义二期（AI辅助诊断+患者端自助+跨院联邦查询）边界
   - [ ] 每个功能点标注一期或二期

8. 状态机定义检查（新增）
   - [ ] 定义切片状态流转（在库→已借出→已数字化→已归档）
   - [ ] 定义借阅单状态流转（草稿→待审批→已借出→已归还→已逾期）
   - [ ] 包含状态转换触发条件

9. 审计技术合规（修改）
   - [ ] 使用WORM存储 + 数字签名
   - [ ] **严禁使用区块链技术**

10. 流程图可视化检查（新增）
    - [ ] 核心业务流程包含Mermaid/PlantUML泳道图
    - [ ] 禁止纯文本流程描述

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

## MVP边界定义（必须明确区分一期/二期）
- **一期（MVP）**：挂号 + 缴费 + 病案 + 对账
- **二期（迭代）**：多院区协同 + 智能分析
- 严禁模糊表述，每个功能点必须标注「一期」或「二期」

## 核心状态机定义（必须包含状态转换图+状态转换表）
1. **挂号单状态流转**：待挂号 → 已挂号 → 已就诊 → 已取消 → 已过期
2. **缴费单状态流转**：待缴费 → 部分缴费 → 已缴费 → 已退款 → 已冲正
3. **病案归档状态流转**：书写中 → 待审核 → 已归档 → 已借阅 → 已销毁
- 必须定义每个状态的触发条件、操作人、时限要求

## 权限矩阵（强制输出格式）
- 必须输出「角色 × 模块 × 操作」的权限矩阵表
- 角色至少包含：系统管理员、平台运维、医院管理员、科室主任、医生、收费员、病案管理员
- 模块至少包含：挂号管理、缴费管理、病案管理、对账管理、系统配置、报表中心
- 操作至少包含：查看、新增、编辑、删除、审核、导出、配置

## 对账规则
- 必须明确对账差异处理规则：
  - **长款**：医院多收，触发退款流程
  - **短款**：医院少收，触发补收流程
  - **单边账**：一方有记录一方无记录，触发差异调查流程

## 审计日志技术规范
- 审计日志必须使用 WORM存储 + 数字签名
- **严禁使用区块链技术**（与患者更正权冲突）

## 流程图格式要求
- 挂号→缴费→病案→对账流程必须使用 Mermaid 泳道图
- 禁止纯文本流程描述

## 多院区部署策略
- 必须区分两种部署模式及适用场景：
  - **集中式部署**：逻辑隔离，适用于同一法人的多院区集团
  - **分布式部署**：物理隔离，适用于独立法人的医联体/医共体

## 等保条款引用规范
- 引用等保条款时必须标注版本号，如 GB/T 22239-2019

## 必须覆盖的章节
1. 背景与目标（含等保三级合规要求 GB/T 22239-2019）
2. 用户故事（平台运维、医院管理员、业务执行；含Given-When-Then验收标准）
3. 业务流程（挂号→缴费→病案→对账，必须用Mermaid泳道图）
4. 功能规格（按模块拆解，含信息架构图+核心页面字段清单）
5. 状态机定义（挂号单/缴费单/病案归档状态流转，含状态转换图和转换表）
6. 权限矩阵（角色×模块×操作权限矩阵表）
7. 对账规则（长款/短款/单边账处理流程）
8. 数据需求（多院区数据模型）
9. 合规要求（权限管理、操作审计WORM+数字签名、医疗数据安全）
10. 多院区策略（集中式vs分布式部署适用场景）
11. 数据埋点（运维健康度、业务效率）
12. 里程碑（含等保测评节点，明确一期/二期边界）
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

5. 权限矩阵检查（新增）
   - [ ] 包含完整的RBAC权限矩阵（角色×模块×操作）
   - [ ] 覆盖所有核心角色和模块

6. 对账合规检查（新增）
   - [ ] 明确定义长款处理规则
   - [ ] 明确定义短款处理规则
   - [ ] 明确定义单边账处理规则
   - [ ] 对账差异处理符合财务规范

7. MVP边界检查（新增）
   - [ ] 明确定义一期（挂号+缴费+病案+对账）上线范围
   - [ ] 明确定义二期（多院区协同+智能分析）范围
   - [ ] 每个功能点标注一期或二期

8. 审计技术合规（修改）
   - [ ] 使用WORM存储 + 数字签名
   - [ ] **严禁使用区块链技术**

9. 状态机定义检查（新增）
   - [ ] 定义挂号单状态流转
   - [ ] 定义缴费单状态流转
   - [ ] 定义病案归档状态流转

10. 流程图可视化检查（新增）
    - [ ] 核心业务流程包含Mermaid泳道图
    - [ ] 禁止纯文本流程描述
""",
            },
            mandatory_checks=[
                "权限管理检查",
                "操作审计检查",
                "医疗数据安全检查",
                "跨院区数据管理检查",
            ],
        ),

        "ecommerce_platform": IndustryTemplate(
            id="ecommerce_platform",
            name="电商平台",
            industry=IndustryType.ECOMMERCE,
            description="电商平台PRD模板，覆盖核心交易链路、商品管理、库存、订单、支付、物流、促销、售后全链路",
            keywords=[
                "电商", "商品", "订单", "购物车", "支付", "物流", "库存",
                "促销", "优惠券", "会员", "商家", "平台", "SKU", "SPU",
                "秒杀", "拼团", "直播", "带货", "退换货", "对账",
                "ecommerce", "shop", "product", "order", "cart",
                "payment", "shipping", "inventory", "merchant", "retail"
            ],
            compliance_requirements=[
                ComplianceRequirement(
                    name="支付合规",
                    description="电商平台支付环节必须遵守《非银行支付机构条例》，严禁二清，需确保持牌机构合作",
                    category="legal",
                    priority="critical",
                    checklist=[
                        "支付牌照或合作持证机构资质有效",
                        "资金二清红线规避（使用电商收付通或银行存管）",
                        "支付协议与用户授权条款明确",
                        "跨境支付外汇合规",
                        "大额/高频支付风控监测",
                    ],
                ),
                ComplianceRequirement(
                    name="消费者权益保护",
                    description="遵守《消费者权益保护法》《电子商务法》，保障七日无理由退货、价格真实、评价真实",
                    category="legal",
                    priority="critical",
                    checklist=[
                        "七日无理由退货政策明示",
                        "预售/秒杀规则透明（定金、尾款、发货时间）",
                        "价格监控防止虚构原价",
                        "评价真实性保障（禁止删差评、刷单）",
                        "投诉处理48小时内响应",
                    ],
                ),
                ComplianceRequirement(
                    name="网络安全与数据安全",
                    description="遵守《网络安全法》《数据安全法》《个人信息保护法》，全链路HTTPS、数据分级、隐私控制",
                    category="security",
                    priority="critical",
                    checklist=[
                        "全链路HTTPS加密",
                        "敏感数据加密存储（AES-256）",
                        "个人信息最小必要采集",
                        "用户授权与撤回机制",
                        "数据保留期限与销毁策略",
                    ],
                ),
                ComplianceRequirement(
                    name="税务合规",
                    description="电子发票、纳税申报、代扣代缴义务",
                    category="legal",
                    priority="high",
                    checklist=[
                        "电子发票自动开具（普票/专票）",
                        "平台内经营者涉税信息报送",
                        "主播/推广者个税代扣代缴",
                        "交易记录保存至少3年",
                        "跨境交易出口退税/增值税合规",
                    ],
                ),
            ],
            workflow_enhancements={
                "mandatory_agents": ["compliance_checker"],
                "additional_context": {
                    "ecommerce_specific": True,
                    "payment_integration": True,
                    "inventory_sensitive": True,
                },
            },
            agent_prompts={
                "prd_generator": """你是电商行业PRD专家，拥有10年以上电商平台产品设计经验，曾主导过多个亿级GMV电商平台建设。

## 电商平台PRD写作要点
- 必须覆盖核心交易链路：浏览→加购→结算→支付→发货→签收→售后
- 必须区分「买家」「卖家」「平台运营」「客服」「风控」五层角色
- 必须考虑高并发场景：秒杀、大促峰值、库存超卖防护
- 必须设计「促销规则引擎」：满减、秒杀、优惠券、积分、拼团

## 核心状态机定义（必须包含状态转换图+状态转换表）
1. **订单状态流转**：待支付 → 已支付 → 待发货 → 已发货 → 已签收 → 已完成 → 已取消 → 退款中 → 已退款
2. **库存状态流转**：可售 → 预占 → 锁定 → 已出库 → 退货入库
- 必须定义每个状态的触发条件、操作人、时限要求

## 对账规则（必须明确三账差异）
- **长款**：平台多收，触发退款流程
- **短款**：平台少收，触发补收流程
- **单边账**：一方有记录一方无记录，触发差异调查流程

## 流程图格式要求
- 核心交易链路必须使用 Mermaid 泳道图（买家/卖家/平台/物流四方泳道）
- 禁止纯文本流程描述

## 必须覆盖的章节
1. 背景与目标（含市场背景、三方目标、GMV与毛利率目标）
2. 用户故事（买家/卖家/运营/客服；含Given-When-Then验收标准）
3. 业务流程（浏览→加购→结算→支付→发货→签收→售后，必须用Mermaid泳道图）
4. 功能规格（商品管理、价格体系、库存管理、订单管理、支付、物流；含信息架构图+核心页面字段清单）
5. 状态机定义（订单状态+库存状态流转，含状态转换图和转换表）
6. 对账规则（长款/短款/单边账处理流程）
7. 数据架构（订单/库存/SKU/价格/支付流水/用户行为模型）
8. 合规要求（支付牌照、消费者权益、网络安全、税务）
9. 供应链与促销策略（采购/仓储/物流/满减/秒杀/优惠券/积分/拼团）
10. 数据埋点（GMV/转化率/客单价/复购率/退货率/漏斗分析/热力图/大促监控）
11. 里程碑（明确一期/二期边界，含压测和灰度节点）

## 电商特殊要求
- 库存采用「预占+锁定+扣减+释放」四层模型，严禁超卖
- 支付采用「异步通知+主动查询」双重机制，防止掉单
- 促销规则引擎需支持多规则叠加，优先级：秒杀价 > 限时折扣 > 会员价 > 优惠券 > 满减
- 大促期间需支持静态资源CDN、API网关熔断、业务降级
- 物流需集成电子面单、轨迹查询、异常预警
""",
                "compliance_checker": """你是电商行业合规专家。请对电商平台进行合规检查：

1. 支付合规
   - [ ] 支付牌照或合作持证机构资质有效
   - [ ] 规避资金二清（使用电商收付通或银行存管）
   - [ ] 支付协议与用户授权条款明确
   - [ ] 大额/高频支付风控监测

2. 消费者权益保护
   - [ ] 七日无理由退货政策明示
   - [ ] 预售/秒杀规则透明
   - [ ] 价格监控防止虚构原价
   - [ ] 评价真实性保障

3. 网络安全与数据安全
   - [ ] 全链路HTTPS加密
   - [ ] 敏感数据加密存储
   - [ ] 个人信息最小必要采集
   - [ ] 用户授权与撤回机制

4. 税务合规
   - [ ] 电子发票自动开具
   - [ ] 交易记录保存至少3年
   - [ ] 主播/推广者个税代扣代缴

5. 订单状态机检查（新增）
   - [ ] 定义订单状态流转（待支付→已支付→待发货→已发货→已签收→已完成→已取消→退款中→已退款）
   - [ ] 包含状态转换触发条件和时限

6. 库存状态流转检查（新增）
   - [ ] 定义库存状态流转（可售→预占→锁定→已出库→退货入库）
   - [ ] 包含每层状态的触发条件和释放规则

7. 对账合规检查（新增）
   - [ ] 明确定义长款处理规则
   - [ ] 明确定义短款处理规则
   - [ ] 明确定义单边账处理规则
   - [ ] 对账差异处理符合财务规范

8. MVP边界检查（新增）
   - [ ] 明确定义一期（核心交易链路+基础售后）上线范围
   - [ ] 明确定义二期（直播/O2O/跨境/供应链金融）范围
   - [ ] 每个功能点标注一期或二期

9. 流程图可视化检查（新增）
   - [ ] 核心业务流程包含Mermaid泳道图
   - [ ] 禁止纯文本流程描述

10. 信息架构检查（新增）
    - [ ] 功能规格包含信息架构图(IA)
    - [ ] 包含核心页面字段清单
""",
            },
            mandatory_checks=[
                "支付合规检查",
                "消费者权益保护检查",
                "网络安全与数据安全检查",
                "税务合规检查",
                "订单状态机检查",
                "库存状态流转检查",
                "对账合规检查",
            ],
        ),

        "saas_product": IndustryTemplate(
            id="saas_product",
            name="SaaS产品",
            industry=IndustryType.SAAS,
            description="B2B SaaS产品PRD模板，覆盖多租户、订阅管理、权限体系、集成方案、计费规则",
            keywords=[
                "SaaS", "B2B", "订阅", "租户", "多租户", "权限",
                "集成", "API", "Webhook", "计费", "定价", "套餐",
                "管理员", "成员", "角色", "工作区", "团队",
                "saas", "subscription", "tenant", "billing", "integration"
            ],
            compliance_requirements=[
                ComplianceRequirement(
                    name="数据隔离与隐私",
                    description="多租户场景下必须确保租户间数据严格隔离，防止越权访问",
                    category="security",
                    priority="critical",
                    checklist=[
                        "租户ID贯穿所有数据层（数据库/缓存/搜索/存储）",
                        "行级隔离或独立Schema/数据库隔离",
                        "跨租户数据访问禁止",
                        "租户数据导出权限控制",
                        "数据保留期限与删除策略",
                    ],
                ),
                ComplianceRequirement(
                    name="订阅与计费合规",
                    description="订阅管理、计费规则、发票开具、退款策略需符合商业规范",
                    category="legal",
                    priority="critical",
                    checklist=[
                        "订阅状态变更可审计（开通/升级/降级/取消/续费）",
                        "计费规则透明（按座/按量/按功能/按存储）",
                        "发票自动开具与税务合规",
                        "退款策略明确（按比例/按周期）",
                        "价格变更提前通知机制",
                    ],
                ),
                ComplianceRequirement(
                    name="API安全与集成",
                    description="开放平台API需防止滥用、泄露、越权",
                    category="security",
                    priority="high",
                    checklist=[
                        "API认证（OAuth2 / API Key / JWT）",
                        "接口限流与配额管理",
                        "敏感操作二次确认",
                        "API调用日志完整记录",
                        "Webhook签名验证",
                    ],
                ),
                ComplianceRequirement(
                    name="审计与合规报表",
                    description="SaaS产品需提供审计日志和合规报表满足企业客户审计需求",
                    category="audit",
                    priority="high",
                    checklist=[
                        "用户操作全程记录",
                        "数据变更留痕（旧值/新值）",
                        "登录日志与异常告警",
                        "定期合规报告生成",
                        "数据导出留痕",
                    ],
                ),
            ],
            workflow_enhancements={
                "mandatory_agents": ["compliance_checker"],
                "additional_context": {
                    "saas_specific": True,
                    "multi_tenant": True,
                    "subscription_model": True,
                },
            },
            agent_prompts={
                "prd_generator": """你是SaaS产品PRD专家，拥有10年以上B2B SaaS产品设计经验，曾主导过多租户架构、订阅计费、企业级权限体系建设。

## SaaS产品PRD写作要点
- 必须覆盖核心模块：租户管理、用户与权限、订阅与计费、功能模块、集成方案
- 必须区分「超级管理员」「租户管理员」「普通成员」「访客」四层角色
- 必须设计「多租户隔离策略」（逻辑隔离/物理隔离/混合隔离）
- 必须设计「订阅生命周期管理」（试用→付费→续费→欠费→停用→注销）

## 核心状态机定义（必须包含状态转换图+状态转换表）
1. **租户状态流转**：注册 → 试用 → 付费 → 续费 → 欠费 → 停用 → 注销
2. **订阅状态流转**：活跃 → 升级中 → 降级中 → 取消待生效 → 已取消 → 已过期
- 必须定义每个状态的触发条件、操作人、时限要求

## 计费规则（必须明确计费单元）
- 必须明确计费单元和价格锚点：
  - 按座计费：按用户数量计费
  - 按量计费：按API调用次数/存储容量/流量计费
  - 按功能计费：按功能模块/套餐等级计费
  - 混合计费：基础套餐+超额用量计费

## 流程图格式要求
- 核心业务流程必须使用 Mermaid 泳道图
- 禁止纯文本流程描述

## 必须覆盖的章节
1. 背景与目标（含市场定位、目标客群、价值主张）
2. 用户故事（管理员/成员/访客；含Given-When-Then验收标准）
3. 业务流程（注册→试用→订阅→使用→续费/取消，必须用Mermaid泳道图）
4. 功能规格（租户管理、用户权限、核心功能、配置管理；含信息架构图+核心页面字段清单）
5. 状态机定义（租户状态+订阅状态流转，含状态转换图和转换表）
6. 计费规则（计费单元、价格锚点、套餐对比表、计费流程）
7. 多租户架构（隔离策略、数据模型、性能优化）
8. 集成方案（API设计、Webhook、SSO、第三方集成）
9. 数据安全（租户隔离、加密、备份、合规）
10. 数据埋点（活跃度、功能使用率、转化率、流失率）
11. 里程碑（明确一期/二期边界，含GTM计划）

## SaaS特殊要求
- 多租户数据隔离是核心红线，必须在数据层、缓存层、搜索层、文件存储层全部实现
- 订阅变更必须支持「立即生效」和「周期末生效」两种模式
- 计费系统需支持「预付费」和「后付费」两种模式
- 降级时必须处理超额数据（只读/删除/导出）
- 必须提供沙箱环境供客户测试集成
""",
                "compliance_checker": """你是SaaS产品合规专家。请对SaaS产品进行合规检查：

1. 数据隔离与隐私
   - [ ] 租户ID贯穿所有数据层
   - [ ] 行级隔离或独立Schema/数据库隔离
   - [ ] 跨租户数据访问禁止
   - [ ] 租户数据导出权限控制

2. 订阅与计费合规
   - [ ] 订阅状态变更可审计
   - [ ] 计费规则透明
   - [ ] 发票自动开具
   - [ ] 退款策略明确

3. API安全与集成
   - [ ] API认证机制
   - [ ] 接口限流与配额
   - [ ] 敏感操作二次确认
   - [ ] Webhook签名验证

4. 审计与合规报表
   - [ ] 用户操作全程记录
   - [ ] 数据变更留痕
   - [ ] 登录日志与异常告警

5. 租户状态机检查（新增）
   - [ ] 定义租户状态流转（注册→试用→付费→续费→欠费→停用→注销）
   - [ ] 包含状态转换触发条件和时限

6. 订阅状态机检查（新增）
   - [ ] 定义订阅状态流转（活跃→升级中→降级中→取消待生效→已取消→已过期）
   - [ ] 包含升级/降级/取消的处理规则

7. 计费规则检查（新增）
   - [ ] 明确定义计费单元（按座/按量/按功能/混合）
   - [ ] 包含价格锚点和套餐对比表

8. MVP边界检查（新增）
   - [ ] 明确定义一期（核心功能+基础租户管理）上线范围
   - [ ] 明确定义二期（高级权限/自定义字段/开放平台）范围
   - [ ] 每个功能点标注一期或二期

9. 流程图可视化检查（新增）
   - [ ] 核心业务流程包含Mermaid泳道图
   - [ ] 禁止纯文本流程描述

10. 信息架构检查（新增）
    - [ ] 功能规格包含信息架构图(IA)
    - [ ] 包含核心页面字段清单
""",
            },
            mandatory_checks=[
                "数据隔离与隐私检查",
                "订阅与计费合规检查",
                "API安全与集成检查",
                "审计与合规报表检查",
                "租户状态机检查",
                "订阅状态机检查",
                "计费规则检查",
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
            logger.info("Loaded %d external compliance rule configurations", loaded)

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
            result = base_prompt
        else:
            industry_prompt = template.agent_prompts[agent_name]
            result = f"""{base_prompt}

=== 行业特定要求 ===
{industry_prompt}
"""

        # 为 prd_generator 自动注入通用输出规范
        if agent_name == "prd_generator":
            result += f"""

=== PRD 通用输出规范 ===
{self.DEFAULT_PRD_GUIDELINES}
"""

        return result

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
