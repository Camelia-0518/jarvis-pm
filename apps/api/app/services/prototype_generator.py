"""
PRD转原型生成器
从PRD文档提取UI需求，生成HTML + Tailwind CSS原型代码
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ComponentType(Enum):
    """UI组件类型"""
    BUTTON = "button"
    INPUT = "input"
    SELECT = "select"
    TABLE = "table"
    CARD = "card"
    MODAL = "modal"
    FORM = "form"
    NAVIGATION = "navigation"
    SIDEBAR = "sidebar"
    HEADER = "header"
    FOOTER = "footer"
    CHART = "chart"
    LIST = "list"
    TABS = "tabs"
    DROPDOWN = "dropdown"
    SEARCH = "search"
    FILTER = "filter"
    PAGINATION = "pagination"
    UPLOAD = "upload"


@dataclass
class UIComponent:
    """UI组件定义"""
    type: ComponentType
    name: str
    label: Optional[str] = None
    placeholder: Optional[str] = None
    required: bool = False
    options: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    props: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageSection:
    """页面区块"""
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    components: List[UIComponent] = field(default_factory=list)
    layout: str = "vertical"  # vertical, horizontal, grid
    columns: int = 1


@dataclass
class Page:
    """页面定义"""
    name: str
    route: str
    title: str
    description: Optional[str] = None
    sections: List[PageSection] = field(default_factory=list)
    layout_type: str = "default"  # default, sidebar, fullwidth, centered
    authenticated: bool = True


@dataclass
class Interaction:
    """交互定义"""
    trigger: str  # click, hover, submit, change, load
    target: str
    action: str  # navigate, show, hide, validate, submit, modal
    params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class Prototype:
    """原型定义"""
    name: str
    description: str
    pages: List[Page] = field(default_factory=list)
    interactions: List[Interaction] = field(default_factory=list)
    global_components: List[UIComponent] = field(default_factory=list)
    theme: Dict[str, str] = field(default_factory=lambda: {
        "primary": "#3b82f6",
        "secondary": "#64748b",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "background": "#ffffff",
        "surface": "#f8fafc",
        "text": "#1e293b",
        "textMuted": "#64748b"
    })


class PRDParser:
    """PRD文档解析器"""

    # 页面识别模式
    PAGE_PATTERNS = [
        r'[#]+\s*页面[：:]?\s*([^\n]+)',
        r'[#]+\s*([^\n]+?)\s*页面',
        r'\*\*页面[：:]?\s*([^\*]+)\*\*',
        r'###\s*([^\n]+?)\s*(?:页面|界面|Screen|Page)',
    ]

    # 组件识别模式
    COMPONENT_PATTERNS = {
        ComponentType.BUTTON: [
            r'按钮[：:]?\s*([^\n，,]+)',
            r'(?:点击|提交|保存|删除|编辑|查看).*?按钮',
            r'button[:]?\s*([^\n]+)',
        ],
        ComponentType.INPUT: [
            r'输入框[：:]?\s*([^\n，,]+)',
            r'(?:输入|填写).*?框',
            r'(?:手机号|邮箱|姓名|密码|搜索).*?输入',
            r'input[:]?\s*([^\n]+)',
        ],
        ComponentType.SELECT: [
            r'下拉[框选][：:]?\s*([^\n，,]+)',
            r'选择器[：:]?\s*([^\n，,]+)',
            r'select[:]?\s*([^\n]+)',
        ],
        ComponentType.TABLE: [
            r'表格[：:]?\s*([^\n，,]+)',
            r'列表[：:]?\s*([^\n，,]+)',
            r'table[:]?\s*([^\n]+)',
            r'数据展示',
        ],
        ComponentType.CARD: [
            r'卡片[：:]?\s*([^\n，,]+)',
            r'card[:]?\s*([^\n]+)',
        ],
        ComponentType.MODAL: [
            r'弹窗[：:]?\s*([^\n，,]+)',
            r'对话框[：:]?\s*([^\n，,]+)',
            r'modal[:]?\s*([^\n]+)',
            r'dialog[:]?\s*([^\n]+)',
        ],
        ComponentType.FORM: [
            r'表单[：:]?\s*([^\n，,]+)',
            r'form[:]?\s*([^\n]+)',
        ],
        ComponentType.SEARCH: [
            r'搜索[框栏]?',
            r'search[:]?\s*([^\n]+)',
        ],
        ComponentType.NAVIGATION: [
            r'导航[栏菜单]?',
            r'nav[:]?\s*([^\n]+)',
        ],
        ComponentType.SIDEBAR: [
            r'侧边栏',
            r'sidebar[:]?\s*([^\n]+)',
        ],
        ComponentType.TABS: [
            r'标签页',
            r'选项卡',
            r'tabs[:]?\s*([^\n]+)',
        ],
        ComponentType.UPLOAD: [
            r'上传',
            r'文件选择',
            r'upload[:]?\s*([^\n]+)',
        ],
    }

    # 交互识别模式
    INTERACTION_PATTERNS = [
        r'点击([^，,]+?)(?:时|后)?，?([^\n]+)',
        r'当([^，,]+?)时，?([^\n]+)',
        r'([^\n]+?)后，?([^\n]+)',
    ]

    def __init__(self, prd_content: str):
        self.prd_content = prd_content
        self.lines = prd_content.split('\n')

    def parse(self) -> Prototype:
        """解析PRD文档"""
        # 提取项目名称和描述
        name = self._extract_project_name()
        description = self._extract_description()

        prototype = Prototype(name=name, description=description)

        # 提取页面
        pages = self._extract_pages()
        prototype.pages = pages

        # 提取全局交互
        interactions = self._extract_interactions()
        prototype.interactions = interactions

        return prototype

    def _extract_project_name(self) -> str:
        """提取项目名称"""
        patterns = [
            r'^#\s*([^\n]+)',
            r'项目名称[：:]\s*([^\n]+)',
            r'PRD[：:]?\s*([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.prd_content, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "未命名项目"

    def _extract_description(self) -> str:
        """提取项目描述"""
        patterns = [
            r'项目描述[：:]\s*([^#]+)',
            r'产品描述[：:]\s*([^#]+)',
            r'##\s*描述\s*\n([^#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.prd_content, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_pages(self) -> List[Page]:
        """提取页面列表"""
        pages = []

        # 尝试识别页面区块
        page_sections = self._split_into_page_sections()

        for section_name, section_content in page_sections:
            page = self._parse_page(section_name, section_content)
            if page:
                pages.append(page)

        # 如果没有识别到页面，创建默认页面
        if not pages:
            pages.append(self._create_default_page())

        return pages

    def _split_into_page_sections(self) -> List[tuple]:
        """将PRD内容分割成页面区块"""
        sections = []

        # 查找所有页面标题
        page_indices = []
        for i, line in enumerate(self.lines):
            for pattern in self.PAGE_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    page_indices.append(i)
                    break

        # 如果没有找到页面标题，尝试其他分割方式
        if not page_indices:
            # 查找功能模块
            for i, line in enumerate(self.lines):
                if re.match(r'^##\s+', line) and ('功能' in line or '模块' in line):
                    page_indices.append(i)

        # 分割内容
        if page_indices:
            for i, start_idx in enumerate(page_indices):
                end_idx = page_indices[i + 1] if i + 1 < len(page_indices) else len(self.lines)
                section_name = self.lines[start_idx].strip('# *')
                section_content = '\n'.join(self.lines[start_idx:end_idx])
                sections.append((section_name, section_content))
        else:
            # 整个文档作为一个页面
            sections.append(("主页面", self.prd_content))

        return sections

    def _parse_page(self, name: str, content: str) -> Optional[Page]:
        """解析单个页面"""
        # 生成路由
        route = self._generate_route(name)

        # 提取页面标题
        title = name.replace('页面', '').strip()

        # 提取页面区块
        sections = self._extract_page_sections(content)

        # 提取页面组件
        components = self._extract_components(content)

        return Page(
            name=name,
            route=route,
            title=title,
            sections=sections,
            description=self._extract_section_description(content)
        )

    def _generate_route(self, name: str) -> str:
        """生成路由路径"""
        # 移除常见后缀
        route = name.lower()
        route = re.sub(r'页面|界面|screen|page', '', route, flags=re.IGNORECASE)
        route = route.strip()

        # 转换为kebab-case
        route = re.sub(r'[^\w\s-]', '', route)
        route = re.sub(r'[-\s]+', '-', route)

        return f"/{route}" if route else "/"

    def _extract_page_sections(self, content: str) -> List[PageSection]:
        """提取页面区块"""
        sections = []

        # 查找区块标题
        section_pattern = r'^#{2,4}\s*([^\n]+)'
        matches = list(re.finditer(section_pattern, content, re.MULTILINE))

        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            section_content = content[start:end]

            # 提取区块组件
            components = self._extract_components(section_content)

            section = PageSection(
                name=section_name,
                components=components,
                description=self._extract_section_description(section_content)
            )
            sections.append(section)

        # 如果没有区块，创建一个默认区块
        if not sections:
            components = self._extract_components(content)
            sections.append(PageSection(
                name="主要内容",
                components=components
            ))

        return sections

    def _extract_components(self, content: str) -> List[UIComponent]:
        """提取UI组件"""
        components = []

        for comp_type, patterns in self.COMPONENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip() if match.groups() else comp_type.value

                    component = UIComponent(
                        type=comp_type,
                        name=name,
                        label=self._extract_label(content, match.start()),
                        placeholder=self._extract_placeholder(content, match.start()),
                        required=self._check_required(content, match.start()),
                        actions=self._extract_actions(content, match.end())
                    )
                    components.append(component)

        return components

    def _extract_label(self, content: str, position: int) -> Optional[str]:
        """提取标签文本"""
        # 向前查找标签
        before = content[max(0, position - 100):position]
        match = re.search(r'([^\n：:]+)[：:]\s*$', before)
        if match:
            return match.group(1).strip()
        return None

    def _extract_placeholder(self, content: str, position: int) -> Optional[str]:
        """提取占位符文本"""
        # 向后查找占位符提示
        after = content[position:min(len(content), position + 100)]
        match = re.search(r'占位符[：:]?\s*([^\n，,]+)', after)
        if match:
            return match.group(1).strip()
        return None

    def _check_required(self, content: str, position: int) -> bool:
        """检查是否为必填项"""
        around = content[max(0, position - 50):min(len(content), position + 50)]
        return bool(re.search(r'必填|必需|required|必选|\*', around, re.IGNORECASE))

    def _extract_actions(self, content: str, position: int) -> List[str]:
        """提取组件关联的操作"""
        after = content[position:min(len(content), position + 200)]
        actions = []

        action_patterns = [
            r'(?:点击|触发).*?(?:打开|跳转|显示|提交|保存|删除|编辑)',
            r'(?:打开|跳转|显示|提交|保存|删除|编辑).*?(?:页面|弹窗|数据)',
        ]

        for pattern in action_patterns:
            matches = re.finditer(pattern, after)
            for match in matches:
                actions.append(match.group(0))

        return actions

    def _extract_section_description(self, content: str) -> Optional[str]:
        """提取区块描述"""
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 10:
                return line[:200]
        return None

    def _extract_interactions(self) -> List[Interaction]:
        """提取交互定义"""
        interactions = []

        for pattern in self.INTERACTION_PATTERNS:
            matches = re.finditer(pattern, self.prd_content, re.IGNORECASE)
            for match in matches:
                trigger = match.group(1).strip()
                action_desc = match.group(2).strip()

                # 解析动作
                action = self._parse_action(action_desc)

                interaction = Interaction(
                    trigger=self._normalize_trigger(trigger),
                    target=trigger,
                    action=action,
                    params=self._extract_action_params(action_desc)
                )
                interactions.append(interaction)

        return interactions

    def _normalize_trigger(self, trigger: str) -> str:
        """规范化触发器名称"""
        trigger_map = {
            '点击': 'click',
            '双击': 'dblclick',
            '悬停': 'hover',
            '鼠标移入': 'mouseenter',
            '鼠标移出': 'mouseleave',
            '输入': 'input',
            '改变': 'change',
            '提交': 'submit',
            '加载': 'load',
            '滚动': 'scroll',
        }
        for cn, en in trigger_map.items():
            if cn in trigger:
                return en
        return 'click'

    def _parse_action(self, action_desc: str) -> str:
        """解析动作类型"""
        action_keywords = {
            'navigate': ['跳转', '打开页面', '前往', '切换到'],
            'show': ['显示', '展示', '出现', '展开'],
            'hide': ['隐藏', '收起', '关闭', '消失'],
            'submit': ['提交', '保存', '发送'],
            'validate': ['验证', '校验', '检查'],
            'modal': ['弹窗', '对话框', 'modal'],
            'delete': ['删除', '移除'],
            'edit': ['编辑', '修改'],
        }

        for action, keywords in action_keywords.items():
            for keyword in keywords:
                if keyword in action_desc:
                    return action

        return 'navigate'

    def _extract_action_params(self, action_desc: str) -> Dict[str, Any]:
        """提取动作参数"""
        params = {}

        # 提取URL/路径
        url_match = re.search(r'["\']?(/[^"\'\s]+)["\']?', action_desc)
        if url_match:
            params['url'] = url_match.group(1)

        # 提取页面名称
        page_match = re.search(r'["\']?([^"\']*?页面)["\']?', action_desc)
        if page_match:
            params['page'] = page_match.group(1)

        return params

    def _create_default_page(self) -> Page:
        """创建默认页面"""
        return Page(
            name="首页",
            route="/",
            title="首页",
            sections=[PageSection(
                name="主要内容",
                components=self._extract_components(self.prd_content)
            )]
        )


class PrototypeGenerator:
    """原型代码生成器"""

    def __init__(self, prototype: Prototype):
        self.prototype = prototype

    def generate(self) -> Dict[str, str]:
        """生成完整的原型代码"""
        return {
            "index.html": self._generate_main_html(),
            "styles.css": self._generate_styles(),
            "scripts.js": self._generate_scripts(),
            "preview.html": self._generate_preview(),
        }

    def _generate_main_html(self) -> str:
        """生成主HTML文件"""
        pages_html = []

        for page in self.prototype.pages:
            page_html = self._generate_page_html(page)
            pages_html.append(page_html)

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.prototype.name} - 原型</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="styles.css">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '{self.prototype.theme.get("primary", "#3b82f6")}',
                        secondary: '{self.prototype.theme.get("secondary", "#64748b")}',
                        success: '{self.prototype.theme.get("success", "#22c55e")}',
                        warning: '{self.prototype.theme.get("warning", "#f59e0b")}',
                        danger: '{self.prototype.theme.get("danger", "#ef4444")}',
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-gray-50 text-gray-900">
    <!-- 导航栏 -->
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-bold text-primary">{self.prototype.name}</h1>
                </div>
                <div class="flex items-center space-x-4">
                    {self._generate_nav_links()}
                </div>
            </div>
        </div>
    </nav>

    <!-- 页面内容 -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {''.join(pages_html)}
    </main>

    <!-- 页脚 -->
    <footer class="bg-white border-t mt-12">
        <div class="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500">
            <p>© 2024 {self.prototype.name} - 原型预览</p>
        </div>
    </footer>

    <script src="scripts.js"></script>
</body>
</html>'''

    def _generate_nav_links(self) -> str:
        """生成导航链接"""
        links = []
        for page in self.prototype.pages:
            links.append(f'<a href="#{page.route[1:]}" class="text-gray-600 hover:text-primary px-3 py-2 rounded-md text-sm font-medium">{page.title}</a>')
        return '\n                    '.join(links)

    def _generate_page_html(self, page: Page) -> str:
        """生成单个页面HTML"""
        sections_html = []

        for section in page.sections:
            section_html = self._generate_section_html(section)
            sections_html.append(section_html)

        return f'''
        <!-- {page.name} -->
        <section id="{page.route[1:]}" class="page-section mb-12" data-route="{page.route}">
            <div class="mb-6">
                <h2 class="text-2xl font-bold text-gray-900">{page.title}</h2>
                {f'<p class="mt-2 text-gray-600">{page.description}</p>' if page.description else ''}
            </div>
            {''.join(sections_html)}
        </section>
        '''

    def _generate_section_html(self, section: PageSection) -> str:
        """生成区块HTML"""
        components_html = []

        for component in section.components:
            comp_html = self._generate_component_html(component)
            components_html.append(comp_html)

        layout_class = self._get_layout_class(section.layout, section.columns)

        return f'''
        <div class="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">{section.name}</h3>
            {f'<p class="text-sm text-gray-500 mb-4">{section.description}</p>' if section.description else ''}
            <div class="{layout_class}">
                {''.join(components_html)}
            </div>
        </div>
        '''

    def _generate_component_html(self, component: UIComponent) -> str:
        """生成组件HTML"""
        generators = {
            ComponentType.BUTTON: self._generate_button,
            ComponentType.INPUT: self._generate_input,
            ComponentType.SELECT: self._generate_select,
            ComponentType.TABLE: self._generate_table,
            ComponentType.CARD: self._generate_card,
            ComponentType.MODAL: self._generate_modal,
            ComponentType.FORM: self._generate_form,
            ComponentType.SEARCH: self._generate_search,
            ComponentType.NAVIGATION: self._generate_navigation,
            ComponentType.TABS: self._generate_tabs,
            ComponentType.UPLOAD: self._generate_upload,
        }

        generator = generators.get(component.type, self._generate_generic)
        return generator(component)

    def _generate_button(self, component: UIComponent) -> str:
        """生成按钮"""
        variant = component.props.get('variant', 'primary')
        size = component.props.get('size', 'md')

        variant_classes = {
            'primary': 'bg-primary text-white hover:bg-blue-600',
            'secondary': 'bg-gray-200 text-gray-800 hover:bg-gray-300',
            'success': 'bg-success text-white hover:bg-green-600',
            'danger': 'bg-danger text-white hover:bg-red-600',
            'ghost': 'bg-transparent text-gray-600 hover:bg-gray-100',
        }

        size_classes = {
            'sm': 'px-3 py-1.5 text-sm',
            'md': 'px-4 py-2 text-base',
            'lg': 'px-6 py-3 text-lg',
        }

        class_name = f"{variant_classes.get(variant, variant_classes['primary'])} {size_classes.get(size, size_classes['md'])} rounded-lg font-medium transition-colors"

        return f'<button class="{class_name}" data-action="{component.name}">{component.label or component.name}</button>'

    def _generate_input(self, component: UIComponent) -> str:
        """生成输入框"""
        required_attr = 'required' if component.required else ''
        placeholder = component.placeholder or f"请输入{component.label or component.name}"

        return f'''
        <div class="form-group">
            <label class="block text-sm font-medium text-gray-700 mb-1">
                {component.label or component.name}
                {'<span class="text-danger">*</span>' if component.required else ''}
            </label>
            <input type="text"
                   class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
                   placeholder="{placeholder}"
                   {required_attr}
                   data-field="{component.name}">
        </div>
        '''

    def _generate_select(self, component: UIComponent) -> str:
        """生成下拉选择"""
        options_html = ''
        for option in component.options or ['选项1', '选项2', '选项3']:
            options_html += f'<option value="{option}">{option}</option>'

        return f'''
        <div class="form-group">
            <label class="block text-sm font-medium text-gray-700 mb-1">
                {component.label or component.name}
                {'<span class="text-danger">*</span>' if component.required else ''}
            </label>
            <select class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
                    data-field="{component.name}">
                <option value="">请选择</option>
                {options_html}
            </select>
        </div>
        '''

    def _generate_table(self, component: UIComponent) -> str:
        """生成表格"""
        columns = component.props.get('columns', ['列1', '列2', '列3'])
        headers_html = ''.join([f'<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{col}</th>' for col in columns])

        # 生成示例数据行
        rows_html = ''
        for i in range(3):
            cells_html = ''.join([f'<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">数据{i+1}-{j+1}</td>' for j in range(len(columns))])
            rows_html += f'<tr class="hover:bg-gray-50">{cells_html}</tr>'

        return f'''
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>{headers_html}</tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {rows_html}
                </tbody>
            </table>
        </div>
        '''

    def _generate_card(self, component: UIComponent) -> str:
        """生成卡片"""
        return f'''
        <div class="bg-white rounded-lg shadow border p-6 hover:shadow-md transition-shadow">
            <h4 class="text-lg font-semibold text-gray-900 mb-2">{component.label or component.name}</h4>
            <p class="text-gray-600">{component.placeholder or '卡片内容描述'}</p>
        </div>
        '''

    def _generate_modal(self, component: UIComponent) -> str:
        """生成弹窗"""
        return f'''
        <div class="modal hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" data-modal="{component.name}">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                <div class="flex justify-between items-center p-6 border-b">
                    <h3 class="text-lg font-semibold">{component.label or component.name}</h3>
                    <button class="modal-close text-gray-400 hover:text-gray-600">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div class="p-6">
                    <p class="text-gray-600">{component.placeholder or '弹窗内容'}</p>
                </div>
                <div class="flex justify-end space-x-3 p-6 border-t bg-gray-50 rounded-b-lg">
                    <button class="modal-close px-4 py-2 text-gray-600 hover:text-gray-800">取消</button>
                    <button class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600">确认</button>
                </div>
            </div>
        </div>
        '''

    def _generate_form(self, component: UIComponent) -> str:
        """生成表单容器"""
        return f'''
        <form class="space-y-4" data-form="{component.name}">
            <div class="form-content">
                <!-- 表单字段将通过组件生成 -->
            </div>
            <div class="flex justify-end space-x-3 pt-4">
                <button type="button" class="px-4 py-2 text-gray-600 hover:text-gray-800">取消</button>
                <button type="submit" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600">提交</button>
            </div>
        </form>
        '''

    def _generate_search(self, component: UIComponent) -> str:
        """生成搜索框"""
        return f'''
        <div class="relative">
            <input type="text"
                   class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
                   placeholder="{component.placeholder or '搜索...'}">
            <svg class="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
        </div>
        '''

    def _generate_navigation(self, component: UIComponent) -> str:
        """生成导航"""
        return f'''
        <nav class="flex space-x-4">
            <a href="#" class="text-primary font-medium">首页</a>
            <a href="#" class="text-gray-600 hover:text-primary">功能</a>
            <a href="#" class="text-gray-600 hover:text-primary">关于</a>
        </nav>
        '''

    def _generate_tabs(self, component: UIComponent) -> str:
        """生成标签页"""
        tabs = component.options or ['标签1', '标签2', '标签3']
        tabs_html = ''
        for i, tab in enumerate(tabs):
            active = 'border-primary text-primary' if i == 0 else 'border-transparent text-gray-500 hover:text-gray-700'
            tabs_html += f'<button class="tab-btn py-2 px-4 border-b-2 font-medium text-sm {active}" data-tab="{i}">{tab}</button>'

        return f'''
        <div class="tabs">
            <div class="border-b border-gray-200">
                <nav class="-mb-px flex space-x-8">{tabs_html}</nav>
            </div>
            <div class="tab-content py-4">
                <!-- 标签内容 -->
            </div>
        </div>
        '''

    def _generate_upload(self, component: UIComponent) -> str:
        """生成上传组件"""
        return f'''
        <div class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary transition-colors cursor-pointer">
            <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
            <p class="mt-2 text-sm text-gray-600">点击上传或拖拽文件到此处</p>
            <p class="text-xs text-gray-500">支持 PDF, Word, Excel 格式</p>
        </div>
        '''

    def _generate_generic(self, component: UIComponent) -> str:
        """生成通用组件"""
        return f'<div class="p-4 bg-gray-50 rounded-lg">{component.label or component.name}</div>'

    def _get_layout_class(self, layout: str, columns: int) -> str:
        """获取布局类名"""
        if layout == 'horizontal':
            return 'flex flex-wrap gap-4'
        elif layout == 'grid':
            return f'grid grid-cols-1 md:grid-cols-{columns} gap-4'
        else:
            return 'space-y-4'

    def _generate_styles(self) -> str:
        """生成CSS样式"""
        return '''/* 原型样式 */
.page-section {
    display: none;
}

.page-section.active {
    display: block;
}

/* 表单验证样式 */
.form-group.error input,
.form-group.error select {
    border-color: #ef4444;
}

.form-group .error-message {
    color: #ef4444;
    font-size: 0.875rem;
    margin-top: 0.25rem;
}

/* 模态框动画 */
.modal {
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s, visibility 0.3s;
}

.modal.show {
    opacity: 1;
    visibility: visible;
}

.modal > div {
    transform: scale(0.95);
    transition: transform 0.3s;
}

.modal.show > div {
    transform: scale(1);
}

/* 标签页样式 */
.tab-content > div {
    display: none;
}

.tab-content > div.active {
    display: block;
}

/* 响应式调整 */
@media (max-width: 640px) {
    .page-section {
        padding: 1rem;
    }
}

/* 打印样式 */
@media print {
    nav, footer, .modal {
        display: none !important;
    }

    .page-section {
        display: block !important;
        page-break-after: always;
    }
}
'''

    def _generate_scripts(self) -> str:
        """生成JavaScript代码"""
        interactions_js = self._generate_interactions_js()

        return f'''// 原型交互脚本
document.addEventListener('DOMContentLoaded', function() {{
    // 初始化路由
    initRouting();

    // 初始化交互
    initInteractions();

    // 初始化表单验证
    initFormValidation();

    // 初始化模态框
    initModals();

    // 初始化标签页
    initTabs();
}});

// 路由管理
function initRouting() {{
    // 显示默认页面
    showPage(window.location.hash.slice(1) || '{self.prototype.pages[0].route[1:] if self.prototype.pages else "home"}');

    // 监听hash变化
    window.addEventListener('hashchange', function() {{
        showPage(window.location.hash.slice(1));
    }});
}}

function showPage(pageId) {{
    // 隐藏所有页面
    document.querySelectorAll('.page-section').forEach(function(page) {{
        page.classList.remove('active');
    }});

    // 显示目标页面
    const targetPage = document.getElementById(pageId);
    if (targetPage) {{
        targetPage.classList.add('active');
    }} else {{
        // 显示第一个页面
        const firstPage = document.querySelector('.page-section');
        if (firstPage) firstPage.classList.add('active');
    }}
}}

// 交互管理
function initInteractions() {{
    {interactions_js}

    // 按钮点击反馈
    document.querySelectorAll('button[data-action]').forEach(function(btn) {{
        btn.addEventListener('click', function(e) {{
            const action = this.getAttribute('data-action');
            console.log('Action triggered:', action);

            // 显示Toast提示
            showToast('操作: ' + action);
        }});
    }});
}}

// 表单验证
function initFormValidation() {{
    document.querySelectorAll('form').forEach(function(form) {{
        form.addEventListener('submit', function(e) {{
            e.preventDefault();

            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');

            requiredFields.forEach(function(field) {{
                const formGroup = field.closest('.form-group');

                if (!field.value.trim()) {{
                    isValid = false;
                    formGroup.classList.add('error');

                    // 添加错误提示
                    let errorMsg = formGroup.querySelector('.error-message');
                    if (!errorMsg) {{
                        errorMsg = document.createElement('p');
                        errorMsg.className = 'error-message';
                        formGroup.appendChild(errorMsg);
                    }}
                    errorMsg.textContent = '此字段为必填项';
                }} else {{
                    formGroup.classList.remove('error');
                    const errorMsg = formGroup.querySelector('.error-message');
                    if (errorMsg) errorMsg.remove();
                }}
            }});

            if (isValid) {{
                showToast('表单提交成功！', 'success');
            }}
        }});
    }});
}}

// 模态框管理
function initModals() {{
    // 打开模态框
    document.querySelectorAll('[data-modal-target]').forEach(function(trigger) {{
        trigger.addEventListener('click', function() {{
            const modalId = this.getAttribute('data-modal-target');
            const modal = document.querySelector('[data-modal="' + modalId + '"]');
            if (modal) modal.classList.add('show');
        }});
    }});

    // 关闭模态框
    document.querySelectorAll('.modal-close').forEach(function(closeBtn) {{
        closeBtn.addEventListener('click', function() {{
            const modal = this.closest('.modal');
            if (modal) modal.classList.remove('show');
        }});
    }});

    // 点击背景关闭
    document.querySelectorAll('.modal').forEach(function(modal) {{
        modal.addEventListener('click', function(e) {{
            if (e.target === this) {{
                this.classList.remove('show');
            }}
        }});
    }});
}}

// 标签页管理
function initTabs() {{
    document.querySelectorAll('.tabs').forEach(function(tabContainer) {{
        const tabBtns = tabContainer.querySelectorAll('.tab-btn');
        const tabContents = tabContainer.querySelectorAll('.tab-content > div');

        tabBtns.forEach(function(btn, index) {{
            btn.addEventListener('click', function() {{
                // 移除所有活动状态
                tabBtns.forEach(function(b) {{
                    b.classList.remove('border-primary', 'text-primary');
                    b.classList.add('border-transparent', 'text-gray-500');
                }});
                tabContents.forEach(function(c) {{
                    c.classList.remove('active');
                }});

                // 激活当前标签
                this.classList.remove('border-transparent', 'text-gray-500');
                this.classList.add('border-primary', 'text-primary');
                if (tabContents[index]) tabContents[index].classList.add('active');
            }});
        }});
    }});
}}

// Toast提示
function showToast(message, type = 'info') {{
    const toast = document.createElement('div');
    const colors = {{
        info: 'bg-gray-800',
        success: 'bg-success',
        warning: 'bg-warning',
        error: 'bg-danger'
    }};

    toast.className = `fixed bottom-4 right-4 ${{colors[type] || colors.info}} text-white px-6 py-3 rounded-lg shadow-lg z-50 transform translate-y-0 transition-transform`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(function() {{
        toast.style.transform = 'translateY(100px)';
        setTimeout(function() {{
            toast.remove();
        }}, 300);
    }}, 3000);
}}
'''

    def _generate_interactions_js(self) -> str:
        """生成交互JS代码"""
        js_lines = []

        for interaction in self.prototype.interactions:
            if interaction.action == 'navigate':
                js_lines.append(f'''
    // {interaction.target} -> 导航
    document.querySelectorAll('[data-action="{interaction.target}"]').forEach(function(el) {{
        el.addEventListener('click', function() {{
            window.location.hash = '{interaction.params.get('url', '')}';
        }});
    }});''')
            elif interaction.action == 'modal':
                js_lines.append(f'''
    // {interaction.target} -> 弹窗
    document.querySelectorAll('[data-action="{interaction.target}"]').forEach(function(el) {{
        el.addEventListener('click', function() {{
            const modal = document.querySelector('[data-modal="{interaction.params.get('modal', 'default')}"]');
            if (modal) modal.classList.add('show');
        }});
    }});''')

        return '\n'.join(js_lines) if js_lines else '// 暂无特定交互'

    def _generate_preview(self) -> str:
        """生成预览页面"""
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.prototype.name} - 原型预览</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; }}
        .preview-container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .preview-header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .preview-header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .preview-header p {{ color: #666; }}
        .device-selector {{ margin-top: 16px; }}
        .device-btn {{ padding: 8px 16px; margin-right: 8px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; }}
        .device-btn.active {{ background: #3b82f6; color: white; border-color: #3b82f6; }}
        .preview-frame-container {{ background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
        .preview-frame {{ width: 100%; height: 800px; border: none; transition: width 0.3s; }}
        .preview-frame.mobile {{ width: 375px; margin: 0 auto; }}
        .preview-frame.tablet {{ width: 768px; margin: 0 auto; }}
        .export-actions {{ margin-top: 20px; text-align: center; }}
        .export-btn {{ padding: 12px 24px; margin: 0 8px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }}
        .export-btn:hover {{ background: #2563eb; }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="preview-header">
            <h1>{self.prototype.name}</h1>
            <p>{self.prototype.description or '原型预览'}</p>
            <div class="device-selector">
                <button class="device-btn active" onclick="setDevice('desktop')">桌面端</button>
                <button class="device-btn" onclick="setDevice('tablet')">平板</button>
                <button class="device-btn" onclick="setDevice('mobile')">手机</button>
            </div>
        </div>

        <div class="preview-frame-container">
            <iframe src="index.html" class="preview-frame" id="previewFrame"></iframe>
        </div>

        <div class="export-actions">
            <button class="export-btn" onclick="exportHTML()">导出 HTML</button>
            <button class="export-btn" onclick="exportZip()">导出 ZIP</button>
            <button class="export-btn" onclick="deployPreview()">部署预览</button>
        </div>
    </div>

    <script>
        function setDevice(device) {{
            const frame = document.getElementById('previewFrame');
            const btns = document.querySelectorAll('.device-btn');

            btns.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            frame.className = 'preview-frame ' + device;
        }}

        function exportHTML() {{
            alert('导出功能：将下载完整的HTML原型文件');
        }}

        function exportZip() {{
            alert('导出功能：将下载ZIP压缩包（包含所有原型文件）');
        }}

        function deployPreview() {{
            alert('部署功能：将原型部署到预览服务器');
        }}
    </script>
</body>
</html>'''


# API接口函数
def generate_prototype_from_prd(prd_content: str) -> Dict[str, str]:
    """
    从PRD内容生成原型

    Args:
        prd_content: PRD文档内容

    Returns:
        包含所有原型文件的字典
    """
    # 解析PRD
    parser = PRDParser(prd_content)
    prototype = parser.parse()

    # 生成代码
    generator = PrototypeGenerator(prototype)
    files = generator.generate()

    return {
        "files": files,
        "metadata": {
            "name": prototype.name,
            "description": prototype.description,
            "page_count": len(prototype.pages),
            "pages": [{"name": p.name, "route": p.route, "title": p.title} for p in prototype.pages],
        }
    }


def extract_ui_requirements(prd_content: str) -> Dict[str, Any]:
    """
    从PRD提取UI需求

    Args:
        prd_content: PRD文档内容

    Returns:
        UI需求结构化数据
    """
    parser = PRDParser(prd_content)
    prototype = parser.parse()

    return {
        "project_name": prototype.name,
        "description": prototype.description,
        "pages": [
            {
                "name": p.name,
                "route": p.route,
                "title": p.title,
                "description": p.description,
                "sections": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "components": [
                            {
                                "type": c.type.value,
                                "name": c.name,
                                "label": c.label,
                                "required": c.required,
                                "actions": c.actions,
                            }
                            for c in s.components
                        ]
                    }
                    for s in p.sections
                ]
            }
            for p in prototype.pages
        ],
        "interactions": [
            {
                "trigger": i.trigger,
                "target": i.target,
                "action": i.action,
                "params": i.params,
            }
            for i in prototype.interactions
        ],
        "theme": prototype.theme,
    }
