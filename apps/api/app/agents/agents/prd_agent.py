#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD 生成 Agent v2.0

- 自动行业检测与模板增强
- 结构化 JSON + Markdown 双输出
- 支持章节细粒度生成与上下文继承
- 内置医疗等行业合规注入
"""

import asyncio
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError

from ..base import BaseAgent, AgentResult, AgentState
from ..templates import get_template_system, IndustryType, TemplateSystem
from ..evaluator import LLMJudge

logger = logging.getLogger(__name__)


class PRDSection(BaseModel):
    """PRD 章节结构"""
    title: str = Field(default="", description="章节标题")
    content: str = Field(default="", description="章节内容")
    subsections: List[Dict[str, str]] = Field(default_factory=list, description="子章节")


class PRDStructuredOutput(BaseModel):
    """PRD 结构化输出模型"""
    title: str = Field(default="", description="PRD 标题")
    sections: List[PRDSection] = Field(default_factory=list, description="章节列表")
    summary: str = Field(default="", description="摘要")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


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
- 仅返回 Markdown 格式的 PRD 文档
- 不要返回 JSON
- 使用标准 Markdown 语法（# ## ### 等标题）
"""

    def __init__(self, llm_client=None, **kwargs):
        """初始化 PRD Agent"""
        super().__init__(llm_client=llm_client, **kwargs)
        self.template_system = get_template_system()
        self._section_cache: Dict[str, str] = {}
        self._evaluator = LLMJudge(llm_client=self.llm_client)

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行 PRD 生成（单一路径：一次请求生成完整内容）

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
                - skip_evaluation: 是否跳过 AI 质量评估（默认 True，关闭以加快速度）

        Returns:
            AgentResult: 包含生成的 PRD（markdown + structured）
        """
        skip_evaluation = input_data.get("skip_evaluation", True)

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

        # 步骤4: 调用 LLM 生成（带超时保护，防止挂死）
        step4 = self._create_step("generate", "生成 PRD 文档")
        try:
            raw_output = await asyncio.wait_for(
                self._call_llm(prompt=prompt, system_prompt=system_prompt),
                timeout=120  # 最多等待 120 秒
            )
        except asyncio.TimeoutError:
            raise RuntimeError("LLM 生成超时（120秒），请检查网络或稍后重试")
        self._complete_step(step4, f"原始输出长度: {len(raw_output)} 字符")

        # 步骤5: 解析与后处理
        step5 = self._create_step("post_process", "解析结构化数据")
        structured, markdown = self._parse_output(raw_output, ctx)
        self._complete_step(step5, f"Markdown {len(markdown)} 字符, 提取 {len(structured.get('sections', []))} 个章节")

        # 步骤6: 自动质量评估（可选，默认跳过以加快速度）
        eval_result = None
        if not skip_evaluation:
            step6 = self._create_step("quality_eval", "AI 质量评估")
            try:
                eval_result = await self._evaluator.evaluate(
                    agent_name=self.name,
                    task_type="prd",
                    output=markdown,
                    context={
                        "product_name": ctx["product_name"],
                        "industry": ctx["industry"],
                        "template_id": template.id if template else None,
                    },
                )
                self._complete_step(
                    step6,
                    f"综合评分: {eval_result.total_score}/10"
                )
            except Exception as eval_err:
                self._complete_step(step6, f"评估跳过: {eval_err}")

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
                "evaluation": eval_result.to_dict() if eval_result else None,
            },
            execution_time=self.elapsed_seconds,
            metadata={
                "agent_name": self.name,
                "version": self.version,
                "steps_completed": len(self.steps),
                "template_used": template.id if template else None,
                "evaluated": eval_result is not None,
            }
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

        # 大纲优先模式：注入大纲要点
        outline_hint = ""
        outline = context.get("outline")
        if outline:
            section_outline = next(
                (s for s in outline.get("sections", []) if s.get("id") == section_id),
                None
            )
            if section_outline and section_outline.get("key_points"):
                outline_hint = "\n## 大纲要点（必须覆盖）\n"
                for kp in section_outline["key_points"]:
                    outline_hint += f"- {kp}\n"

        prompt = f"""请为以下产品生成 PRD 的「{section_meta['name']}」章节。

## 产品信息
- 产品名称: {ctx['product_name']}
- 产品描述: {ctx['description']}
- 目标用户: {ctx['target_users']}
- 核心功能: {', '.join(ctx['key_features'])}
- 约束条件: {', '.join(ctx['constraints']) if ctx['constraints'] else '无'}

## 已有 PRD 上下文（供参考，保持风格一致）
{existing_md[:2000] if existing_md else '（尚无其他章节）'}
{outline_hint}

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

        # 注入 PRD 通用输出规范
        parts.append(f"\n=== PRD 通用输出规范 ===\n{TemplateSystem.DEFAULT_PRD_GUIDELINES}")

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

        # 合规章节与功能需求融合提示
        compliance_fusion = ""
        template = ctx.get("template")
        if template and template.compliance_requirements:
            compliance_fusion = "\n## 合规与功能融合要求\n"
            compliance_fusion += "在「功能规格」章节中，每个功能模块必须标注其关联的合规要求。\n"
            compliance_fusion += "格式示例：\n"
            compliance_fusion += "- 功能A：患者在线申请切片借阅 → 关联合规：患者身份核验（等保三级-身份鉴别）、授权书电子签章（患者隐私保护-授权机制）\n"
            compliance_fusion += "- 功能B：医生查看检验报告 → 关联合规：RBAC权限控制（等保三级-访问控制）、操作审计（审计追踪-全程记录）\n"
            compliance_fusion += "\n必须关联的合规维度：\n"
            for req in template.compliance_requirements[:4]:  # 取前4个关键合规项
                compliance_fusion += f"- {req.name}：{req.description}\n"

        prompt += f"""
## 需要生成的章节
{chr(10).join(section_names)}
{compliance_fusion}

## 输出格式要求（必须严格遵守）

请直接输出 Markdown 格式的 PRD 文档。以下格式要求具有最高优先级，必须严格执行：

### 章节编号规则
- 文档主标题：`# 产品名称`（不带编号）
- 一级章节标题：`## N. 标题`（例如：`## 1. 背景与目标`）
- 二级章节标题：`### N.N 标题`（例如：`### 1.1 市场背景`）
- 三级章节标题：`#### N.N.N 标题`（例如：`#### 1.1.1 子模块`）
- **绝对禁止**出现 `## 1. 1. 背景与目标`、`### 2. 2. 用户故事` 这种数字重复格式
- 章节标题中禁止出现双重编号，每个标题只应有一个章节号

### 必须包含的内容元素
1. **MVP 边界**：每个功能点必须明确标注「一期」或「二期」
2. **状态机**：必须包含 Mermaid 状态转换图（`stateDiagram-v2` 或 `graph TD`）和 Markdown 状态转换表
3. **流程图**：核心业务流程必须使用 Mermaid/PlantUML 泳道图，禁止纯文本描述
4. **信息架构(IA)**：功能规格章节必须包含信息架构图（树状结构）和核心页面字段清单（Markdown 表格）
5. **验收标准**：每个用户故事必须使用 Given-When-Then 格式
6. **对账规则**（如涉及支付/财务）：必须明确长款/短款/单边账的处理规则

### 章节结构示例（仅供参考，必须按实际内容填充）

# {ctx['product_name']} 产品需求文档

## 1. 背景与目标
### 1.1 市场环境
### 1.2 业务目标（标注一期/二期）

## 2. 用户故事
### 2.1 角色画像
### 2.2 用户故事与验收标准（Given-When-Then 格式）

## 3. 业务流程
### 3.1 核心流程（附 Mermaid 泳道图）
### 3.2 异常流程

## 4. 功能规格
### 4.1 信息架构图(IA)
### 4.2 核心页面字段清单（表格）
### 4.3 功能模块详述（标注一期/二期）

## 5. 数据架构
### 5.1 状态机定义（附 Mermaid 图 + 转换表）
### 5.2 数据模型

## 6. 合规要求

## 7. 数据埋点

## 8. 供应链与促销策略（如适用）

## 9. 里程碑
### 9.1 一期里程碑
### 9.2 二期里程碑
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

    def _repair_json(self, raw: str) -> str:
        """修复常见的 JSON 格式错误"""
        # 去除首尾空白
        cleaned = raw.strip()
        # 去除可能的 markdown 标记
        cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.DOTALL)
        # 去除尾部逗号（对象/数组最后一个元素后的逗号）
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
        # 将单引号键值对转换为双引号（简单替换）
        cleaned = re.sub(r"'([^']+)'\s*:", r'"\1":', cleaned)
        # 修复缺失的右花括号（简单补全）
        open_count = cleaned.count('{')
        close_count = cleaned.count('}')
        if open_count > close_count:
            cleaned += '}' * (open_count - close_count)
        return cleaned

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从输出中提取 JSON 块，使用 Pydantic 结构化解析 + 容错修复"""
        candidates = []

        # 候选1: ```json ... ``` — 贪婪匹配到闭合的 ```
        match = re.search(r"```json\s*([\s\S]*?)\s*```", content, re.DOTALL)
        if match:
            candidates.append(match.group(1).strip())

        # 候选2: 直接找第一个大括号包裹的内容（贪婪匹配到最后的 }）
        match = re.search(r"(\{[\s\S]*\})", content)
        if match:
            candidates.append(match.group(1).strip())

        for raw in candidates:
            try:
                repaired = self._repair_json(raw)
                data = json.loads(repaired)
                # 使用 Pydantic 验证结构
                validated = PRDStructuredOutput.model_validate(data)
                return validated.model_dump()
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"JSON parse attempt failed: {e}")
                continue

        logger.error("All JSON parse attempts failed, returning empty dict")
        return {}

    def _extract_markdown(self, content: str, fallback_section_id: Optional[str] = None) -> str:
        """提取 Markdown 部分（JSON 之后的内容）"""
        # 去掉 JSON 块（贪婪匹配到闭合的 ```）
        cleaned = re.sub(r"```json\s*[\s\S]*?\s*```", "", content, flags=re.DOTALL)
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
