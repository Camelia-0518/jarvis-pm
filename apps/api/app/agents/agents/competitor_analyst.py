#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞品分析 Agent

搜索竞品信息并进行分析
"""

import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState
from ..llm_client import create_default_client
from ..tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class CompetitorAnalyst(BaseAgent):
    """
    竞品分析 Agent

    搜索竞品信息，分析优缺点，生成竞品分析报告
    """

    name = "competitor_analyst"
    description = "搜索并分析竞品，提取优缺点和市场定位"
    version = "1.0.0"
    capabilities = [
        "competitor_search",
        "market_analysis",
        "feature_comparison"
    ]
    required_tools = ["web_search", "web_crawler"]

    SYSTEM_PROMPT = """你是竞品分析专家。搜索并分析竞品信息，提取：
1. 竞品基本信息（名称、定位、目标用户）
2. 核心功能对比
3. 优缺点分析
4. 市场策略
5. 可借鉴点

输出结构化报告，使用 Markdown 格式。"""

    def __init__(self, llm_client=None, **kwargs):
        super().__init__(
            llm_client=llm_client or create_default_client(),
            **kwargs
        )
        self.tool_registry = ToolRegistry()

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行竞品分析

        Args:
            input_data: 包含 product_name, industry, keywords

        Returns:
            AgentResult: 包含竞品分析报告
        """
        start_time = datetime.now()
        self._set_state(AgentState.RUNNING)

        try:
            product_name = input_data.get("product_name", "")
            industry = input_data.get("industry", "")
            keywords = input_data.get("keywords", [])

            # 步骤1: 搜索竞品
            step1 = self._create_step("search_competitors", "搜索竞品")
            competitors = await self._search_competitors(
                product_name, industry, keywords
            )
            self._complete_step(step1, f"找到 {len(competitors)} 个竞品")

            # 步骤2: 获取竞品详情
            step2 = self._create_step("analyze_details", "分析竞品详情")
            detailed_analysis = []
            for competitor in competitors[:3]:  # 只分析前3个
                analysis = await self._analyze_competitor(competitor)
                detailed_analysis.append(analysis)
            self._complete_step(step2, f"分析了 {len(detailed_analysis)} 个竞品")

            # 步骤3: 生成对比分析
            step3 = self._create_step("generate_comparison", "生成对比分析")
            comparison = await self._generate_comparison(detailed_analysis)
            self._complete_step(step3, "对比分析完成")

            # 步骤4: 生成报告
            step4 = self._create_step("generate_report", "生成报告")
            report = self._generate_report(
                product_name=product_name,
                industry=industry,
                competitors=detailed_analysis,
                comparison=comparison
            )
            self._complete_step(step4, f"报告长度: {len(report)} 字符")

            execution_time = (datetime.now() - start_time).total_seconds()
            self._set_state(AgentState.COMPLETED)

            return AgentResult(
                success=True,
                output=report,
                data={
                    "competitors": detailed_analysis,
                    "comparison": comparison,
                    "report_length": len(report)
                },
                execution_time=execution_time
            )

        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def _search_competitors(
        self,
        product_name: str,
        industry: str,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """搜索竞品信息"""
        # 构建搜索查询
        search_queries = [
            f"{product_name} 竞品",
            f"{product_name} 竞争对手",
            f"{industry} 同类产品"
        ]
        if keywords:
            search_queries.append(f"{' '.join(keywords[:2])} 平台")

        competitors = []

        # 获取 web_search 工具
        web_search_tool = self.tool_registry.create_instance("web_search")

        if web_search_tool:
            for query in search_queries[:2]:
                try:
                    result = await web_search_tool.execute(query=query, limit=5)
                    if result.success:
                        competitors.extend(result.data.get("results", []))
                except Exception as e:
                    logger.error(f"Search error: {e}")

        # 如果搜索失败或没有工具，使用模拟数据
        if not competitors:
            competitors = self._get_mock_competitors(product_name, industry)

        return competitors

    async def _analyze_competitor(self, competitor: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个竞品"""
        name = competitor.get("name", "Unknown")
        url = competitor.get("url", "")

        # 尝试获取更多信息
        details = {
            "name": name,
            "url": url,
            "description": competitor.get("description", ""),
            "features": [],
            "strengths": [],
            "weaknesses": [],
            "target_users": "",
            "pricing": ""
        }

        # 使用 LLM 分析
        prompt = f"""分析以下竞品信息：

竞品名称: {name}
描述: {details['description']}
URL: {url}

请分析并输出 JSON：
{{
    "features": ["功能1", "功能2"],
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "target_users": "目标用户描述",
    "pricing": "定价策略"
}}"""

        try:
            response = await self._call_llm(prompt=prompt)
            analysis = json.loads(response)
            details.update(analysis)
        except Exception:
            pass

        return details

    async def _generate_comparison(
        self,
        competitors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成竞品对比"""
        if len(competitors) < 2:
            return {"message": "竞品数量不足，无法生成对比"}

        # 提取所有功能
        all_features = set()
        for c in competitors:
            all_features.update(c.get("features", []))

        # 生成功能对比矩阵
        feature_matrix = {}
        for feature in all_features:
            feature_matrix[feature] = {}
            for c in competitors:
                has_feature = feature in c.get("features", [])
                feature_matrix[feature][c["name"]] = "✓" if has_feature else "✗"

        return {
            "feature_matrix": feature_matrix,
            "competitor_count": len(competitors),
            "summary": "竞品功能对比完成"
        }

    def _generate_report(
        self,
        product_name: str,
        industry: str,
        competitors: List[Dict[str, Any]],
        comparison: Dict[str, Any]
    ) -> str:
        """生成竞品分析报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# 竞品分析报告

---
generated_at: {timestamp}
agent: {self.name} v{self.version}
---

## 分析对象

- **产品**: {product_name}
- **行业**: {industry}
- **分析时间**: {timestamp}

## 竞品列表

"""

        for i, c in enumerate(competitors, 1):
            report += f"""### {i}. {c['name']}

**网址**: {c.get('url', 'N/A')}

**描述**: {c.get('description', '暂无描述')}

**目标用户**: {c.get('target_users', '未明确')}

**核心功能**:
"""
            for feature in c.get('features', [])[:5]:
                report += f"- {feature}\n"

            report += f"""
**优势**:
"""
            for strength in c.get('strengths', [])[:3]:
                report += f"- {strength}\n"

            report += f"""
**劣势**:
"""
            for weakness in c.get('weaknesses', [])[:3]:
                report += f"- {weakness}\n"

            report += "\n---\n\n"

        # 添加对比总结
        report += """## 对比总结

### 功能对比

"""
        feature_matrix = comparison.get("feature_matrix", {})
        if feature_matrix:
            # 表头
            competitor_names = list(competitors[i]["name"] for i in range(len(competitors)))
            report += "| 功能 | " + " | ".join(competitor_names) + " |\n"
            report += "|" + "---|" * (len(competitor_names) + 1) + "\n"

            # 数据行
            for feature, values in list(feature_matrix.items())[:10]:
                row = f"| {feature} |"
                for name in competitor_names:
                    row += f" {values.get(name, '-')} |"
                report += row + "\n"

        report += f"""
## 建议

基于以上分析，建议：

1. **差异化定位**: 找到与竞品的差异化优势
2. **功能补充**: 补齐竞品缺失的核心功能
3. **用户体验**: 在易用性上超越竞品
4. **定价策略**: 根据竞品定价制定合理策略

---

*报告由 Jarvis PM Agent 系统自动生成*
"""

        return report

    def _get_mock_competitors(
        self,
        product_name: str,
        industry: str
    ) -> List[Dict[str, Any]]:
        """获取模拟竞品数据（当搜索失败时使用）"""
        return [
            {
                "name": "竞品A",
                "description": f"{industry}领域的主流解决方案",
                "url": "https://example-a.com"
            },
            {
                "name": "竞品B",
                "description": "新兴的创新型产品",
                "url": "https://example-b.com"
            },
            {
                "name": "竞品C",
                "description": "大型企业级解决方案",
                "url": "https://example-c.com"
            }
        ]
