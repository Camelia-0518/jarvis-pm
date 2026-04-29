#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
需求分析 Agent

分析需求并提供结构化的需求文档
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState
from ..llm_client import create_default_client


class RequirementAgent(BaseAgent):
    """
    需求分析 Agent

    分析产品需求，提取关键信息，生成结构化的需求分析文档
    """

    name = "requirement_analyzer"
    description = "Analyze requirements and extract structured information"
    version = "1.0.0"
    capabilities = [
        "requirement_analysis",
        "user_story_extraction",
        "pain_point_identification",
        "feature_prioritization"
    ]

    # 系统提示词
    SYSTEM_PROMPT = """你是一位资深业务分析师和产品经理，专注于需求分析领域。

你的任务是：
1. 深入分析产品需求
2. 识别目标用户及其痛点
3. 提取用户故事和用例
4. 识别功能性和非功能性需求
5. 建议功能优先级
6. 识别潜在风险和约束条件

请在需要时输出结构化 JSON 格式，叙述性内容使用 Markdown 格式。

重要：所有输出必须使用中文。"""

    def __init__(self, llm_client=None, **kwargs):
        """初始化需求分析 Agent"""
        super().__init__(
            llm_client=llm_client or create_default_client(),
            **kwargs
        )

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行需求分析

        Args:
            input_data: 包含以下字段:
                - raw_requirements: 原始需求描述（文本）
                - product_name: 产品名称（可选）
                - industry: 行业领域（可选）
                - analysis_depth: 分析深度 ('basic', 'standard', 'deep')

        Returns:
            AgentResult: 包含结构化分析结果
        """
        start_time = datetime.now()
        self._set_state(AgentState.RUNNING)

        try:
            # 步骤1: 解析输入
            step1 = self._create_step("parse_input", "解析输入")
            raw_requirements = input_data.get("raw_requirements", "")
            product_name = input_data.get("product_name", "未命名产品")
            industry = input_data.get("industry", "")
            analysis_depth = input_data.get("analysis_depth", "standard")
            self._complete_step(step1, f"产品: {product_name}, 深度: {analysis_depth}")

            # 步骤2: 用户分析
            step2 = self._create_step("user_analysis", "目标用户分析")
            user_analysis = await self._analyze_users(raw_requirements, industry)
            self._complete_step(step2, f"识别用户群体: {len(user_analysis.get('user_groups', []))}")

            # 步骤3: 痛点分析
            step3 = self._create_step("pain_point_analysis", "痛点分析")
            pain_points = await self._analyze_pain_points(raw_requirements)
            self._complete_step(step3, f"识别痛点: {len(pain_points.get('pain_points', []))}")

            # 步骤4: 功能需求提取
            step4 = self._create_step("feature_extraction", "功能需求提取")
            features = await self._extract_features(raw_requirements, analysis_depth)
            self._complete_step(step4, f"提取功能: {len(features.get('features', []))}")

            # 步骤5: 用户故事生成
            step5 = self._create_step("user_stories", "用户故事生成")
            user_stories = await self._generate_user_stories(features, user_analysis)
            self._complete_step(step5, f"生成故事: {len(user_stories)}")

            # 步骤6: 优先级排序
            step6 = self._create_step("prioritization", "优先级排序")
            prioritized = await self._prioritize_features(features, pain_points)
            self._complete_step(step6, "排序完成")

            # 组装结果
            execution_time = (datetime.now() - start_time).total_seconds()

            result_data = {
                "product_name": product_name,
                "industry": industry,
                "analysis_depth": analysis_depth,
                "user_analysis": user_analysis,
                "pain_points": pain_points,
                "features": features,
                "user_stories": user_stories,
                "prioritized_features": prioritized
            }

            # 生成 Markdown 报告
            report = self._generate_report(result_data)

            self._set_state(AgentState.COMPLETED)

            return AgentResult(
                success=True,
                output=report,
                data=result_data,
                execution_time=execution_time,
                metadata={
                    "agent_name": self.name,
                    "version": self.version,
                    "steps_completed": len(self.steps)
                }
            )

        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def _analyze_users(
        self,
        requirements: str,
        industry: str
    ) -> Dict[str, Any]:
        """分析目标用户"""
        prompt = f"""分析以下需求，识别目标用户群体：

行业领域: {industry or "未指定"}

需求描述:
{requirements}

请输出以下格式的 JSON：
{{
    "target_market": "目标市场描述",
    "user_groups": [
        {{
            "name": "用户群体名称",
            "description": "描述",
            "characteristics": ["特征1", "特征2"],
            "needs": ["需求1", "需求2"]
        }}
    ],
    "primary_users": "主要用户群体",
    "secondary_users": "次要用户群体"
}}

只输出 JSON，不要其他内容。"""

        try:
            response = await self._call_llm(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            # 尝试解析 JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果解析失败，返回结构化文本
            return {
                "analysis_text": response,
                "user_groups": []
            }

    async def _analyze_pain_points(self, requirements: str) -> Dict[str, Any]:
        """分析痛点"""
        prompt = f"""分析以下需求，识别用户痛点：

{requirements}

请输出以下格式的 JSON：
{{
    "pain_points": [
        {{
            "description": "痛点描述",
            "severity": "high/medium/low",
            "frequency": "经常/偶尔/很少",
            "impact": "影响范围"
        }}
    ],
    "current_solutions": "当前解决方案及不足",
    "opportunities": ["机会点1", "机会点2"]
}}

只输出 JSON。"""

        try:
            response = await self._call_llm(prompt=prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            return {"pain_points": [], "analysis_text": response}

    async def _extract_features(
        self,
        requirements: str,
        depth: str
    ) -> Dict[str, Any]:
        """提取功能需求"""
        depth_instruction = {
            "basic": "提取核心功能即可",
            "standard": "提取核心功能和重要辅助功能",
            "deep": "全面分析，包括核心功能、辅助功能、潜在功能"
        }.get(depth, "standard")

        prompt = f"""分析以下需求，提取功能需求：

{requirements}

分析深度: {depth_instruction}

请输出以下格式的 JSON：
{{
    "features": [
        {{
            "name": "功能名称",
            "description": "功能描述",
            "category": "类别",
            "priority": "must_have/should_have/nice_to_have",
            "acceptance_criteria": ["标准1", "标准2"]
        }}
    ],
    "constraints": ["约束1", "约束2"],
    "dependencies": ["依赖1", "依赖2"]
}}

只输出 JSON。"""

        try:
            response = await self._call_llm(prompt=prompt)
            return json.loads(response)
        except json.JSONDecodeError:
            return {"features": [], "analysis_text": response}

    async def _generate_user_stories(
        self,
        features: Dict,
        user_analysis: Dict
    ) -> List[Dict[str, str]]:
        """生成用户故事"""
        prompt = f"""基于以下功能需求和用户分析，生成用户故事：

功能需求: {json.dumps(features, ensure_ascii=False)}

用户分析: {json.dumps(user_analysis, ensure_ascii=False)}

请生成用户故事，格式为 JSON：
{{
    "user_stories": [
        {{
            "role": "作为...",
            "action": "我想要...",
            "benefit": "以便...",
            "acceptance_criteria": ["标准1", "标准2"],
            "priority": "high/medium/low"
        }}
    ]
}}

只输出 JSON。"""

        try:
            response = await self._call_llm(prompt=prompt)
            data = json.loads(response)
            return data.get("user_stories", [])
        except json.JSONDecodeError:
            return []

    async def _prioritize_features(
        self,
        features: Dict,
        pain_points: Dict
    ) -> Dict[str, List]:
        """优先级排序"""
        # 简化版本：直接按优先级字段排序
        feature_list = features.get("features", [])

        prioritized = {
            "must_have": [],
            "should_have": [],
            "nice_to_have": []
        }

        for feature in feature_list:
            priority = feature.get("priority", "nice_to_have")
            if priority in prioritized:
                prioritized[priority].append(feature)
            else:
                prioritized["nice_to_have"].append(feature)

        return prioritized

    def _generate_report(self, data: Dict[str, Any]) -> str:
        """生成 Markdown 报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# 需求分析报告

---
generated_at: {timestamp}
agent: {self.name} v{self.version}
---

## 产品信息

- **产品名称**: {data.get('product_name', '未命名')}
- **行业领域**: {data.get('industry', '未指定')}
- **分析深度**: {data.get('analysis_depth', 'standard')}

## 目标用户分析

{json.dumps(data.get('user_analysis', {}), ensure_ascii=False, indent=2)}

## 痛点分析

{json.dumps(data.get('pain_points', {}), ensure_ascii=False, indent=2)}

## 功能需求

{json.dumps(data.get('features', {}), ensure_ascii=False, indent=2)}

## 用户故事

"""
        for story in data.get('user_stories', []):
            report += f"""### {story.get('role', '')}
- **动作**: {story.get('action', '')}
- **价值**: {story.get('benefit', '')}
- **优先级**: {story.get('priority', '')}

"""

        report += """## 优先级排序

### Must Have
"""
        for f in data.get('prioritized_features', {}).get('must_have', []):
            report += f"- {f.get('name')}: {f.get('description')}\n"

        report += "\n### Should Have\n"
        for f in data.get('prioritized_features', {}).get('should_have', []):
            report += f"- {f.get('name')}: {f.get('description')}\n"

        report += "\n### Nice to Have\n"
        for f in data.get('prioritized_features', {}).get('nice_to_have', []):
            report += f"- {f.get('name')}: {f.get('description')}\n"

        return report
