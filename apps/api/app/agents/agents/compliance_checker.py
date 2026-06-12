#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合规检查 Agent

针对医疗行业进行合规性检查
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

from ..base import BaseAgent, AgentResult, AgentState


class ComplianceChecker(BaseAgent):
    """
    合规检查 Agent

    针对医疗信息化产品进行合规性检查：
    - 等保三级要求
    - 医疗数据隐私保护
    - 患者信息安全
    - 法规政策符合性
    """

    name = "compliance_checker"
    description = "检查医疗产品合规性，识别风险和整改建议"
    version = "1.0.0"
    capabilities = [
        "compliance_check",
        "risk_assessment",
        "regulatory_analysis"
    ]

    # 医疗合规检查清单
    COMPLIANCE_ITEMS = {
        "data_security": {
            "name": "数据安全",
            "items": [
                {"id": "DS-001", "name": "患者数据加密存储", "severity": "critical"},
                {"id": "DS-002", "name": "传输层加密(HTTPS/TLS)", "severity": "critical"},
                {"id": "DS-003", "name": "数据访问日志记录", "severity": "high"},
                {"id": "DS-004", "name": "数据备份与恢复机制", "severity": "high"},
                {"id": "DS-005", "name": "敏感数据脱敏显示", "severity": "high"}
            ]
        },
        "access_control": {
            "name": "访问控制",
            "items": [
                {"id": "AC-001", "name": "身份认证机制(双因素认证)", "severity": "critical"},
                {"id": "AC-002", "name": "角色权限分离(RBAC)", "severity": "critical"},
                {"id": "AC-003", "name": "会话超时机制", "severity": "high"},
                {"id": "AC-004", "name": "密码复杂度策略", "severity": "medium"}
            ]
        },
        "privacy_protection": {
            "name": "隐私保护",
            "items": [
                {"id": "PP-001", "name": "患者知情同意", "severity": "critical"},
                {"id": "PP-002", "name": "数据使用目的限制", "severity": "critical"},
                {"id": "PP-003", "name": "数据最小化原则", "severity": "high"},
                {"id": "PP-004", "name": "患者数据查看/导出权", "severity": "high"},
                {"id": "PP-005", "name": "数据保留期限策略", "severity": "medium"}
            ]
        },
        "audit_trail": {
            "name": "审计追溯",
            "items": [
                {"id": "AT-001", "name": "操作日志完整性", "severity": "critical"},
                {"id": "AT-002", "name": "日志防篡改机制", "severity": "critical"},
                {"id": "AT-003", "name": "审计日志保留时间(≥6个月)", "severity": "high"}
            ]
        },
        "business_continuity": {
            "name": "业务连续性",
            "items": [
                {"id": "BC-001", "name": "系统高可用设计", "severity": "high"},
                {"id": "BC-002", "name": "灾难恢复计划", "severity": "high"},
                {"id": "BC-003", "name": "应急响应机制", "severity": "medium"}
            ]
        }
    }

    # 医疗行业特殊要求
    MEDICAL_REQUIREMENTS = [
        {
            "id": "MR-001",
            "name": "等保三级认证",
            "description": "必须通过国家信息安全等级保护三级认证",
            "severity": "critical"
        },
        {
            "id": "MR-002",
            "name": "医疗器械软件注册",
            "description": "如涉及诊断功能，需进行医疗器械软件注册",
            "severity": "high"
        },
        {
            "id": "MR-003",
            "name": "网络安全等级保护",
            "description": "符合《网络安全法》和《数据安全法》要求",
            "severity": "critical"
        },
        {
            "id": "MR-004",
            "name": "个人信息保护法合规",
            "description": "符合《个人信息保护法》要求",
            "severity": "critical"
        },
        {
            "id": "MR-005",
            "name": "电子病历管理规范",
            "description": "符合《电子病历应用管理规范》",
            "severity": "high"
        }
    ]

    SYSTEM_PROMPT = """你是医疗信息化合规专家。检查产品是否符合：
1. 等保三级要求
2. 医疗数据隐私保护法规
3. 患者信息安全规范
4. 网络安全法、数据安全法、个人信息保护法

输出详细的合规检查报告，包含风险等级和整改建议。"""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行合规检查

        Args:
            input_data: 包含 product_name, industry, features

        Returns:
            AgentResult: 包含合规检查报告
        """
        product_name = input_data.get("product_name", "")
        industry = input_data.get("industry", "")
        features = input_data.get("features", [])

        # 步骤1: 基础合规检查
        step1 = self._create_step("basic_check", "基础合规检查")
        basic_results = self._check_basic_compliance()
        self._complete_step(step1, f"检查 {len(basic_results)} 项基础要求")

        # 步骤2: 医疗行业特殊检查
        step2 = self._create_step("medical_check", "医疗行业特殊要求")
        medical_results = self._check_medical_requirements(features)
        self._complete_step(step2, f"检查 {len(medical_results)} 项医疗要求")

        # 步骤3: 功能特性风险分析
        step3 = self._create_step("feature_risk", "功能特性风险分析")
        feature_risks = await self._analyze_feature_risks(features)
        self._complete_step(step3, f"分析 {len(feature_risks)} 个功能风险")

        # 步骤4: 生成整改建议
        step4 = self._create_step("recommendations", "生成整改建议")
        all_issues = basic_results + medical_results + feature_risks
        recommendations = self._generate_recommendations(all_issues)
        self._complete_step(step4, f"生成 {len(recommendations)} 条建议")

        # 步骤5: 生成报告
        step5 = self._create_step("generate_report", "生成合规报告")
        report = self._generate_report(
            product_name=product_name,
            industry=industry,
            basic_results=basic_results,
            medical_results=medical_results,
            feature_risks=feature_risks,
            recommendations=recommendations
        )
        self._complete_step(step5, f"报告长度: {len(report)} 字符")

        # 计算合规得分
        total_items = len(all_issues)
        passed_items = sum(1 for i in all_issues if i.get("status") == "pass")
        compliance_score = (passed_items / total_items * 100) if total_items > 0 else 0

        return AgentResult(
            success=True,
            output=report,
            data={
                "compliance_score": round(compliance_score, 2),
                "total_items": total_items,
                "passed_items": passed_items,
                "failed_items": total_items - passed_items,
                "critical_issues": len([i for i in all_issues if i.get("severity") == "critical"]),
                "recommendations": recommendations
            },
            execution_time=self.elapsed_seconds
        )

    def _check_basic_compliance(self) -> List[Dict[str, Any]]:
        """基础合规检查"""
        results = []

        for category, data in self.COMPLIANCE_ITEMS.items():
            for item in data["items"]:
                results.append({
                    "id": item["id"],
                    "category": data["name"],
                    "name": item["name"],
                    "severity": item["severity"],
                    "status": "unknown",  # 实际使用时需要检查系统配置
                    "description": f"需要检查{item['name']}的实现情况"
                })

        return results

    def _check_medical_requirements(self, features: List[str]) -> List[Dict[str, Any]]:
        """检查医疗行业特殊要求"""
        results = []

        for req in self.MEDICAL_REQUIREMENTS:
            results.append({
                "id": req["id"],
                "category": "医疗特殊要求",
                "name": req["name"],
                "description": req["description"],
                "severity": req["severity"],
                "status": "unknown"
            })

        return results

    async def _analyze_feature_risks(self, features: List[str]) -> List[Dict[str, Any]]:
        """分析功能特性风险"""
        risks = []

        prompt = f"""分析以下医疗产品功能的安全和合规风险：

功能列表: {json.dumps(features, ensure_ascii=False)}

请识别：
1. 涉及敏感数据的功能
2. 需要特殊权限的功能
3. 潜在的隐私风险点

输出JSON格式：
{{
    "risks": [
        {{
            "feature": "功能名称",
            "risk": "风险描述",
            "severity": "critical/high/medium/low",
            "mitigation": "缓解措施"
        }}
    ]
}}"""

        try:
            response = await self._call_llm(prompt=prompt)
            data = json.loads(response)
            for risk in data.get("risks", []):
                risks.append({
                    "id": f"FR-{len(risks)+1:03d}",
                    "category": "功能风险",
                    "name": risk.get("feature", ""),
                    "description": risk.get("risk", ""),
                    "severity": risk.get("severity", "medium"),
                    "mitigation": risk.get("mitigation", ""),
                    "status": "unknown"
                })
        except Exception:
            logger.warning("Failed to parse compliance risk from LLM output", exc_info=True)

        return risks

    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成整改建议"""
        recommendations = []

        # 按严重程度分组
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        high_issues = [i for i in issues if i.get("severity") == "high"]

        if critical_issues:
            recommendations.append({
                "priority": "P0-立即处理",
                "title": "关键合规缺陷整改",
                "description": f"存在 {len(critical_issues)} 个关键合规缺陷，必须在上线前完成整改",
                "actions": [f"整改: {i['name']}" for i in critical_issues[:5]],
                "timeline": "1-2周"
            })

        if high_issues:
            recommendations.append({
                "priority": "P1-尽快处理",
                "title": "高风险项整改",
                "description": f"存在 {len(high_issues)} 个高风险项，建议尽快整改",
                "actions": [f"整改: {i['name']}" for i in high_issues[:5]],
                "timeline": "2-4周"
            })

        recommendations.append({
            "priority": "P2-持续改进",
            "title": "安全体系建设",
            "description": "建立完善的安全管理体系，通过等保三级认证",
            "actions": [
                "制定安全管理制度",
                "开展安全培训",
                "定期安全审计",
                "建立应急响应机制"
            ],
            "timeline": "3-6个月"
        })

        return recommendations

    def _generate_report(
        self,
        product_name: str,
        industry: str,
        basic_results: List[Dict],
        medical_results: List[Dict],
        feature_risks: List[Dict],
        recommendations: List[Dict]
    ) -> str:
        """生成合规检查报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        all_issues = basic_results + medical_results + feature_risks
        critical_count = len([i for i in all_issues if i.get("severity") == "critical"])
        high_count = len([i for i in all_issues if i.get("severity") == "high"])

        report = f"""# 合规检查报告

---
generated_at: {timestamp}
agent: {self.name} v{self.version}
---

## 检查对象

- **产品名称**: {product_name}
- **行业领域**: {industry or "医疗信息化"}
- **检查时间**: {timestamp}

## 合规评分

| 指标 | 数值 | 状态 |
|------|------|------|
| 关键缺陷 | {critical_count} | {"🔴 需要立即整改" if critical_count > 0 else "🟢 通过"} |
| 高风险项 | {high_count} | {"🟡 需要关注" if high_count > 0 else "🟢 通过"} |

## 检查范围

### 1. 数据安全 ({len([i for i in basic_results if i['category'] == '数据安全'])} 项)

| 编号 | 检查项 | 严重程度 | 状态 |
|------|--------|----------|------|
"""

        for item in basic_results:
            if item["category"] == "数据安全":
                status_icon = "❓" if item["status"] == "unknown" else ("✅" if item["status"] == "pass" else "❌")
                report += f"| {item['id']} | {item['name']} | {item['severity']} | {status_icon} |\n"

        report += """
### 2. 访问控制

| 编号 | 检查项 | 严重程度 | 状态 |
|------|--------|----------|------|
"""

        for item in basic_results:
            if item["category"] == "访问控制":
                status_icon = "❓" if item["status"] == "unknown" else ("✅" if item["status"] == "pass" else "❌")
                report += f"| {item['id']} | {item['name']} | {item['severity']} | {status_icon} |\n"

        report += """
### 3. 医疗行业特殊要求

| 编号 | 要求 | 说明 | 严重程度 |
|------|------|------|----------|
"""

        for item in medical_results:
            report += f"| {item['id']} | {item['name']} | {item['description'][:30]}... | {item['severity']} |\n"

        if feature_risks:
            report += """
### 4. 功能特性风险

| 功能 | 风险描述 | 严重程度 |
|------|----------|----------|
"""
            for risk in feature_risks[:10]:
                report += f"| {risk['name']} | {risk['description'][:40]}... | {risk['severity']} |\n"

        report += """
## 整改建议

"""

        for rec in recommendations:
            report += f"""### {rec['priority']}: {rec['title']}

{rec['description']}

**建议措施**:
"""
            for action in rec['actions']:
                report += f"- {action}\n"

            report += f"""
**时间要求**: {rec['timeline']}

---

"""

        report += """
## 法规参考

1. 《网络安全法》
2. 《数据安全法》
3. 《个人信息保护法》
4. 《信息安全技术 网络安全等级保护基本要求》(GB/T 22239-2019)
5. 《电子病历应用管理规范》
6. 《医疗健康数据安全指南》

---

*报告由 Jarvis PM Agent 系统自动生成，仅供参考，具体合规要求请咨询专业合规顾问。*
"""

        return report