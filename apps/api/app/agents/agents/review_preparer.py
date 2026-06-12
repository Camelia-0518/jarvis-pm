#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评审准备 Agent

准备评审材料、风险评估和预设问答
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState


class ReviewPreparer(BaseAgent):
    """
    评审准备 Agent

    为产品评审会议准备材料：
    - 评审材料汇总
    - 风险分析
    - 预设问答
    - 决策建议
    """

    name = "review_preparer"
    description = "准备评审材料、风险分析和预设问答"
    version = "1.0.0"
    capabilities = [
        "review_preparation",
        "risk_analysis",
        "qa_preparation",
        "decision_support"
    ]

    SYSTEM_PROMPT = """你是评审准备专家。为产品评审会议准备完整的材料：

1. 材料汇总 - 整理所有相关文档
2. 风险分析 - 识别潜在风险和应对策略
3. 预设问答 - 预判评审委员会可能提出的问题
4. 决策建议 - 给出明确的通过/修改/暂缓建议

输出结构化的评审材料。"""

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行评审准备

        Args:
            input_data: 包含 product_name, prd_content, analysis_results等

        Returns:
            AgentResult: 包含评审材料
        """
        product_name = input_data.get("product_name", "")
        prd_content = input_data.get("prd_content", "")
        analysis_results = input_data.get("analysis_results", {})
        competitor_analysis = input_data.get("competitor_analysis", "")
        compliance_report = input_data.get("compliance_report", "")

        # 步骤1: 汇总材料
        step1 = self._create_step("material_summary", "汇总评审材料")
        materials = self._summarize_materials(
            product_name, prd_content, analysis_results,
            competitor_analysis, compliance_report
        )
        self._complete_step(step1, f"汇总 {len(materials)} 类材料")

        # 步骤2: 风险分析
        step2 = self._create_step("risk_analysis", "风险分析")
        risks = await self._analyze_risks(
            product_name, prd_content, compliance_report
        )
        self._complete_step(step2, f"识别 {len(risks)} 个风险点")

        # 步骤3: 预设问答
        step3 = self._create_step("prepare_qa", "预设问答")
        qa_list = await self._prepare_qa(
            product_name, prd_content, analysis_results
        )
        self._complete_step(step3, f"准备 {len(qa_list)} 个问答")

        # 步骤4: 决策建议
        step4 = self._create_step("decision_recommendation", "决策建议")
        recommendation = self._generate_recommendation(
            materials, risks, qa_list
        )
        self._complete_step(step4, f"建议: {recommendation['decision']}")

        # 步骤5: 生成评审材料
        step5 = self._create_step("generate_materials", "生成评审材料")
        review_package = self._generate_review_package(
            product_name=product_name,
            materials=materials,
            risks=risks,
            qa_list=qa_list,
            recommendation=recommendation
        )
        self._complete_step(step5, "评审材料生成完成")

        return AgentResult(
            success=True,
            output=review_package,
            data={
                "product_name": product_name,
                "material_count": len(materials),
                "risk_count": len(risks),
                "qa_count": len(qa_list),
                "recommendation": recommendation,
                "package_length": len(review_package)
            },
            execution_time=self.elapsed_seconds
        )

    def _summarize_materials(
        self,
        product_name: str,
        prd_content: str,
        analysis_results: Dict,
        competitor_analysis: str,
        compliance_report: str
    ) -> List[Dict[str, Any]]:
        """汇总评审材料"""
        materials = []

        if prd_content:
            materials.append({
                "type": "prd",
                "name": "产品需求文档",
                "description": f"{product_name} PRD",
                "size": len(prd_content),
                "status": "已完成"
            })

        if analysis_results:
            materials.append({
                "type": "analysis",
                "name": "需求分析报告",
                "description": "用户需求和痛点分析",
                "status": "已完成"
            })

        if competitor_analysis:
            materials.append({
                "type": "competitor",
                "name": "竞品分析报告",
                "description": "竞品对比分析",
                "status": "已完成"
            })

        if compliance_report:
            materials.append({
                "type": "compliance",
                "name": "合规检查报告",
                "description": "合规性和风险评估",
                "status": "已完成"
            })

        return materials

    async def _analyze_risks(
        self,
        product_name: str,
        prd_content: str,
        compliance_report: str
    ) -> List[Dict[str, Any]]:
        """分析风险"""
        risks = []

        # 从技术风险、业务风险、合规风险三个维度分析
        prompt = f"""分析产品 "{product_name}" 的潜在风险：

PRD摘要: {prd_content[:1000]}...

请从以下维度分析风险：
1. 技术风险 - 技术可行性、性能、安全
2. 业务风险 - 市场接受度、竞争、收益
3. 合规风险 - 法规、政策、数据安全

输出JSON格式：
{{
    "risks": [
        {{
            "category": "技术/业务/合规",
            "description": "风险描述",
            "probability": "高/中/低",
            "impact": "高/中/低",
            "mitigation": "缓解措施"
        }}
    ]
}}"""

        try:
            response = await self._call_llm(prompt=prompt)
            data = json.loads(response)
            for risk in data.get("risks", []):
                risks.append(risk)
        except Exception:
            # 使用默认风险列表
            risks = [
                {
                    "category": "技术",
                    "description": "开发周期可能延长",
                    "probability": "中",
                    "impact": "中",
                    "mitigation": "预留缓冲时间，分阶段交付"
                },
                {
                    "category": "业务",
                    "description": "用户接受度不确定",
                    "probability": "中",
                    "impact": "高",
                    "mitigation": "早期用户验证，MVP快速迭代"
                },
                {
                    "category": "合规",
                    "description": "医疗合规要求高",
                    "probability": "高",
                    "impact": "高",
                    "mitigation": "提前进行合规审查，咨询专业顾问"
                }
            ]

        return risks

    async def _prepare_qa(
        self,
        product_name: str,
        prd_content: str,
        analysis_results: Dict
    ) -> List[Dict[str, Any]]:
        """准备预设问答"""
        prompt = f"""为产品 "{product_name}" 的评审会准备问答：

基于以下信息，预判评审委员会可能提出的问题：

产品: {product_name}
PRD摘要: {prd_content[:1500]}...

请准备8-10个常见问答，覆盖：
1. 产品价值和市场定位
2. 技术方案和可行性
3. 资源投入和排期
4. 风险和应对措施

输出JSON格式：
{{
    "qa": [
        {{
            "question": "问题",
            "answer": "建议回答",
            "category": "类别",
            "priority": "高/中/低"
        }}
    ]
}}"""

        try:
            response = await self._call_llm(prompt=prompt)
            data = json.loads(response)
            return data.get("qa", [])
        except Exception:
            return []

    def _generate_recommendation(
        self,
        materials: List[Dict],
        risks: List[Dict],
        qa_list: List[Dict]
    ) -> Dict[str, Any]:
        """生成决策建议"""
        # 根据风险等级判断
        high_risks = [r for r in risks if r.get("impact") == "高"]
        critical_risks = [r for r in risks if r.get("probability") == "高" and r.get("impact") == "高"]

        if critical_risks:
            decision = "暂缓评审"
            reason = f"存在 {len(critical_risks)} 个关键风险，建议先解决后再评审"
        elif high_risks:
            decision = "有条件通过"
            reason = f"可以通过，但需关注 {len(high_risks)} 个高风险点"
        else:
            decision = "建议通过"
            reason = "材料完整，风险可控，建议通过评审"

        return {
            "decision": decision,
            "reason": reason,
            "conditions": ["完成风险缓解措施"] if high_risks else [],
            "next_steps": [
                "组织评审会议",
                "准备演示环境",
                "邀请相关方参与"
            ]
        }

    def _generate_review_package(
        self,
        product_name: str,
        materials: List[Dict],
        risks: List[Dict],
        qa_list: List[Dict],
        recommendation: Dict
    ) -> str:
        """生成评审材料包"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        package = f"""# 评审材料包

---
product: {product_name}
generated_at: {timestamp}
agent: {self.name} v{self.version}
---

## 一、材料清单

| 序号 | 材料类型 | 材料名称 | 状态 |
|------|----------|----------|------|
"""

        for i, m in enumerate(materials, 1):
            package += f"| {i} | {m['type']} | {m['name']} | {m['status']} |\n"

        package += f"""
## 二、风险评估

### 风险汇总

| 类别 | 描述 | 概率 | 影响 | 缓解措施 |
|------|------|------|------|----------|
"""

        for risk in risks:
            package += f"| {risk['category']} | {risk['description'][:30]}... | {risk['probability']} | {risk['impact']} | {risk['mitigation'][:20]}... |\n"

        package += f"""
### 风险矩阵

- 高风险项: {len([r for r in risks if r.get('impact') == '高'])} 个
- 中风险项: {len([r for r in risks if r.get('impact') == '中'])} 个
- 低风险项: {len([r for r in risks if r.get('impact') == '低'])} 个

## 三、预设问答

"""

        # 按优先级排序
        sorted_qa = sorted(qa_list, key=lambda x: {"高": 0, "中": 1, "低": 2}.get(x.get("priority", "中"), 1))

        for i, qa in enumerate(sorted_qa[:10], 1):
            package += f"""### Q{i}: {qa['question']}

**类别**: {qa.get('category', '一般')}

**建议回答**:
{qa['answer']}

---

"""

        package += f"""## 四、评审建议

### 决策建议

**{recommendation['decision']}**

{recommendation['reason']}

### 前提条件

"""

        for condition in recommendation.get("conditions", []):
            package += f"- [ ] {condition}\n"

        package += f"""
### 后续步骤

"""

        for i, step in enumerate(recommendation.get("next_steps", []), 1):
            package += f"{i}. {step}\n"

        package += """
## 五、评审会议安排建议

### 参会人员

- **必需**: 产品经理、技术负责人、业务负责人
- **建议**: 合规顾问、安全专家、用户体验设计师

### 会议议程（建议 60 分钟）

1. **产品介绍** (10分钟) - 产品经理
2. **技术方案** (15分钟) - 技术负责人
3. **风险分析** (10分钟) - 合规/安全专家
4. **讨论问答** (20分钟) - 全体
5. **决策总结** (5分钟) - 主持人

### 决策选项

评审委员会可选择：

- ✅ **通过** - 可以进入开发阶段
- 🟡 **有条件通过** - 需完成指定修改后启动
- 🔴 **暂缓** - 需重大调整后再评审

---

*评审材料由 Jarvis PM Agent 系统自动生成*
"""

        return package