#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞品分析 Agent

搜索竞品信息并进行分析
支持用户确认模式：LLM推断的竞品需用户确认后才生成正式报告
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
    支持用户确认模式：当网络搜索不可用时，LLM推断的竞品标记为"候选"，
    需用户勾选确认后再生成正式报告。
    """

    name = "competitor_analyst"
    description = "搜索并分析竞品，提取优缺点和市场定位"
    version = "2.0.0"
    capabilities = [
        "competitor_search",
        "market_analysis",
        "feature_comparison",
        "candidate_confirmation"
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
        执行竞品分析（步骤1：搜索/推断竞品）

        如果所有竞品来自网络搜索 -> 直接生成完整报告
        如果部分/全部来自 LLM 推断 -> 返回候选模式，需用户确认

        Args:
            input_data: 包含 product_name, industry, keywords

        Returns:
            AgentResult:
                - 正常模式: output=完整报告, data.needs_confirmation=False
                - 候选模式: output=候选提示, data.needs_confirmation=True, data.candidates=候选列表
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

            # 区分已验证和候选竞品
            verified = [c for c in competitors if c.get("source") == "web_search"]
            candidates = [c for c in competitors if c.get("source") == "llm_inferred"]

            # 如果存在候选竞品（LLM推断），进入用户确认模式
            if candidates:
                self._set_state(AgentState.WAITING_FOR_INPUT)
                candidate_preview = self._generate_candidate_preview(
                    product_name=product_name,
                    industry=industry,
                    verified=verified,
                    candidates=candidates
                )
                return AgentResult(
                    success=True,
                    output=candidate_preview,
                    data={
                        "needs_confirmation": True,
                        "verified_count": len(verified),
                        "candidates": candidates,
                        "verified": verified,
                        "product_name": product_name,
                        "industry": industry,
                        "keywords": keywords,
                        "message": "检测到以下竞品基于 LLM 推断生成，请勾选确认后再生成正式报告。",
                    },
                    execution_time=(datetime.now() - start_time).total_seconds()
                )

            # 全部已验证 -> 直接生成完整报告
            return await self._generate_full_report(
                product_name=product_name,
                industry=industry,
                competitors=competitors,
                start_time=start_time
            )

        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def confirm_competitors(
        self,
        product_name: str,
        industry: str,
        keywords: List[str],
        confirmed_candidates: List[Dict[str, Any]],
        verified: List[Dict[str, Any]]
    ) -> AgentResult:
        """
        用户确认候选竞品后，生成正式竞品分析报告

        Args:
            product_name: 产品名称
            industry: 行业
            keywords: 关键词
            confirmed_candidates: 用户确认的候选竞品列表
            verified: 已验证的竞品列表

        Returns:
            AgentResult: 完整竞品分析报告
        """
        start_time = datetime.now()
        self._set_state(AgentState.RUNNING)

        try:
            # 合并已验证和已确认的候选竞品
            all_competitors = verified + confirmed_candidates

            if not all_competitors:
                return AgentResult(
                    success=False,
                    error="没有可用的竞品数据，请至少确认一个竞品。",
                    execution_time=(datetime.now() - start_time).total_seconds()
                )

            return await self._generate_full_report(
                product_name=product_name,
                industry=industry,
                competitors=all_competitors,
                start_time=start_time
            )

        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def _generate_full_report(
        self,
        product_name: str,
        industry: str,
        competitors: List[Dict[str, Any]],
        start_time: Optional[datetime] = None
    ) -> AgentResult:
        """生成完整竞品分析报告"""
        if start_time is None:
            start_time = datetime.now()

        # 步骤2: 获取竞品详情
        step2 = self._create_step("analyze_details", "分析竞品详情")
        detailed_analysis = []
        for competitor in competitors[:5]:  # 最多分析5个
            analysis = await self._analyze_competitor(competitor)
            detailed_analysis.append(analysis)
        self._complete_step(step2, f"分析了 {len(detailed_analysis)} 个竞品")

        # 步骤3: 生成对比分析
        step3 = self._create_step("generate_comparison", "生成对比分析")
        comparison = await self._generate_comparison(detailed_analysis)
        self._complete_step(step3, "对比分析完成")

        # 步骤4: 生成报告
        step4 = self._create_step("generate_report", "生成报告")
        report = self._generate_formal_report(
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
                "report_length": len(report),
                "needs_confirmation": False,
                "confirmed": True,
            },
            execution_time=execution_time
        )

    async def _search_competitors(
        self,
        product_name: str,
        industry: str,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """搜索竞品信息，区分已验证和候选来源"""
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
                        for item in result.data.get("results", []):
                            item["source"] = "web_search"
                            competitors.append(item)
                except Exception as e:
                    logger.error(f"Search error: {e}")

        # 如果搜索失败或没有工具，让 LLM 基于已知信息推断竞品
        if not competitors:
            inferred = await self._llm_analyze_competitors(product_name, industry, keywords)
            for item in inferred:
                item["source"] = "llm_inferred"
                competitors.append(item)

        return competitors

    async def _analyze_competitor(self, competitor: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个竞品"""
        name = competitor.get("name", "Unknown")
        url = competitor.get("url", "")
        source = competitor.get("source", "unknown")

        details = {
            "name": name,
            "url": url,
            "description": competitor.get("description", ""),
            "source": source,
            "features": [],
            "strengths": [],
            "weaknesses": [],
            "target_users": "",
            "pricing": ""
        }

        prompt = f"""分析以下竞品信息：

竞品名称: {name}
描述: {details['description']}
URL: {url}
信息来源: {"网络搜索" if source == "web_search" else "LLM推断"}

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

        all_features = set()
        for c in competitors:
            all_features.update(c.get("features", []))

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

    def _generate_formal_report(
        self,
        product_name: str,
        industry: str,
        competitors: List[Dict[str, Any]],
        comparison: Dict[str, Any]
    ) -> str:
        """生成正式竞品分析报告（所有竞品已确认）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# 竞品分析报告

> ✅ **数据可信度说明**：本报告中的竞品信息已通过用户确认，可作为分析参考。建议结合最新市场动态进行决策。

---
generated_at: {timestamp}
agent: {self.name} v{self.version}
---

## 分析对象

- **产品**: {product_name}
- **行业**: {industry}
- **分析时间**: {timestamp}
- **竞品来源**: {"网络搜索 + 用户确认" if any(c.get('source') == 'llm_inferred' for c in competitors) else "网络搜索"}

## 竞品列表

"""

        for i, c in enumerate(competitors, 1):
            source_tag = "🔍 已验证" if c.get("source") == "web_search" else "✅ 已确认"
            report += f"""### {i}. {c['name']} {source_tag}

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
            competitor_names = list(competitors[i]["name"] for i in range(len(competitors)))
            report += "| 功能 | " + " | ".join(competitor_names) + " |\n"
            report += "|" + "---|" * (len(competitor_names) + 1) + "\n"

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

    def _generate_candidate_preview(
        self,
        product_name: str,
        industry: str,
        verified: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]]
    ) -> str:
        """生成候选竞品预览（供用户确认）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        preview = f"""# 竞品分析 — 候选确认

> ⏳ **等待用户确认**：由于网络搜索未返回结果，以下竞品由 LLM 基于知识库推断生成。
> 请勾选确认准确的竞品后，系统将生成正式分析报告。

---

## 分析对象

- **产品**: {product_name}
- **行业**: {industry}
- **时间**: {timestamp}

## 数据来源

| 类型 | 数量 | 状态 |
|------|------|------|
| 网络搜索验证 | {len(verified)} | 🔍 已验证 |
| LLM 推断 | {len(candidates)} | ⏳ 待确认 |

"""

        if verified:
            preview += """## 已验证竞品

"""
            for c in verified:
                preview += f"- **{c['name']}** — {c.get('description', '暂无描述')}\n"
            preview += "\n"

        preview += """## 候选竞品（请确认）

以下竞品基于 LLM 知识库推断，可能不完全准确：

"""
        for i, c in enumerate(candidates, 1):
            preview += f"""### {i}. {c['name']}

**描述**: {c.get('description', '暂无描述')}

**推断来源**: {c.get('source_detail', 'LLM知识库/行业推断')}

**建议操作**: □ 确认纳入分析  /  □ 排除

---

"""

        preview += """## 下一步

请确认以上候选竞品后，系统将继续：
1. 获取每个竞品的详细信息
2. 生成功能对比矩阵
3. 输出完整分析报告

---

*候选列表由 Jarvis PM Agent 系统自动生成*
"""

        return preview

    async def _llm_analyze_competitors(
        self,
        product_name: str,
        industry: str,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """当搜索不可用时，让 LLM 基于其知识生成竞品列表（标记为候选）"""
        prompt = f"""请基于你的产品知识，分析 "{product_name}" 在 {industry} 行业的主要竞品。

关键词: {', '.join(keywords) if keywords else '无'}

要求：
1. 列出 2-4 个真实或代表性的竞品名称
2. 对每个竞品提供：名称、定位描述、核心特点
3. 必须明确标注哪些是真实已知产品，哪些是基于行业特征的代表性推断
4. 不要编造虚假 URL 或具体数据

以 JSON 数组格式返回：
[{{"name": "竞品名称", "description": "定位和描述", "url": "", "source_detail": "LLM知识库推断/行业特征推断"}}]

注意：如果你不确定具体产品名称，请诚实说明。"""

        try:
            response = await self._call_llm(prompt=prompt, system_prompt=self.SYSTEM_PROMPT)
            data = json.loads(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "competitors" in data:
                return data["competitors"]
            return []
        except Exception as e:
            logger.warning(f"LLM 竞品分析失败: {e}")
            return []
