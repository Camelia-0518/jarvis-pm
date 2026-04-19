#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD 生成 Agent v2.0

- 自动行业检测与模板增强
- 结构化 JSON + Markdown 双输出
- 支持章节细粒度生成与上下文继承
- 内置医疗等行业合规注入
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseAgent, AgentResult, AgentState
from ..llm_client import create_default_client
from ..templates import get_template_system, IndustryType


class PRDAgent(BaseAgent):
    """
    PRD 生成 Agent

    根据输入的需求信息，生成结构化、高质量的产品需求文档。
    支持自动行业检测、模板增强、章节单独生成。
    """

    name = "prd_generator"
    description = "Generate structured Product Requirement Documents with industry-aware templates"
    version = "2.0.0"
    capabilities = [
        "prd_generation",
        "requirement_analysis",
        "document_structure",
        "industry_detection",
        "section_generation"
    ]

    # PRD 标准章节结构（与前端对齐）
    PRD_SECTIONS = [
        {"id": "background", "name": "背景与目标", "required": True},
        {"id": "user_stories", "name": "用户故事", "required": True},
        {"id": "business_flow", "name": "业务流程", "required": True},
        {"id": "functional_requirements", "name": "功能规格", "required": True},
        {"id": "data_requirements", "name": "数据需求", "required": False},
        {"id": "compliance", "name": "合规要求", "required": False},
        {"id": "analytics", "name": "数据埋点", "required": False},
        {"id": "milestones", "name": "里程碑", "required": True},
    ]

    # 基础系统提示词
    BASE_SYSTEM_PROMPT = """你是一位资深产品经理，擅长撰写可直接投入评审的产品需求文档（PRD）。

撰写原则：
1. 聚焦「用户价值」和「业务目标」，避免过度技术实现细节
2. 使用具体、可量化的描述，拒绝空泛套话
3. 每个功能必须配套用户故事和验收标准
4. 考虑主流程、异常流程、边界条件
5. 医疗/金融等行业必须包含专门的合规与数据安全章节

输出要求：
- 必须同时返回 **结构化 JSON** 和 **Markdown 文档**
- JSON 用于系统存储和前端渲染
- Markdown 用于人工阅读和导出
"""

    def __init__(self, llm_client=None, **kwargs):
        """初始化 PRD Agent"""
        super().__init__(
            llm_client=llm_client or create_default_client(),
            **kwargs
        )
        self.template_system = get_template_system()
        self._section_cache: Dict[str, str] = {}

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行 PRD 生成

        Args:
            input_data: 包含以下字段:
                - product_name: 产品名称
                - description: 产品描述
                - target_users: 目标用户
                - key_features: 核心功能列表
                - constraints: 约束条件（可选）
                - sections: 需要生成的章节列表（可选，默认全部）
                - industry: 行业类型（可选，自动检测）
                - template_id: 指定模板ID（可选）

        Returns:
            AgentResult: 包含生成的 PRD（markdown + structured）
        """
        start_time = datetime.now()
        self._set_state(AgentState.RUNNING)

        try:
            # 步骤1: 解析与标准化输入
            step1 = self._create_step("parse_input", "解析输入需求")
            ctx = self._build_context(input_data)
            self._complete_step(step1, f"解析产品: {ctx['product_name']}, 行业: {ctx['industry']}")

            # 步骤2: 行业检测与模板匹配
            step2 = self._create_step("detect_industry", "检测行业并匹配模板")
            template = self._match_template(ctx)
            ctx["template"] = template
            self._complete_step(
                step2,
                f"匹配模板: {template.name if template else '默认通用模板'}"
            )

            # 步骤3: 构建增强提示词
            step3 = self._create_step("build_prompt", "构建增强提示词")
            prompt = self._build_prompt(ctx)
            system_prompt = self._build_system_prompt(ctx)
            self._complete_step(step3, f"提示词长度: {len(prompt)} 字符")

            # 步骤4: 调用 LLM 生成
            step4 = self._create_step("generate", "生成 PRD 文档")
            raw_output = await self._call_llm(prompt=prompt, system_prompt=system_prompt)
            self._complete_step(step4, f"原始输出长度: {len(raw_output)} 字符")

            # 步骤5: 解析与后处理
            step5 = self._create_step("post_process", "解析结构化数据")
            structured, markdown = self._parse_output(raw_output, ctx)
            self._complete_step(step5, f"Markdown {len(markdown)} 字符, 提取 {len(structured.get('sections', []))} 个章节")

            execution_time = (datetime.now() - start_time).total_seconds()
            self._set_state(AgentState.COMPLETED)

            return AgentResult(
                success=True,
                output=markdown,
                data={
                    "product_name": ctx["product_name"],
                    "industry": ctx["industry"],
                    "template_id": template.id if template else None,
                    "sections_generated": [s["id"] for s in structured.get("sections", [])],
                    "content_length": len(markdown),
                    "structured": structured,
                    "markdown": markdown,
                    "user_stories": structured.get("user_stories", []),
                    "requirements": structured.get("requirements", []),
                    "compliance_items": structured.get("compliance_items", []),
                },
                execution_time=execution_time,
                metadata={
                    "agent_name": self.name,
                    "version": self.version,
                    "steps_completed": len(self.steps),
                    "template_used": template.id if template else None,
                }
            )

        except Exception as e:
            self._set_state(AgentState.FAILED)
            return AgentResult(
                success=False,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def generate_section(
        self,
        section_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        单独生成某个章节，支持基于已有 PRD 内容的上下文继承

        Args:
            section_id: 章节标识（如 background, user_stories）
            context: 上下文信息，可包含:
                - product_name, description, target_users 等基础信息
                - existing_prd: 已有 PRD 的 markdown 或 structured 内容
                - industry, template_id 等行业模板信息

        Returns:
            {"section_id": str, "markdown": str, "structured": dict}
        """
        section_map = {s["id"]: s for s in self.PRD_SECTIONS}
        section_meta = section_map.get(section_id)
        if not section_meta:
            return {"section_id": section_id, "markdown": "", "structured": {}, "error": "未知章节"}

        ctx = self._build_context(context)
        template = self._match_template(ctx)
        ctx["template"] = template

        existing_prd = context.get("existing_prd", "")
        existing_md = existing_prd if isinstance(existing_prd, str) else existing_prd.get("markdown", "")

        prompt = f"""请为以下产品生成 PRD 的「{section_meta['name']}」章节。

## 产品信息
- 产品名称: {ctx['product_name']}
- 产品描述: {ctx['description']}
- 目标用户: {ctx['target_users']}
- 核心功能: {', '.join(ctx['key_features'])}
- 约束条件: {', '.join(ctx['constraints']) if ctx['constraints'] else '无'}

## 已有 PRD 上下文（供参考，保持风格一致）
{existing_md[:2000] if existing_md else '（尚无其他章节）'}

## 输出要求
1. 只输出该章节的 Markdown 内容
2. 必须与已有上下文逻辑一致
3. 内容具体、可直接用于评审
"""

        system_prompt = self._build_system_prompt(ctx)
        raw_output = await self._call_llm(prompt=prompt, system_prompt=system_prompt)
        markdown = self._extract_markdown(raw_output, section_id)

        # 尝试提取结构化数据
        structured = self._extract_section_structured(section_id, markdown)

        return {
            "section_id": section_id,
            "markdown": markdown,
            "structured": structured,
        }

    # ==================== Context & Template ====================

    def _build_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建标准化上下文"""
        product_name = input_data.get("product_name", "未命名产品")
        description = input_data.get("description", "")
        target_users = input_data.get("target_users", "")
        key_features = input_data.get("key_features", [])
        constraints = input_data.get("constraints", [])
        sections = input_data.get("sections", [s["id"] for s in self.PRD_SECTIONS])
        industry = input_data.get("industry", "")
        template_id = input_data.get("template_id", "")

        # 自动检测行业（如果未指定）
        if not industry:
            detected = self.template_system.detect_industry(f"{product_name} {description}")
            industry = detected.value

        # 规范化 sections
        if isinstance(sections, list) and sections and isinstance(sections[0], str):
            section_ids = sections
        else:
            section_ids = [s["id"] for s in self.PRD_SECTIONS]

        # 医疗行业强制加入合规章节
        if industry == "medical" and "compliance" not in section_ids:
            # 在 functional_requirements 之后插入 compliance
            idx = next((i for i, s in enumerate(section_ids) if s == "functional_requirements"), len(section_ids) - 1)
            section_ids.insert(idx + 1, "compliance")

        return {
            "product_name": product_name,
            "description": description,
            "target_users": target_users,
            "key_features": key_features if isinstance(key_features, list) else [key_features],
            "constraints": constraints if isinstance(constraints, list) else [constraints],
            "sections": section_ids,
            "industry": industry,
            "template_id": template_id,
        }

    def _match_template(self, ctx: Dict[str, Any]) -> Optional[Any]:
        """匹配行业模板"""
        # 优先按 template_id
        if ctx.get("template_id"):
            template = self.template_system.get_template(ctx["template_id"])
            if template:
                return template

        # 按行业+内容匹配
        text = f"{ctx['product_name']} {ctx['description']}"
        try:
            industry = IndustryType(ctx["industry"]) if ctx["industry"] else IndustryType.UNKNOWN
        except ValueError:
            industry = IndustryType.UNKNOWN
        return self.template_system.match_template(text, industry)

    # ==================== Prompt Engineering ====================

    def _build_system_prompt(self, ctx: Dict[str, Any]) -> str:
        """构建增强的系统提示词"""
        parts = [self.BASE_SYSTEM_PROMPT]

        template = ctx.get("template")
        if template and "prd_generator" in template.agent_prompts:
            parts.append(f"\n=== 行业特定要求 ===\n{template.agent_prompts['prd_generator']}")

        return "\n".join(parts)

    def _build_prompt(self, ctx: Dict[str, Any]) -> str:
        """构建结构化生成提示词"""
        sections = ctx["sections"]
        section_names = []
        for sec in self.PRD_SECTIONS:
            if sec["id"] in sections:
                section_names.append(f"- {sec['name']} ({'必选' if sec['required'] else '可选'})")

        prompt = f"""# PRD 生成任务

## 产品信息
- **产品名称**: {ctx['product_name']}
- **产品描述**: {ctx['description']}
- **目标用户**: {ctx['target_users']}
- **核心功能**:
"""
        for i, feature in enumerate(ctx["key_features"], 1):
            prompt += f"  {i}. {feature}\n"

        if ctx["constraints"]:
            prompt += "\n## 约束与限制\n"
            for c in ctx["constraints"]:
                prompt += f"- {c}\n"

        prompt += f"""
## 需要生成的章节
{chr(10).join(section_names)}

## 输出格式（非常重要）
请严格按以下格式返回：

```json
{{
    "title": "{ctx['product_name']}",
    "industry": "{ctx['industry']}",
    "sections": [
        {{"id": "background", "name": "背景与目标", "key_points": ["要点1", "要点2"]}},
        {{"id": "user_stories", "name": "用户故事", "key_points": []}}
    ],
    "user_stories": [
        {{"id": "US-001", "role": "作为患者", "story": "我想要在线申请切片借阅", "acceptance_criteria": ["条件1"], "priority": "P0"}}
    ],
    "requirements": [
        {{"id": "FR-001", "title": "在线申请", "description": "...", "priority": "P0", "type": "functional"}}
    ],
    "compliance_items": [
        {{"name": "等保三级", "category": "security", "checklist": ["..."]}}
    ],
    "milestones": [
        {{"phase": "第一阶段", "deliverables": ["..."], "duration": "2周"}}
    ]
}}
```

---

# {ctx['product_name']} 产品需求文档

[此处开始为完整的 Markdown PRD 正文]
"""
        return prompt

    # ==================== Output Parsing ====================

    def _parse_output(self, raw_output: str, ctx: Dict[str, Any]) -> tuple:
        """
        解析 LLM 输出为 structured + markdown
        """
        structured = self._extract_json(raw_output)
        markdown = self._extract_markdown(raw_output)

        # 如果 markdown 为空，从 structured 反向生成
        if not markdown.strip():
            markdown = self._structured_to_markdown(structured, ctx)

        # 如果 structured 为空，从 markdown 反向提取
        if not structured:
            structured = self._markdown_to_structured(markdown, ctx)

        return structured, markdown

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从输出中提取 JSON 块"""
        # 尝试匹配 ```json ... ```
        match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试直接找第一个大括号包裹的 JSON
        match = re.search(r"(\{.*\})", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return {}

    def _extract_markdown(self, content: str, fallback_section_id: Optional[str] = None) -> str:
        """提取 Markdown 部分（JSON 之后的内容）"""
        # 去掉 JSON 块
        cleaned = re.sub(r"```json\s*\{.*?\}\s*```", "", content, flags=re.DOTALL)
        cleaned = cleaned.strip()

        # 去掉 "---" 分隔线之前的 JSON 残留
        if "---" in cleaned and "# " not in cleaned.split("---")[0]:
            cleaned = cleaned[cleaned.find("---"):]

        # 确保有标题
        if fallback_section_id and not cleaned.startswith("#"):
            sec_name = next((s["name"] for s in self.PRD_SECTIONS if s["id"] == fallback_section_id), "")
            cleaned = f"# {sec_name}\n\n{cleaned}"

        return cleaned.strip()

    def _extract_section_structured(self, section_id: str, markdown: str) -> Dict[str, Any]:
        """从单个章节的 markdown 中提取结构化数据"""
        if section_id == "user_stories":
            return {"user_stories": self._parse_user_stories(markdown)}
        if section_id == "functional_requirements":
            return {"requirements": self._parse_requirements(markdown)}
        if section_id == "compliance":
            return {"compliance_items": self._parse_compliance(markdown)}
        return {"raw": markdown[:1000]}

    def _markdown_to_structured(self, markdown: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """从 Markdown 反向提取结构化数据（兜底）"""
        return {
            "title": ctx["product_name"],
            "industry": ctx["industry"],
            "sections": [
                {"id": s, "name": next((x["name"] for x in self.PRD_SECTIONS if x["id"] == s), s), "key_points": []}
                for s in ctx["sections"]
            ],
            "user_stories": self._parse_user_stories(markdown),
            "requirements": self._parse_requirements(markdown),
            "compliance_items": self._parse_compliance(markdown),
            "milestones": [],
        }

    def _structured_to_markdown(self, data: Dict[str, Any], ctx: Dict[str, Any]) -> str:
        """从结构化数据生成 Markdown（兜底）"""
        md = [f"# {data.get('title', ctx['product_name'])}"]

        for sec in data.get("sections", []):
            md.append(f"\n## {sec.get('name', '')}")
            for kp in sec.get("key_points", []):
                md.append(f"- {kp}")

        us_list = data.get("user_stories", [])
        if us_list:
            md.append("\n## 用户故事")
            for us in us_list:
                md.append(f"\n### {us.get('id', '')}: {us.get('role', '')}")
                md.append(f"> {us.get('story', '')}")
                ac = us.get("acceptance_criteria", [])
                if ac:
                    md.append("\n**验收标准**:")
                    for c in ac:
                        md.append(f"- {c}")

        return "\n".join(md)

    # ==================== Regex Extractors ====================

    def _parse_user_stories(self, markdown: str) -> List[Dict[str, Any]]:
        """解析用户故事"""
        stories = []
        # 匹配 ### US-001: 作为...
        pattern = r"###\s*(US-\d+)[:\s]*(.*?)[\n\r]+>\s*(.*?)(?=\n\r?\n|$)"
        for m in re.finditer(pattern, markdown, re.DOTALL):
            stories.append({
                "id": m.group(1).strip(),
                "role": m.group(2).strip(),
                "story": m.group(3).strip().replace("\n", " "),
                "acceptance_criteria": [],
                "priority": "P1"
            })

        # 如果没有结构化匹配，尝试文本行匹配
        if not stories:
            for line in markdown.split("\n"):
                line = line.strip()
                if line.startswith("- 作为") or line.startswith("> 作为"):
                    stories.append({
                        "id": f"US-{len(stories)+1:03d}",
                        "role": "",
                        "story": line.strip("- >").strip(),
                        "acceptance_criteria": [],
                        "priority": "P1"
                    })

        return stories

    def _parse_requirements(self, markdown: str) -> List[Dict[str, Any]]:
        """解析功能需求"""
        reqs = []
        # 匹配 #### FR-001 功能名称 或 - **FR-001** 功能名称
        pattern = r"(?:^|\n)(?:#{1,4}\s*|[-*]\s*\*\*)(FR-\d+)[\s*:*]+(.*?)\n"
        for m in re.finditer(pattern, markdown, re.MULTILINE):
            reqs.append({
                "id": m.group(1).strip(),
                "title": m.group(2).strip(),
                "description": "",
                "priority": "P1",
                "type": "functional"
            })
        return reqs

    def _parse_compliance(self, markdown: str) -> List[Dict[str, Any]]:
        """解析合规项"""
        items = []
        lines = markdown.split("\n")
        current = None
        for line in lines:
            line = line.strip()
            if line.startswith("### ") or line.startswith("## "):
                if current:
                    items.append(current)
                name = line.strip("# ")
                current = {"name": name, "category": "security", "checklist": []}
            elif line.startswith("- [") and current:
                current["checklist"].append(line.strip("- []").strip())
            elif line.startswith("- ") and current and "checklist" in current:
                current["checklist"].append(line.strip("- "))
        if current:
            items.append(current)
        return items

    def _post_process(self, content: str) -> str:
        """兼容性后处理"""
        content = content.strip()
        if not content.startswith("#"):
            content = f"# 产品需求文档 (PRD)\n\n{content}"

        if "---" not in content[:200]:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f"""---
generated_at: {timestamp}
agent: {self.name} v{self.version}
---

"""
            content = header + content

        return content
