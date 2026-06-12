"""AI 原型生成服务

提供从 PRD 到高保真可交互原型的全链路生成能力。
- 透明流水线：骨架提取 → 用户确认 → 流式生成 → 生成报告
- 高保真输出：对标 Figma 视觉精度 + Axure 交互深度
- 快速出图：双层缓存 + 流式 SSE
"""

import copy
import json
import hashlib
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator

from app.services.ai_service import ai_service
from app.core.cache import cache_manager

logger = logging.getLogger(__name__)


class PrototypeAIService:
    """AI 原型生成服务"""

    # 行业设计系统预设
    DESIGN_SYSTEMS = {
        "medical": {
            "name": "医疗专业",
            "colors": {
                "primary": "#2563eb",
                "primary_light": "#dbeafe",
                "bg": "#f8fafc",
                "surface": "#ffffff",
                "success": "#22c55e",
                "warning": "#f59e0b",
                "danger": "#ef4444",
                "text": "#1e293b",
                "text_secondary": "#64748b",
                "border": "#e2e8f0",
            },
            "style_notes": "医疗系统风格，蓝白配色，专业严谨，大量留白，信息层级清晰",
        },
        "saas": {
            "name": "SaaS 现代",
            "colors": {
                "primary": "#6366f1",
                "primary_light": "#e0e7ff",
                "bg": "#f1f5f9",
                "surface": "#ffffff",
                "success": "#10b981",
                "warning": "#f59e0b",
                "danger": "#ef4444",
                "text": "#0f172a",
                "text_secondary": "#64748b",
                "border": "#e2e8f0",
            },
            "style_notes": "SaaS 现代风格，紫蓝主色，简洁高效，卡片式布局，微交互动效",
        },
        "ecommerce": {
            "name": "电商活力",
            "colors": {
                "primary": "#f97316",
                "primary_light": "#ffedd5",
                "bg": "#fafaf9",
                "surface": "#ffffff",
                "success": "#22c55e",
                "warning": "#eab308",
                "danger": "#ef4444",
                "text": "#18181b",
                "text_secondary": "#71717a",
                "border": "#e4e4e7",
            },
            "style_notes": "电商活力风格，橙色系，促销氛围，大图卡片，行动按钮突出",
        },
        "general": {
            "name": "通用简洁",
            "colors": {
                "primary": "#0ea5e9",
                "primary_light": "#e0f2fe",
                "bg": "#f8fafc",
                "surface": "#ffffff",
                "success": "#22c55e",
                "warning": "#f59e0b",
                "danger": "#ef4444",
                "text": "#1e293b",
                "text_secondary": "#64748b",
                "border": "#e2e8f0",
            },
            "style_notes": "通用简洁风格，天蓝色系，清爽干净，适合大多数产品",
        },
    }

    def __init__(self):
        self.ai = ai_service

    def _get_design_system(self, industry: str) -> Dict[str, Any]:
        """根据行业获取设计系统配置"""
        return copy.deepcopy(self.DESIGN_SYSTEMS.get(industry, self.DESIGN_SYSTEMS["general"]))

    # ========== 占位符清洗 ==========

    def clean_placeholders(self, text: str) -> str:
        """清洗 PRD 中的占位符和估算标注"""
        text = re.sub(r'\{\{待填写:[^}]*\}\}', '待定', text)
        text = re.sub(r'【估算，需核实】', '', text)
        text = re.sub(r'\{\{[^}]*\}\}', '待定', text)
        return text

    # ========== 骨架提取 ==========

    async def extract_skeleton(
        self,
        prd_content: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """从 PRD 提取结构化骨架，返回透明可见的产品信息"""
        options = options or {}
        style = options.get("style", "high-fidelity")

        cleaned_prd = self.clean_placeholders(prd_content)

        cache_key = self._generate_cache_key("proto:skeleton", cleaned_prd[:5000], style)
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.info("[Cache Hit] Skeleton: %s", cached.get("product_name", "unknown"))
            return cached

        prompt = self._build_extract_prompt(cleaned_prd)

        try:
            response = await self.ai.chat(
                prompt,
                {
                    "system_prompt": (
                        "你是一位产品分析专家，擅长从 PRD 文档中提取结构化产品信息。"
                        "只输出 JSON，不要其他文字。"
                    ),
                    "max_tokens": 4000,
                },
            )

            skeleton = self._parse_json_response(response)
            skeleton.setdefault("product_name", "未命名产品")
            skeleton.setdefault("industry", "general")
            skeleton.setdefault("roles", [])
            skeleton.setdefault("user_journeys", [])
            skeleton.setdefault("pages", [])
            skeleton.setdefault("key_entities", [])
            skeleton.setdefault("design_hints", {})

            await cache_manager.set(cache_key, skeleton, ttl=3600)
            logger.info(
                "[Cache Set] Skeleton: %s, pages=%d, roles=%d",
                skeleton["product_name"],
                len(skeleton["pages"]),
                len(skeleton["roles"]),
            )
            return skeleton

        except Exception as e:
            logger.error("骨架提取失败: %s", e)
            return self._fallback_skeleton(cleaned_prd)

    def _build_extract_prompt(self, prd_content: str) -> str:
        return f"""请从以下 PRD 文档中提取产品骨架信息，以 JSON 格式输出。

需要提取的字段：
1. product_name: 产品名称（字符串）
2. industry: 行业类型，只能是 medical/saas/ecommerce/general 之一
3. roles: 用户角色列表（数组，每个元素包含 name, permissions 数组, primary 布尔值）
4. user_journeys: 用户旅程列表（数组，每个元素包含 name, steps 数组, pages 数组）
5. pages: 页面列表（数组，每个元素包含 name, role, type, key_features 数组）
   - type 可选：dashboard/form/table/detail/list/settings
6. key_entities: 核心数据实体名称列表（数组，用于生成模拟数据）
7. design_hints: 设计提示（对象，包含 style 和 primary_color）

注意：
- 只输出合法的 JSON，不要 markdown 代码块标记，不要其他文字
- 如果信息不足，用合理的默认值填充
- 页面要按照用户旅程的顺序排列
- 角色中的 primary=true 表示最主要的用户角色

PRD 内容：
{prd_content[:8000]}"""

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """从 LLM 响应中提取 JSON"""
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        match = re.search(r'(\{{[\s\S]*\}})', text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        raise ValueError("无法从响应中解析 JSON")

    def _fallback_skeleton(self, prd_content: str) -> Dict[str, Any]:
        """提取失败时的兜底骨架"""
        industry = "general"
        if any(k in prd_content for k in ["医院", "医疗", "病理", "医生", "患者", "HIS", "EMR"]):
            industry = "medical"
        elif any(k in prd_content for k in ["电商", "商品", "订单", "支付", "库存", "SKU"]):
            industry = "ecommerce"
        elif any(k in prd_content for k in ["SaaS", "租户", "订阅", "B2B", "RBAC"]):
            industry = "saas"

        return {
            "product_name": "产品原型",
            "industry": industry,
            "roles": [{"name": "用户", "permissions": ["查看", "操作"], "primary": True}],
            "user_journeys": [
                {
                    "name": "核心流程",
                    "steps": ["开始", "操作", "完成"],
                    "pages": ["首页", "操作页"],
                }
            ],
            "pages": [
                {"name": "首页", "role": "用户", "type": "dashboard", "key_features": ["数据展示"]},
                {"name": "操作页", "role": "用户", "type": "form", "key_features": ["表单操作"]},
            ],
            "key_entities": ["数据记录"],
            "design_hints": {"style": f"{industry}_professional"},
        }

    # ========== 原型生成（流式） ==========

    async def generate_prototype_stream(
        self,
        skeleton: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式生成原型，yield SSE 事件字典

        事件类型：
        - stage: 阶段进度（extract/skeleton_confirmed/design_system/page_generating/mock_data/interactions）
        - chunk: HTML 代码片段
        - done: 完成，附带生成报告
        - error: 错误信息
        """
        options = options or {}
        style = options.get("style", "high-fidelity")
        pages = skeleton.get("pages", [])
        roles = skeleton.get("roles", [])

        # 阶段 1: 骨架确认
        yield {
            "event": "stage",
            "data": {
                "stage": "skeleton_confirmed",
                "product_name": skeleton.get("product_name", ""),
                "pages": len(pages),
                "roles": len(roles),
                "style": style,
            },
        }

        # 缓存检查
        skeleton_str = json.dumps(skeleton, sort_keys=True, ensure_ascii=False)
        cache_key = self._generate_cache_key("proto:demo", skeleton_str, style)
        cached = await cache_manager.get(cache_key)

        if cached and cached.get("html"):
            logger.info("[Cache Hit] Demo: %s", skeleton.get("product_name"))
            html = cached["html"]
            report = cached.get("report", {})

            yield {
                "event": "stage",
                "data": {
                    "stage": "design_system",
                    "colors": report.get("design_system", {}).get("colors", {}),
                },
            }
            yield {
                "event": "stage",
                "data": {
                    "stage": "page_generating",
                    "current": "从缓存恢复",
                    "progress": f"{len(pages)}/{len(pages)}",
                },
            }
            for i in range(0, len(html), 800):
                yield {"event": "chunk", "data": html[i:i + 800]}
            yield {
                "event": "stage",
                "data": {"stage": "mock_data", "entities": report.get("mock_data", {})},
            }
            yield {
                "event": "done",
                "data": {"report": report, "cached": True},
            }
            return

        # 阶段 2: 设计系统
        industry = skeleton.get("industry", "general")
        design_system = self._get_design_system(industry)
        yield {
            "event": "stage",
            "data": {
                "stage": "design_system",
                "name": design_system["name"],
                "colors": design_system["colors"],
            },
        }

        # 阶段 3: 生成 HTML
        prompt = self._build_generate_prompt(skeleton, design_system, style)

        first_page = pages[0]["name"] if pages else "首页"
        yield {
            "event": "stage",
            "data": {
                "stage": "page_generating",
                "current": first_page,
                "progress": f"0/{len(pages)}",
            },
        }

        html_parts: list[str] = []
        MAX_HTML_SIZE = 2 * 1024 * 1024  # 2MB safety limit
        try:
            async for chunk in self.ai.chat_stream(
                prompt,
                {
                    "system_prompt": self._get_generate_system_prompt(),
                    "max_tokens": 8000,
                },
            ):
                html_parts.append(chunk)
                yield {"event": "chunk", "data": chunk}
                # Memory safety check
                current_size = sum(len(c.encode("utf-8")) for c in html_parts)
                if current_size > MAX_HTML_SIZE:
                    logger.error("HTML generation exceeded %d bytes, aborting", MAX_HTML_SIZE)
                    yield {
                        "event": "error",
                        "data": {"message": "生成内容过大，已中断", "stage": "page_generating"},
                    }
                    return
        except Exception as e:
            logger.error("HTML 生成失败: %s", e)
            yield {
                "event": "error",
                "data": {"message": "生成失败，请稍后重试", "stage": "page_generating"},
            }
            return

        full_html = "".join(html_parts)
        # 提取和验证 HTML
        html_code = self._extract_and_validate_html(full_html)

        # 阶段 4 & 5: 数据统计
        mock_data = self._estimate_mock_data(skeleton)
        interactions = self._estimate_interactions(html_code)

        report = {
            "product_name": skeleton.get("product_name", ""),
            "pages": len(pages),
            "page_list": [
                {"name": p["name"], "role": p.get("role", ""), "type": p.get("type", "")}
                for p in pages
            ],
            "roles": [{"name": r["name"], "primary": r.get("primary", False)} for r in roles],
            "design_system": design_system,
            "mock_data": mock_data,
            "interactions": {
                "total": interactions,
                "types": ["路由切换", "表单提交", "弹窗", "筛选", "分页", "Toast反馈"],
            },
            "html_size_kb": round(len(html_code.encode("utf-8")) / 1024, 1),
        }

        yield {
            "event": "stage",
            "data": {"stage": "mock_data", "entities": mock_data},
        }
        yield {
            "event": "stage",
            "data": {"stage": "interactions", "count": interactions},
        }

        # 缓存
        await cache_manager.set(
            cache_key,
            {"html": html_code, "report": report},
            ttl=7200,
        )

        # 完成
        yield {
            "event": "done",
            "data": {"report": report, "cached": False},
        }

    # ========== Prompt 构建 ==========

    def _get_generate_system_prompt(self) -> str:
        return """你是一位资深前端工程师，擅长用 HTML + Tailwind CSS 构建高保真产品原型。
你的输出对标 Figma 设计稿的视觉精度和 Axure 的交互深度。

【核心原则】
1. 输出完整的、可独立运行的单文件 HTML
2. 使用 Tailwind CSS CDN（https://cdn.tailwindcss.com）
3. 中文界面，字体清晰
4. 代码整洁，无外部依赖

【设计规范】
- 按钮：圆角 md，hover 时亮度变化，primary 按钮最突出
- 输入框：focus:ring-2，有错误状态边框变红
- 卡片：白色背景，shadow-sm，hover 微上浮
- 表格：表头灰色背景，行交替色，状态标签彩色 pill
- 导航：当前项高亮，hover 有背景色变化

【交互要求】
1. 所有按钮可点击，有 hover/active 视觉反馈
2. 表单填写后有验证反馈（成功绿色/错误红色）
3. 页面/视图切换有平滑过渡（opacity + translate）
4. 数据操作后有 Toast 提示（右上角滑入）
5. 表格支持模拟排序、搜索过滤
6. 弹窗/抽屉有遮罩层，点击遮罩或关闭按钮关闭
7. 状态标签用彩色 pill（待审批=黄色，已通过=绿色，已驳回=红色）

【数据结构】
- 生成 20-30 条丰富的模拟数据
- 覆盖各种业务状态
- 数据要有真实感（姓名用中文，日期合理）

请直接输出 HTML 代码，用 ```html 和 ``` 包裹。"""

    def _build_generate_prompt(
        self,
        skeleton: Dict[str, Any],
        design_system: Dict[str, Any],
        style: str = "high-fidelity",
    ) -> str:
        pages_desc = self._format_pages_description(skeleton.get("pages", []))
        roles_desc = self._format_roles_description(skeleton.get("roles", []))
        journeys_desc = self._format_journeys_description(skeleton.get("user_journeys", []))
        entities = skeleton.get("key_entities", [])
        colors = design_system["colors"]

        fidelity_note = ""
        if style == "wireframe":
            fidelity_note = """
【线框风要求】
- 使用灰度配色（灰白背景 + 深灰边框），不要有彩色
- 按钮用边框样式，不要有填充色
- 图片用占位矩形（带斜线或图标）
- 整体风格刻意简洁，突出结构和流程
"""

        return f"""基于以下产品骨架，生成一个高保真可交互的前端原型。

【产品信息】
- 名称：{skeleton.get('product_name', '产品原型')}
- 行业：{skeleton.get('industry', 'general')}

【设计系统】
- 风格：{design_system['style_notes']}
- 主色：{colors['primary']}
- 背景色：{colors['bg']}
- 成功色：{colors['success']}
- 警告色：{colors['warning']}
- 危险色：{colors['danger']}

【用户角色】
{roles_desc}

【用户旅程】
{journeys_desc}

【页面列表】
{pages_desc}

【核心实体】（用于生成模拟数据）
{', '.join(entities) if entities else '数据记录'}

{fidelity_note}
【架构要求】
生成单文件 SPA，包含：

1. **应用外壳**：
   - 顶部导航栏：产品 Logo/名称 + 角色切换器（标签页形式）
   - 左侧边栏：页面导航，按用户旅程分组
   - 主内容区：动态显示当前页面

2. **角色切换**：
   - 点击顶部角色标签切换不同角色的视图
   - 切换时侧边栏和主内容区同步更新
   - 当前角色高亮显示

3. **页面视图**（每个页面一个 section，默认 hidden，当前显示）：
   - Dashboard 类型：统计卡片 + 快捷入口 + 数据列表
   - Form 类型：完整表单 + 验证 + 提交反馈
   - Table 类型：数据表格 + 搜索 + 筛选 + 分页
   - Detail 类型：详情展示 + 操作按钮
   - List 类型：卡片列表 + 状态标签

4. **交互系统**：
   - 路由：hash 路由控制当前页面
   - Toast：操作成功/失败的右上角提示
   - Modal：弹窗确认、详情抽屉
   - 数据过滤：表格搜索、状态筛选

5. **模拟数据**：
   - 在 script 中定义 mockData 对象
   - 每种实体 15-30 条数据
   - 覆盖各种状态组合

请确保代码可直接在浏览器中打开运行。直接输出 HTML 代码，用 ```html 和 ``` 包裹。"""

    def _format_pages_description(self, pages: List[Dict]) -> str:
        lines = []
        for i, p in enumerate(pages, 1):
            features = ", ".join(p.get("key_features", []))
            lines.append(
                f"{i}. {p['name']}（角色：{p.get('role', '通用')}，类型：{p.get('type', 'page')}）"
                f"- 功能：{features}"
            )
        return "\n".join(lines) if lines else "1. 首页（角色：通用，类型：dashboard）"

    def _format_roles_description(self, roles: List[Dict]) -> str:
        lines = []
        for r in roles:
            perms = ", ".join(r.get("permissions", []))
            primary = " [主角色]" if r.get("primary") else ""
            lines.append(f"- {r['name']}{primary}：{perms}")
        return "\n".join(lines) if lines else "- 用户：查看、操作"

    def _format_journeys_description(self, journeys: List[Dict]) -> str:
        lines = []
        for j in journeys:
            steps = " → ".join(j.get("steps", []))
            pages = ", ".join(j.get("pages", []))
            lines.append(f"- {j['name']}：{steps}（涉及页面：{pages}）")
        return "\n".join(lines) if lines else "- 核心流程：开始 → 操作 → 完成"

    # ========== HTML 处理 ==========

    def _extract_and_validate_html(self, content: str) -> str:
        """从 LLM 输出中提取并验证 HTML"""
        html = self._extract_html(content)

        if html.strip().startswith("<!DOCTYPE") or html.strip().startswith("<html"):
            # 已是完整文档，确保有 Tailwind
            if "cdn.tailwindcss.com" not in html:
                html = html.replace("</head>", '<script src="https://cdn.tailwindcss.com"></script>\n</head>')
            return html

        return self._wrap_html(html)

    def _extract_html(self, content: str) -> str:
        """鲁棒提取 HTML 代码块"""
        match = re.search(r'```html\s*([\s\S]*?)\s*```', content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r'```\s*([\s\S]*?)\s*```', content)
        if match:
            candidate = match.group(1).strip()
            if "<" in candidate:
                return candidate

        for pattern in [r'(<html[\s\S]*?</html>)', r'(<body[\s\S]*?</body>)']:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        idx = content.find("<")
        if idx >= 0:
            return content[idx:].strip()

        return content

    def _wrap_html(self, html_code: str) -> str:
        """将裸 HTML 包装为完整文档"""
        tailwind = '<script src="https://cdn.tailwindcss.com"></script>'
        head_inject = tailwind if tailwind not in html_code else ""

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>产品原型</title>
    {head_inject}
</head>
<body class="bg-gray-50">
{html_code}
</body>
</html>"""

    # ========== 统计估算 ==========

    def _estimate_mock_data(self, skeleton: Dict[str, Any]) -> Dict[str, int]:
        """估算模拟数据量"""
        entities = skeleton.get("key_entities", [])
        return {entity: 20 for entity in entities} if entities else {"数据记录": 20}

    def _estimate_interactions(self, html_code: str) -> int:
        """估算交互点数量"""
        count = 0
        count += len(re.findall(r'onclick=', html_code))
        count += len(re.findall(r'addEventListener\(', html_code))
        count += len(re.findall(r'showToast|openModal|switchPage|toggleView|closeModal', html_code))
        count += len(re.findall(r'classList\.', html_code))
        return max(count, 5)

    # ========== 工具方法 ==========

    def _generate_cache_key(self, prefix: str, *parts) -> str:
        key_data = json.dumps(parts, sort_keys=True, default=str)
        return f"{prefix}:{hashlib.sha256(key_data.encode()).hexdigest()}"


# 全局实例
prototype_ai_service = PrototypeAIService()
