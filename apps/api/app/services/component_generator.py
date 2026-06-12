"""
前端组件生成器
从PRD识别UI组件需求，生成React组件代码
"""

import re

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ComponentCategory(Enum):
    """组件类别"""
    FORM = "form"
    DATA_DISPLAY = "data_display"
    FEEDBACK = "feedback"
    NAVIGATION = "navigation"
    OVERLAY = "overlay"
    LAYOUT = "layout"
    GENERAL = "general"


class PropType(Enum):
    """Prop类型"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    FUNCTION = "function"
    ARRAY = "array"
    OBJECT = "object"
    NODE = "node"
    ELEMENT = "element"
    ANY = "any"
    LITERAL = "literal"


@dataclass
class PropDefinition:
    """Prop定义"""
    name: str
    type: PropType
    required: bool = False
    default_value: Any = None
    description: str = ""
    enum_values: List[str] = field(default_factory=list)


@dataclass
class ComponentDefinition:
    """组件定义"""
    name: str
    category: ComponentCategory
    description: str = ""
    props: List[PropDefinition] = field(default_factory=list)
    children_accepted: bool = False
    events: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    styles: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentTest:
    """组件测试定义"""
    name: str
    description: str
    props: Dict[str, Any] = field(default_factory=dict)
    assertions: List[str] = field(default_factory=list)


@dataclass
class ComponentPackage:
    """组件包"""
    component: ComponentDefinition
    code: str
    test_code: str
    story_code: Optional[str] = None
    types_code: Optional[str] = None
    index_code: str = ""


class PRDComponentExtractor:
    """PRD组件提取器"""

    # 组件识别模式
    COMPONENT_PATTERNS = {
        # 表单组件
        'Button': [
            r'按钮[：:]?\s*([^\n，,]+)',
            r'(?:提交|保存|删除|编辑|取消|确认).*?按钮',
            r'button[:]?\s*([^\n]+)',
        ],
        'Input': [
            r'输入框[：:]?\s*([^\n，,]+)',
            r'(?:文本|文字)输入',
            r'input[:]?\s*([^\n]+)',
        ],
        'TextArea': [
            r'(?:多行|文本域).*?输入',
            r'textarea[:]?\s*([^\n]+)',
        ],
        'Select': [
            r'下拉[框选][：:]?\s*([^\n，,]+)',
            r'选择器[：:]?\s*([^\n，,]+)',
            r'select[:]?\s*([^\n]+)',
        ],
        'Checkbox': [
            r'复选框',
            r'多选框',
            r'checkbox[:]?\s*([^\n]+)',
        ],
        'Radio': [
            r'单选[按钮框]?',
            r'radio[:]?\s*([^\n]+)',
        ],
        'Switch': [
            r'开关',
            r'switch[:]?\s*([^\n]+)',
        ],
        'DatePicker': [
            r'日期选择[器]?',
            r'datepicker[:]?\s*([^\n]+)',
        ],
        'Form': [
            r'表单[：:]?\s*([^\n，,]+)',
            r'form[:]?\s*([^\n]+)',
        ],
        'Upload': [
            r'上传[组件]?',
            r'文件选择',
            r'upload[:]?\s*([^\n]+)',
        ],

        # 数据展示
        'Table': [
            r'表格[：:]?\s*([^\n，,]+)',
            r'数据表',
            r'table[:]?\s*([^\n]+)',
        ],
        'List': [
            r'列表[：:]?\s*([^\n，,]+)',
            r'list[:]?\s*([^\n]+)',
        ],
        'Card': [
            r'卡片[：:]?\s*([^\n，,]+)',
            r'card[:]?\s*([^\n]+)',
        ],
        'Badge': [
            r'徽标',
            r'标签[（(]badge[)）]',
            r'badge[:]?\s*([^\n]+)',
        ],
        'Avatar': [
            r'头像',
            r'avatar[:]?\s*([^\n]+)',
        ],
        'Tag': [
            r'标签[：:]?\s*([^\n，,（(]+)',
            r'tag[:]?\s*([^\n]+)',
        ],
        'Progress': [
            r'进度条',
            r'progress[:]?\s*([^\n]+)',
        ],
        'Statistic': [
            r'统计[数值]?',
            r'statistic[:]?\s*([^\n]+)',
        ],
        'Timeline': [
            r'时间轴',
            r'timeline[:]?\s*([^\n]+)',
        ],
        'Tree': [
            r'树[形]?',
            r'tree[:]?\s*([^\n]+)',
        ],
        'Calendar': [
            r'日历',
            r'calendar[:]?\s*([^\n]+)',
        ],

        # 反馈组件
        'Alert': [
            r'警告提示',
            r'alert[:]?\s*([^\n]+)',
        ],
        'Message': [
            r'消息提示',
            r'message[:]?\s*([^\n]+)',
        ],
        'Modal': [
            r'[对话框弹窗][：:]?\s*([^\n，,]+)',
            r'modal[:]?\s*([^\n]+)',
            r'dialog[:]?\s*([^\n]+)',
        ],
        'Drawer': [
            r'抽屉',
            r'drawer[:]?\s*([^\n]+)',
        ],
        'Notification': [
            r'通知提醒',
            r'notification[:]?\s*([^\n]+)',
        ],
        'Popconfirm': [
            r'气泡确认',
            r'popconfirm[:]?\s*([^\n]+)',
        ],
        'Loading': [
            r'加载[中]?',
            r'loading[:]?\s*([^\n]+)',
        ],
        'Skeleton': [
            r'骨架屏',
            r'skeleton[:]?\s*([^\n]+)',
        ],
        'Empty': [
            r'空状态',
            r'empty[:]?\s*([^\n]+)',
        ],
        'Result': [
            r'结果页',
            r'result[:]?\s*([^\n]+)',
        ],

        # 导航组件
        'Menu': [
            r'菜单[栏]?',
            r'menu[:]?\s*([^\n]+)',
        ],
        'Tabs': [
            r'标签页',
            r'选项卡',
            r'tabs[:]?\s*([^\n]+)',
        ],
        'Breadcrumb': [
            r'面包屑',
            r'breadcrumb[:]?\s*([^\n]+)',
        ],
        'Dropdown': [
            r'下拉菜单',
            r'dropdown[:]?\s*([^\n]+)',
        ],
        'Pagination': [
            r'分页[器]?',
            r'pagination[:]?\s*([^\n]+)',
        ],
        'Steps': [
            r'步骤条',
            r'steps[:]?\s*([^\n]+)',
        ],
        'Anchor': [
            r'锚点',
            r'anchor[:]?\s*([^\n]+)',
        ],

        # 遮罩层
        'Tooltip': [
            r'文字提示',
            r'tooltip[:]?\s*([^\n]+)',
        ],
        'Popover': [
            r'气泡卡片',
            r'popover[:]?\s*([^\n]+)',
        ],

        # 布局组件
        'Layout': [
            r'布局',
            r'layout[:]?\s*([^\n]+)',
        ],
        'Grid': [
            r'栅格',
            r'grid[:]?\s*([^\n]+)',
        ],
        'Space': [
            r'间距',
            r'space[:]?\s*([^\n]+)',
        ],
        'Divider': [
            r'分割线',
            r'divider[:]?\s*([^\n]+)',
        ],

        # 通用组件
        'Search': [
            r'搜索[框栏]?',
            r'search[:]?\s*([^\n]+)',
        ],
        'Filter': [
            r'筛选[器条件]?',
            r'filter[:]?\s*([^\n]+)',
        ],
        'Sort': [
            r'排序',
            r'sort[:]?\s*([^\n]+)',
        ],
    }

    # 类别映射
    CATEGORY_MAP = {
        'Button': ComponentCategory.FORM,
        'Input': ComponentCategory.FORM,
        'TextArea': ComponentCategory.FORM,
        'Select': ComponentCategory.FORM,
        'Checkbox': ComponentCategory.FORM,
        'Radio': ComponentCategory.FORM,
        'Switch': ComponentCategory.FORM,
        'DatePicker': ComponentCategory.FORM,
        'Form': ComponentCategory.FORM,
        'Upload': ComponentCategory.FORM,

        'Table': ComponentCategory.DATA_DISPLAY,
        'List': ComponentCategory.DATA_DISPLAY,
        'Card': ComponentCategory.DATA_DISPLAY,
        'Badge': ComponentCategory.DATA_DISPLAY,
        'Avatar': ComponentCategory.DATA_DISPLAY,
        'Tag': ComponentCategory.DATA_DISPLAY,
        'Progress': ComponentCategory.DATA_DISPLAY,
        'Statistic': ComponentCategory.DATA_DISPLAY,
        'Timeline': ComponentCategory.DATA_DISPLAY,
        'Tree': ComponentCategory.DATA_DISPLAY,
        'Calendar': ComponentCategory.DATA_DISPLAY,

        'Alert': ComponentCategory.FEEDBACK,
        'Message': ComponentCategory.FEEDBACK,
        'Modal': ComponentCategory.FEEDBACK,
        'Drawer': ComponentCategory.FEEDBACK,
        'Notification': ComponentCategory.FEEDBACK,
        'Popconfirm': ComponentCategory.FEEDBACK,
        'Loading': ComponentCategory.FEEDBACK,
        'Skeleton': ComponentCategory.FEEDBACK,
        'Empty': ComponentCategory.FEEDBACK,
        'Result': ComponentCategory.FEEDBACK,

        'Menu': ComponentCategory.NAVIGATION,
        'Tabs': ComponentCategory.NAVIGATION,
        'Breadcrumb': ComponentCategory.NAVIGATION,
        'Dropdown': ComponentCategory.NAVIGATION,
        'Pagination': ComponentCategory.NAVIGATION,
        'Steps': ComponentCategory.NAVIGATION,
        'Anchor': ComponentCategory.NAVIGATION,

        'Tooltip': ComponentCategory.OVERLAY,
        'Popover': ComponentCategory.OVERLAY,

        'Layout': ComponentCategory.LAYOUT,
        'Grid': ComponentCategory.LAYOUT,
        'Space': ComponentCategory.LAYOUT,
        'Divider': ComponentCategory.LAYOUT,

        'Search': ComponentCategory.GENERAL,
        'Filter': ComponentCategory.GENERAL,
        'Sort': ComponentCategory.GENERAL,
    }

    def __init__(self, prd_content: str):
        self.prd_content = prd_content

    def extract(self) -> List[ComponentDefinition]:
        """提取组件定义列表"""
        components = []
        found_components = set()

        for comp_name, patterns in self.COMPONENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, self.prd_content, re.IGNORECASE)
                for match in matches:
                    if comp_name not in found_components:
                        component = self._create_component_definition(comp_name, match)
                        components.append(component)
                        found_components.add(comp_name)
                        break

        return components

    def _create_component_definition(self, comp_name: str, match: re.Match) -> ComponentDefinition:
        """创建组件定义"""
        category = self.CATEGORY_MAP.get(comp_name, ComponentCategory.GENERAL)

        # 提取描述
        description = self._extract_description(comp_name)

        # 生成Props
        props = self._generate_props(comp_name)

        # 确定是否接受children
        children_accepted = comp_name in ['Card', 'Modal', 'Drawer', 'Layout', 'Form', 'Alert']

        # 提取事件
        events = self._extract_events(comp_name)

        # 依赖
        dependencies = self._get_dependencies(comp_name)

        return ComponentDefinition(
            name=comp_name,
            category=category,
            description=description,
            props=props,
            children_accepted=children_accepted,
            events=events,
            dependencies=dependencies,
        )

    def _extract_description(self, comp_name: str) -> str:
        """提取组件描述"""
        descriptions = {
            'Button': '按钮用于触发操作或事件',
            'Input': '输入框用于接收用户输入',
            'TextArea': '多行文本输入框',
            'Select': '下拉选择器',
            'Checkbox': '复选框',
            'Radio': '单选按钮',
            'Switch': '开关选择器',
            'DatePicker': '日期选择器',
            'Form': '表单容器',
            'Upload': '文件上传',
            'Table': '数据表格',
            'List': '列表',
            'Card': '卡片容器',
            'Badge': '徽标',
            'Avatar': '头像',
            'Tag': '标签',
            'Progress': '进度条',
            'Statistic': '统计数值',
            'Timeline': '时间轴',
            'Tree': '树形控件',
            'Calendar': '日历',
            'Alert': '警告提示',
            'Message': '消息提示',
            'Modal': '对话框',
            'Drawer': '抽屉',
            'Notification': '通知提醒',
            'Popconfirm': '气泡确认框',
            'Loading': '加载中',
            'Skeleton': '骨架屏',
            'Empty': '空状态',
            'Result': '结果页',
            'Menu': '导航菜单',
            'Tabs': '标签页',
            'Breadcrumb': '面包屑',
            'Dropdown': '下拉菜单',
            'Pagination': '分页器',
            'Steps': '步骤条',
            'Anchor': '锚点',
            'Tooltip': '文字提示',
            'Popover': '气泡卡片',
            'Layout': '布局容器',
            'Grid': '栅格系统',
            'Space': '间距',
            'Divider': '分割线',
            'Search': '搜索框',
            'Filter': '筛选器',
            'Sort': '排序',
        }
        return descriptions.get(comp_name, f'{comp_name}组件')

    def _generate_props(self, comp_name: str) -> List[PropDefinition]:
        """生成组件Props"""
        prop_templates = {
            'Button': [
                PropDefinition('variant', PropType.LITERAL, False, 'primary', '按钮类型', ['primary', 'secondary', 'success', 'danger', 'ghost']),
                PropDefinition('size', PropType.LITERAL, False, 'md', '按钮尺寸', ['sm', 'md', 'lg']),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('loading', PropType.BOOLEAN, False, False, '是否加载中'),
                PropDefinition('onClick', PropType.FUNCTION, False, None, '点击事件'),
            ],
            'Input': [
                PropDefinition('value', PropType.STRING, False, '', '输入值'),
                PropDefinition('placeholder', PropType.STRING, False, '', '占位符'),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('readOnly', PropType.BOOLEAN, False, False, '是否只读'),
                PropDefinition('error', PropType.STRING, False, None, '错误信息'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
                PropDefinition('onBlur', PropType.FUNCTION, False, None, '失焦事件'),
            ],
            'TextArea': [
                PropDefinition('value', PropType.STRING, False, '', '输入值'),
                PropDefinition('placeholder', PropType.STRING, False, '', '占位符'),
                PropDefinition('rows', PropType.NUMBER, False, 4, '行数'),
                PropDefinition('maxLength', PropType.NUMBER, False, None, '最大长度'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'Select': [
                PropDefinition('value', PropType.STRING, False, None, '选中值'),
                PropDefinition('options', PropType.ARRAY, False, [], '选项列表'),
                PropDefinition('placeholder', PropType.STRING, False, '请选择', '占位符'),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'Checkbox': [
                PropDefinition('checked', PropType.BOOLEAN, False, False, '是否选中'),
                PropDefinition('label', PropType.STRING, False, '', '标签文本'),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'Radio': [
                PropDefinition('value', PropType.STRING, False, None, '选中值'),
                PropDefinition('options', PropType.ARRAY, False, [], '选项列表'),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'Switch': [
                PropDefinition('checked', PropType.BOOLEAN, False, False, '是否选中'),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'DatePicker': [
                PropDefinition('value', PropType.STRING, False, None, '选中日期'),
                PropDefinition('placeholder', PropType.STRING, False, '请选择日期', '占位符'),
                PropDefinition('format', PropType.STRING, False, 'YYYY-MM-DD', '日期格式'),
                PropDefinition('disabled', PropType.BOOLEAN, False, False, '是否禁用'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'Form': [
                PropDefinition('initialValues', PropType.OBJECT, False, {}, '初始值'),
                PropDefinition('onSubmit', PropType.FUNCTION, True, None, '提交事件'),
                PropDefinition('onReset', PropType.FUNCTION, False, None, '重置事件'),
            ],
            'Upload': [
                PropDefinition('accept', PropType.STRING, False, '', '接受文件类型'),
                PropDefinition('multiple', PropType.BOOLEAN, False, False, '是否多选'),
                PropDefinition('maxSize', PropType.NUMBER, False, None, '最大文件大小'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '文件变化事件'),
                PropDefinition('onUpload', PropType.FUNCTION, True, None, '上传事件'),
            ],
            'Table': [
                PropDefinition('data', PropType.ARRAY, True, None, '表格数据'),
                PropDefinition('columns', PropType.ARRAY, True, None, '列配置'),
                PropDefinition('loading', PropType.BOOLEAN, False, False, '是否加载中'),
                PropDefinition('pagination', PropType.OBJECT, False, None, '分页配置'),
                PropDefinition('onRowClick', PropType.FUNCTION, False, None, '行点击事件'),
                PropDefinition('onSort', PropType.FUNCTION, False, None, '排序事件'),
            ],
            'List': [
                PropDefinition('data', PropType.ARRAY, True, None, '列表数据'),
                PropDefinition('renderItem', PropType.FUNCTION, True, None, '渲染函数'),
                PropDefinition('loading', PropType.BOOLEAN, False, False, '是否加载中'),
                PropDefinition('emptyText', PropType.STRING, False, '暂无数据', '空状态文本'),
            ],
            'Card': [
                PropDefinition('title', PropType.NODE, False, None, '标题'),
                PropDefinition('extra', PropType.NODE, False, None, '额外操作'),
                PropDefinition('bordered', PropType.BOOLEAN, False, True, '是否显示边框'),
                PropDefinition('hoverable', PropType.BOOLEAN, False, False, '是否悬浮效果'),
            ],
            'Badge': [
                PropDefinition('count', PropType.NUMBER, False, 0, '徽标数'),
                PropDefinition('maxCount', PropType.NUMBER, False, 99, '最大显示数'),
                PropDefinition('dot', PropType.BOOLEAN, False, False, '是否显示点'),
                PropDefinition('status', PropType.LITERAL, False, 'default', '状态', ['success', 'processing', 'default', 'error', 'warning']),
            ],
            'Avatar': [
                PropDefinition('src', PropType.STRING, False, None, '图片地址'),
                PropDefinition('alt', PropType.STRING, False, '', '替代文本'),
                PropDefinition('size', PropType.LITERAL, False, 'md', '尺寸', ['sm', 'md', 'lg', 'xl']),
                PropDefinition('shape', PropType.LITERAL, False, 'circle', '形状', ['circle', 'square']),
            ],
            'Tag': [
                PropDefinition('color', PropType.STRING, False, 'blue', '颜色'),
                PropDefinition('closable', PropType.BOOLEAN, False, False, '是否可关闭'),
                PropDefinition('onClose', PropType.FUNCTION, False, None, '关闭事件'),
            ],
            'Progress': [
                PropDefinition('percent', PropType.NUMBER, True, None, '百分比'),
                PropDefinition('status', PropType.LITERAL, False, 'normal', '状态', ['normal', 'success', 'exception', 'active']),
                PropDefinition('showInfo', PropType.BOOLEAN, False, True, '是否显示信息'),
            ],
            'Statistic': [
                PropDefinition('title', PropType.STRING, False, '', '标题'),
                PropDefinition('value', PropType.NUMBER, True, None, '数值'),
                PropDefinition('prefix', PropType.NODE, False, None, '前缀'),
                PropDefinition('suffix', PropType.NODE, False, None, '后缀'),
                PropDefinition('precision', PropType.NUMBER, False, 0, '精度'),
            ],
            'Timeline': [
                PropDefinition('items', PropType.ARRAY, True, None, '时间轴项'),
                PropDefinition('mode', PropType.LITERAL, False, 'left', '模式', ['left', 'right', 'alternate']),
            ],
            'Tree': [
                PropDefinition('data', PropType.ARRAY, True, None, '树形数据'),
                PropDefinition('defaultExpandAll', PropType.BOOLEAN, False, False, '默认展开所有'),
                PropDefinition('onSelect', PropType.FUNCTION, False, None, '选择事件'),
                PropDefinition('onCheck', PropType.FUNCTION, False, None, '勾选事件'),
            ],
            'Calendar': [
                PropDefinition('value', PropType.STRING, False, None, '当前日期'),
                PropDefinition('mode', PropType.LITERAL, False, 'month', '模式', ['month', 'year']),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '日期变化事件'),
                PropDefinition('onSelect', PropType.FUNCTION, False, None, '选择事件'),
            ],
            'Alert': [
                PropDefinition('type', PropType.LITERAL, False, 'info', '类型', ['success', 'info', 'warning', 'error']),
                PropDefinition('message', PropType.STRING, True, None, '提示内容'),
                PropDefinition('description', PropType.STRING, False, None, '详细描述'),
                PropDefinition('closable', PropType.BOOLEAN, False, False, '是否可关闭'),
                PropDefinition('onClose', PropType.FUNCTION, False, None, '关闭事件'),
            ],
            'Message': [
                PropDefinition('type', PropType.LITERAL, False, 'info', '类型', ['success', 'info', 'warning', 'error']),
                PropDefinition('content', PropType.STRING, True, None, '消息内容'),
                PropDefinition('duration', PropType.NUMBER, False, 3000, '显示时长'),
            ],
            'Modal': [
                PropDefinition('open', PropType.BOOLEAN, True, None, '是否显示'),
                PropDefinition('title', PropType.NODE, False, None, '标题'),
                PropDefinition('width', PropType.NUMBER, False, 520, '宽度'),
                PropDefinition('closable', PropType.BOOLEAN, False, True, '是否可关闭'),
                PropDefinition('onOk', PropType.FUNCTION, False, None, '确认事件'),
                PropDefinition('onCancel', PropType.FUNCTION, False, None, '取消事件'),
                PropDefinition('afterClose', PropType.FUNCTION, False, None, '关闭后事件'),
            ],
            'Drawer': [
                PropDefinition('open', PropType.BOOLEAN, True, None, '是否显示'),
                PropDefinition('title', PropType.NODE, False, None, '标题'),
                PropDefinition('placement', PropType.LITERAL, False, 'right', '位置', ['left', 'right', 'top', 'bottom']),
                PropDefinition('width', PropType.NUMBER, False, 378, '宽度'),
                PropDefinition('onClose', PropType.FUNCTION, True, None, '关闭事件'),
            ],
            'Notification': [
                PropDefinition('type', PropType.LITERAL, False, 'info', '类型', ['success', 'info', 'warning', 'error']),
                PropDefinition('message', PropType.STRING, True, None, '标题'),
                PropDefinition('description', PropType.STRING, False, None, '描述'),
                PropDefinition('duration', PropType.NUMBER, False, 4500, '显示时长'),
            ],
            'Popconfirm': [
                PropDefinition('title', PropType.STRING, True, None, '确认标题'),
                PropDefinition('description', PropType.STRING, False, None, '确认描述'),
                PropDefinition('onConfirm', PropType.FUNCTION, True, None, '确认事件'),
                PropDefinition('onCancel', PropType.FUNCTION, False, None, '取消事件'),
            ],
            'Loading': [
                PropDefinition('loading', PropType.BOOLEAN, True, None, '是否加载中'),
                PropDefinition('size', PropType.LITERAL, False, 'md', '尺寸', ['sm', 'md', 'lg']),
                PropDefinition('tip', PropType.STRING, False, '', '提示文本'),
            ],
            'Skeleton': [
                PropDefinition('active', PropType.BOOLEAN, False, True, '是否动画'),
                PropDefinition('avatar', PropType.BOOLEAN, False, False, '是否显示头像'),
                PropDefinition('paragraph', PropType.OBJECT, False, None, '段落配置'),
            ],
            'Empty': [
                PropDefinition('description', PropType.STRING, False, '暂无数据', '描述文本'),
                PropDefinition('image', PropType.NODE, False, None, '自定义图片'),
            ],
            'Result': [
                PropDefinition('status', PropType.LITERAL, True, None, '状态', ['success', 'error', 'info', 'warning', '404', '403', '500']),
                PropDefinition('title', PropType.STRING, True, None, '标题'),
                PropDefinition('subTitle', PropType.STRING, False, None, '副标题'),
                PropDefinition('extra', PropType.NODE, False, None, '额外操作'),
            ],
            'Menu': [
                PropDefinition('items', PropType.ARRAY, True, None, '菜单项'),
                PropDefinition('mode', PropType.LITERAL, False, 'vertical', '模式', ['vertical', 'horizontal', 'inline']),
                PropDefinition('selectedKeys', PropType.ARRAY, False, [], '选中项'),
                PropDefinition('onClick', PropType.FUNCTION, False, None, '点击事件'),
            ],
            'Tabs': [
                PropDefinition('items', PropType.ARRAY, True, None, '标签项'),
                PropDefinition('activeKey', PropType.STRING, False, None, '当前激活项'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '切换事件'),
            ],
            'Breadcrumb': [
                PropDefinition('items', PropType.ARRAY, True, None, '面包屑项'),
                PropDefinition('separator', PropType.NODE, False, None, '分隔符'),
            ],
            'Dropdown': [
                PropDefinition('menu', PropType.OBJECT, True, None, '菜单配置'),
                PropDefinition('placement', PropType.LITERAL, False, 'bottomLeft', '位置', ['bottomLeft', 'bottomCenter', 'bottomRight', 'topLeft', 'topCenter', 'topRight']),
                PropDefinition('trigger', PropType.ARRAY, False, ['hover'], '触发方式'),
            ],
            'Pagination': [
                PropDefinition('current', PropType.NUMBER, True, None, '当前页'),
                PropDefinition('pageSize', PropType.NUMBER, True, None, '每页条数'),
                PropDefinition('total', PropType.NUMBER, True, None, '总条数'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '页码变化事件'),
            ],
            'Steps': [
                PropDefinition('current', PropType.NUMBER, False, 0, '当前步骤'),
                PropDefinition('items', PropType.ARRAY, True, None, '步骤项'),
                PropDefinition('direction', PropType.LITERAL, False, 'horizontal', '方向', ['horizontal', 'vertical']),
            ],
            'Anchor': [
                PropDefinition('items', PropType.ARRAY, True, None, '锚点项'),
                PropDefinition('affix', PropType.BOOLEAN, False, True, '是否固钉'),
            ],
            'Tooltip': [
                PropDefinition('title', PropType.NODE, True, None, '提示内容'),
                PropDefinition('placement', PropType.LITERAL, False, 'top', '位置', ['top', 'left', 'right', 'bottom', 'topLeft', 'topRight', 'bottomLeft', 'bottomRight']),
            ],
            'Popover': [
                PropDefinition('title', PropType.NODE, False, None, '标题'),
                PropDefinition('content', PropType.NODE, True, None, '内容'),
                PropDefinition('placement', PropType.LITERAL, False, 'top', '位置', ['top', 'left', 'right', 'bottom']),
            ],
            'Layout': [
                PropDefinition('hasSider', PropType.BOOLEAN, False, False, '是否有侧边栏'),
            ],
            'Grid': [
                PropDefinition('span', PropType.NUMBER, False, 24, '栅格占位'),
                PropDefinition('offset', PropType.NUMBER, False, 0, '栅格偏移'),
            ],
            'Space': [
                PropDefinition('size', PropType.LITERAL, False, 'md', '间距', ['sm', 'md', 'lg']),
                PropDefinition('direction', PropType.LITERAL, False, 'horizontal', '方向', ['horizontal', 'vertical']),
                PropDefinition('align', PropType.LITERAL, False, 'start', '对齐', ['start', 'end', 'center', 'baseline']),
            ],
            'Divider': [
                PropDefinition('type', PropType.LITERAL, False, 'horizontal', '类型', ['horizontal', 'vertical']),
                PropDefinition('orientation', PropType.LITERAL, False, 'center', '标题位置', ['left', 'right', 'center']),
            ],
            'Search': [
                PropDefinition('value', PropType.STRING, False, '', '搜索值'),
                PropDefinition('placeholder', PropType.STRING, False, '请输入搜索关键词', '占位符'),
                PropDefinition('loading', PropType.BOOLEAN, False, False, '是否加载中'),
                PropDefinition('onSearch', PropType.FUNCTION, True, None, '搜索事件'),
                PropDefinition('onChange', PropType.FUNCTION, False, None, '值变化事件'),
            ],
            'Filter': [
                PropDefinition('filters', PropType.ARRAY, True, None, '筛选条件'),
                PropDefinition('values', PropType.OBJECT, False, {}, '当前值'),
                PropDefinition('onChange', PropType.FUNCTION, True, None, '值变化事件'),
            ],
            'Sort': [
                PropDefinition('field', PropType.STRING, True, None, '排序字段'),
                PropDefinition('order', PropType.LITERAL, False, null, '排序方式', ['asc', 'desc']),
                PropDefinition('onChange', PropType.FUNCTION, True, None, '排序变化事件'),
            ],
        }

        return prop_templates.get(comp_name, [PropDefinition('className', PropType.STRING, False, '', '自定义类名')])

    def _extract_events(self, comp_name: str) -> List[str]:
        """提取组件事件"""
        events = []
        props = self._generate_props(comp_name)
        for prop in props:
            if prop.type == PropType.FUNCTION:
                events.append(prop.name)
        return events

    def _get_dependencies(self, comp_name: str) -> List[str]:
        """获取组件依赖"""
        # 根据类别返回依赖
        category = self.CATEGORY_MAP.get(comp_name, ComponentCategory.GENERAL)

        base_deps = ['react']

        category_deps = {
            ComponentCategory.FORM: ['react-hook-form', 'zod'],
            ComponentCategory.DATA_DISPLAY: ['@tanstack/react-table'],
            ComponentCategory.FEEDBACK: ['framer-motion'],
            ComponentCategory.NAVIGATION: ['react-router-dom'],
            ComponentCategory.OVERLAY: ['@radix-ui/react-popover'],
            ComponentCategory.LAYOUT: [],
            ComponentCategory.GENERAL: [],
        }

        return base_deps + category_deps.get(category, [])


class ReactComponentGenerator:
    """React组件代码生成器"""

    def __init__(self, component: ComponentDefinition):
        self.component = component

    def generate(self) -> ComponentPackage:
        """生成组件包"""
        return ComponentPackage(
            component=self.component,
            code=self._generate_component_code(),
            test_code=self._generate_test_code(),
            story_code=self._generate_story_code(),
            types_code=self._generate_types_code(),
            index_code=self._generate_index_code(),
        )

    def _generate_component_code(self) -> str:
        """生成组件代码"""
        comp_name = self.component.name
        props_interface = self._generate_props_interface()

        # 生成imports
        imports = self._generate_imports()

        # 生成组件主体
        component_body = self._generate_component_body()

        return f'''"use client";

{imports}

{props_interface}

/**
 * {self.component.description}
 */
export const {comp_name}: React.FC<{comp_name}Props> = ({{
{self._generate_props_destructure()}
}}) => {{
{self._generate_hooks()}
{self._generate_handlers()}

  return (
{component_body}
  );
}};

{comp_name}.displayName = "{comp_name}";

export default {comp_name};
'''

    def _generate_imports(self) -> str:
        """生成imports"""
        imports = ["import React from 'react';"]

        # 根据组件类型添加特定import
        if self.component.category == ComponentCategory.FORM:
            imports.append("import { useFormContext } from 'react-hook-form';")

        if any(prop.type == PropType.FUNCTION for prop in self.component.props):
            imports.append("import { useCallback } from 'react';")

        # 添加classnames
        imports.append("import cn from 'classnames';")

        return '\n'.join(imports)

    def _generate_props_interface(self) -> str:
        """生成Props接口"""
        lines = [f'export interface {self.component.name}Props {{']

        for prop in self.component.props:
            type_str = self._get_typescript_type(prop)
            optional = '?' if not prop.required else ''
            default_comment = f' // 默认值: {prop.default_value}' if prop.default_value is not None else ''
            lines.append(f'  /** {prop.description} */')
            lines.append(f'  {prop.name}{optional}: {type_str};{default_comment}')

        if self.component.children_accepted:
            lines.append('  /** 子元素 */')
            lines.append('  children?: React.ReactNode;')

        lines.append('}')

        return '\n'.join(lines)

    def _get_typescript_type(self, prop: PropDefinition) -> str:
        """获取TypeScript类型"""
        type_mapping = {
            PropType.STRING: 'string',
            PropType.NUMBER: 'number',
            PropType.BOOLEAN: 'boolean',
            PropType.FUNCTION: '((...args: any[]) => void)',
            PropType.ARRAY: 'any[]',
            PropType.OBJECT: 'Record<string, any>',
            PropType.NODE: 'React.ReactNode',
            PropType.ELEMENT: 'React.ReactElement',
            PropType.ANY: 'any',
            PropType.LITERAL: ' | '.join([f'"{v}"' for v in prop.enum_values]) if prop.enum_values else 'string',
        }
        return type_mapping.get(prop.type, 'any')

    def _generate_props_destructure(self) -> str:
        """生成Props解构"""
        props_list = []

        for prop in self.component.props:
            if prop.default_value is not None:
                props_list.append(f'  {prop.name} = {self._format_default_value(prop)}')
            else:
                props_list.append(f'  {prop.name}')

        if self.component.children_accepted:
            props_list.append('  children')

        return ',\n'.join(props_list)

    def _format_default_value(self, prop: PropDefinition) -> str:
        """格式化默认值"""
        if prop.type == PropType.STRING:
            return f'"{prop.default_value}"'
        elif prop.type == PropType.BOOLEAN:
            return str(prop.default_value).lower()
        elif prop.type == PropType.NUMBER:
            return str(prop.default_value)
        elif prop.type == PropType.ARRAY:
            return '[]'
        elif prop.type == PropType.OBJECT:
            return '{}'
        return str(prop.default_value)

    def _generate_hooks(self) -> str:
        """生成hooks"""
        hooks = []

        # 根据组件类型生成不同的hooks
        if self.component.category == ComponentCategory.FORM:
            hooks.append('  const { register, formState: { errors } } = useFormContext();')

        return '\n'.join(hooks) if hooks else ''

    def _generate_handlers(self) -> str:
        """生成事件处理器"""
        handlers = []

        for prop in self.component.props:
            if prop.type == PropType.FUNCTION and prop.name.startswith('on'):
                event_name = prop.name[2:].lower()
                handlers.append(f'''
  const handle{prop.name[2:]} = useCallback((...args: any[]) => {{
    {prop.name}?.(...args);
  }}, [{prop.name}]);''')

        return '\n'.join(handlers) if handlers else ''

    def _generate_component_body(self) -> str:
        """生成组件JSX"""
        generators = {
            'Button': self._generate_button_jsx,
            'Input': self._generate_input_jsx,
            'Select': self._generate_select_jsx,
            'Card': self._generate_card_jsx,
            'Modal': self._generate_modal_jsx,
            'Table': self._generate_table_jsx,
            'Alert': self._generate_alert_jsx,
            'Badge': self._generate_badge_jsx,
            'Avatar': self._generate_avatar_jsx,
            'Loading': self._generate_loading_jsx,
            'Empty': self._generate_empty_jsx,
        }

        generator = generators.get(self.component.name, self._generate_generic_jsx)
        return generator()

    def _generate_button_jsx(self) -> str:
        return '''    <button
      type="button"
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2',
        {
          'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500': variant === 'primary',
          'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500': variant === 'secondary',
          'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500': variant === 'success',
          'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500': variant === 'danger',
          'bg-transparent text-gray-600 hover:bg-gray-100': variant === 'ghost',
          'px-3 py-1.5 text-sm': size === 'sm',
          'px-4 py-2 text-base': size === 'md',
          'px-6 py-3 text-lg': size === 'lg',
          'opacity-50 cursor-not-allowed': disabled || loading,
        },
        className
      )}
      disabled={disabled || loading}
      onClick={handleClick}
    >
      {loading && (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children || 'Button'}
    </button>'''

    def _generate_input_jsx(self) -> str:
        return '''    <div className="w-full">
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        readOnly={readOnly}
        onChange={(e) => onChange?.(e.target.value)}
        onBlur={(e) => onBlur?.(e.target.value)}
        className={cn(
          'w-full px-4 py-2 border rounded-lg transition-all focus:outline-none focus:ring-2',
          'placeholder:text-gray-400',
          {
            'border-gray-300 focus:border-blue-500 focus:ring-blue-200': !error,
            'border-red-500 focus:border-red-500 focus:ring-red-200': error,
            'bg-gray-100 cursor-not-allowed': disabled,
          },
          className
        )}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>'''

    def _generate_select_jsx(self) -> str:
        return '''    <div className="w-full">
      <select
        value={value || ''}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.value)}
        className={cn(
          'w-full px-4 py-2 border border-gray-300 rounded-lg',
          'focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-500',
          'disabled:bg-gray-100 disabled:cursor-not-allowed',
          className
        )}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options?.map((option: any) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>'''

    def _generate_card_jsx(self) -> str:
        return '''    <div
      className={cn(
        'bg-white rounded-lg overflow-hidden',
        {
          'border border-gray-200': bordered,
          'shadow-sm hover:shadow-md transition-shadow': hoverable,
        },
        className
      )}
    >
      {(title || extra) && (
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
          {extra && <div>{extra}</div>}
        </div>
      )}
      <div className="p-6">
        {children}
      </div>
    </div>'''

    def _generate_modal_jsx(self) -> str:
        return '''    <>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
            onClick={() => closable && onCancel?.()}
          />

          {/* Modal */}
          <div
            className={cn(
              'relative bg-white rounded-lg shadow-xl transform transition-all',
              'mx-4 max-h-[90vh] overflow-y-auto'
            )}
            style={{ width }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              {closable && (
                <button
                  onClick={() => onCancel?.()}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>

            {/* Content */}
            <div className="px-6 py-4">
              {children}
            </div>

            {/* Footer */}
            <div className="flex justify-end space-x-3 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
              <button
                onClick={() => onCancel?.()}
                className="px-4 py-2 text-gray-700 hover:text-gray-900 transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => onOk?.()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                确认
              </button>
            </div>
          </div>
        </div>
      )}
    </>'''

    def _generate_table_jsx(self) -> str:
        return '''    <div className="w-full">
      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns?.map((column: any) => (
                <th
                  key={column.key}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {column.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={columns?.length} className="px-6 py-8 text-center">
                  <div className="flex justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                  </div>
                </td>
              </tr>
            ) : data?.length === 0 ? (
              <tr>
                <td colSpan={columns?.length} className="px-6 py-8 text-center text-gray-500">
                  暂无数据
                </td>
              </tr>
            ) : (
              data?.map((row: any, index: number) => (
                <tr
                  key={row.id || index}
                  onClick={() => onRowClick?.(row)}
                  className={cn('hover:bg-gray-50', { 'cursor-pointer': onRowClick })}
                >
                  {columns?.map((column: any) => (
                    <td key={column.key} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {column.render ? column.render(row[column.key], row) : row[column.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>'''

    def _generate_alert_jsx(self) -> str:
        return '''    <div
      className={cn(
        'rounded-lg p-4 mb-4',
        {
          'bg-green-50 text-green-800 border border-green-200': type === 'success',
          'bg-blue-50 text-blue-800 border border-blue-200': type === 'info',
          'bg-yellow-50 text-yellow-800 border border-yellow-200': type === 'warning',
          'bg-red-50 text-red-800 border border-red-200': type === 'error',
        },
        className
      )}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          {type === 'success' && (
            <svg className="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          )}
          {type === 'info' && (
            <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          )}
          {type === 'warning' && (
            <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          )}
          {type === 'error' && (
            <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          )}
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium">{message}</h3>
          {description && <div className="mt-2 text-sm opacity-90">{description}</div>}
        </div>
        {closable && (
          <button
            onClick={onClose}
            className="ml-auto -mx-1.5 -my-1.5 rounded-lg p-1.5 inline-flex text-current opacity-60 hover:opacity-100"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>'''

    def _generate_badge_jsx(self) -> str:
        return '''    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        {
          'bg-green-100 text-green-800': status === 'success',
          'bg-blue-100 text-blue-800': status === 'processing',
          'bg-gray-100 text-gray-800': status === 'default',
          'bg-red-100 text-red-800': status === 'error',
          'bg-yellow-100 text-yellow-800': status === 'warning',
        },
        className
      )}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5" />}
      {count > maxCount ? `${maxCount}+` : count}
    </span>'''

    def _generate_avatar_jsx(self) -> str:
        return '''    <div
      className={cn(
        'inline-flex items-center justify-center rounded-full bg-gray-200 overflow-hidden',
        {
          'w-8 h-8': size === 'sm',
          'w-10 h-10': size === 'md',
          'w-12 h-12': size === 'lg',
          'w-16 h-16': size === 'xl',
          'rounded-full': shape === 'circle',
          'rounded-lg': shape === 'square',
        },
        className
      )}
    >
      {src ? (
        <img src={src} alt={alt} className="w-full h-full object-cover" />
      ) : (
        <svg className="w-1/2 h-1/2 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
        </svg>
      )}
    </div>'''

    def _generate_loading_jsx(self) -> str:
        return '''    <div className={cn('flex items-center justify-center', className)}>
      {loading && (
        <>
          <div
            className={cn(
              'animate-spin rounded-full border-b-2 border-blue-600',
              {
                'w-4 h-4': size === 'sm',
                'w-8 h-8': size === 'md',
                'w-12 h-12': size === 'lg',
              }
            )}
          />
          {tip && <span className="ml-2 text-gray-600">{tip}</span>}
        </>
      )}
    </div>'''

    def _generate_empty_jsx(self) -> str:
        return '''    <div className={cn('flex flex-col items-center justify-center py-12', className)}>
      {image || (
        <svg className="w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      )}
      <p className="text-gray-500">{description}</p>
    </div>'''

    def _generate_generic_jsx(self) -> str:
        return '''    <div className={cn('p-4', className)}>
      {children || <p>Component: ''' + self.component.name + '''</p>}
    </div>'''

    def _generate_test_code(self) -> str:
        """生成测试代码"""
        comp_name = self.component.name

        # 生成基础测试用例
        test_cases = self._generate_test_cases()

        return f'''import React from 'react';
import {{ render, screen, fireEvent }} from '@testing-library/react';
import {comp_name} from './{comp_name}';

describe('{comp_name}', () => {{
{test_cases}
}});
'''

    def _generate_test_cases(self) -> str:
        """生成测试用例"""
        cases = []

        # 基础渲染测试
        cases.append(f'''  it('renders correctly', () => {{
    const {{ container }} = render(<{self.component.name} />);
    expect(container).toBeInTheDocument();
  }});''')

        # Props测试
        for prop in self.component.props[:3]:  # 只测试前3个props
            if prop.type == PropType.STRING:
                cases.append(f'''
  it('renders with {prop.name} prop', () => {{
    render(<{self.component.name} {prop.name}="test-{prop.name}" />);
    // Add assertion based on component behavior
  }});''')
            elif prop.type == PropType.BOOLEAN:
                cases.append(f'''
  it('renders with {prop.name}={str(prop.default_value).lower() if prop.default_value is not None else "true"}', () => {{
    render(<{self.component.name} {prop.name}={prop.default_value if prop.default_value is not None else "true"} />);
    // Add assertion based on component behavior
  }});''')
            elif prop.type == PropType.FUNCTION:
                cases.append(f'''
  it('calls {prop.name} when triggered', () => {{
    const handler = jest.fn();
    render(<{self.component.name} {prop.name}={{handler}} />);
    // Trigger event and assert handler was called
  }});''')

        # 事件测试
        if self.component.events:
            cases.append(f'''
  it('handles events correctly', () => {{
    const handlers = {{{', '.join([f'{event}: jest.fn()' for event in self.component.events[:2]])}}};
    render(<{self.component.name} {{...handlers}} />);
    // Test event handling
  }});''')

        return '\n'.join(cases)

    def _generate_story_code(self) -> str:
        """生成Storybook代码"""
        comp_name = self.component.name

        # 生成stories
        stories = self._generate_stories()

        return f'''import type {{ Meta, StoryObj }} from '@storybook/react';
import {comp_name} from './{comp_name}';

const meta: Meta<typeof {comp_name}> = {{
  title: 'Components/{self.component.category.value.title()}/{comp_name}',
  component: {comp_name},
  parameters: {{
    layout: 'centered',
  }},
  tags: ['autodocs'],
}};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {{
  args: {{
{self._generate_story_args()}
  }},
}};

{stories}
'''

    def _generate_story_args(self) -> str:
        """生成Story参数"""
        args = []
        for prop in self.component.props[:5]:  # 只显示前5个props
            if prop.default_value is not None:
                if prop.type == PropType.STRING:
                    args.append(f'    {prop.name}: "{prop.default_value}",')
                else:
                    args.append(f'    {prop.name}: {str(prop.default_value).lower() if isinstance(prop.default_value, bool) else prop.default_value},')
        return '\n'.join(args) if args else '    // Add default args here'

    def _generate_stories(self) -> str:
        """生成多个Story变体"""
        stories = []

        # 根据组件类型生成不同的stories
        if self.component.name == 'Button':
            stories.append('''export const Variants: Story = {
  render: () => (
    <div className="space-x-2">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="success">Success</Button>
      <Button variant="danger">Danger</Button>
      <Button variant="ghost">Ghost</Button>
    </div>
  ),
};''')
        elif self.component.name == 'Input':
            stories.append('''export const States: Story = {
  render: () => (
    <div className="space-y-4 w-80">
      <Input placeholder="Default input" />
      <Input placeholder="Disabled input" disabled />
      <Input placeholder="With error" error="This field is required" />
    </div>
  ),
};''')

        return '\n\n'.join(stories)

    def _generate_types_code(self) -> str:
        """生成类型定义代码"""
        return self._generate_props_interface()

    def _generate_index_code(self) -> str:
        """生成index导出代码"""
        return f'''export {{ {self.component.name} }} from './{self.component.name}';
export type {{ {self.component.name}Props }} from './{self.component.name}';
export {{ default }} from './{self.component.name}';
'''


# API接口函数
def generate_components_from_prd(prd_content: str) -> Dict[str, Any]:
    """
    从PRD生成前端组件

    Args:
        prd_content: PRD文档内容

    Returns:
        包含组件代码的字典
    """
    # 提取组件定义
    extractor = PRDComponentExtractor(prd_content)
    components = extractor.extract()

    # 生成组件代码
    result = {
        "components": [],
        "files": {},
        "metadata": {
            "total_count": len(components),
            "categories": {},
        }
    }

    for comp_def in components:
        # 统计类别
        category = comp_def.category.value
        if category not in result["metadata"]["categories"]:
            result["metadata"]["categories"][category] = 0
        result["metadata"]["categories"][category] += 1

        # 生成组件
        generator = ReactComponentGenerator(comp_def)
        package = generator.generate()

        comp_info = {
            "name": comp_def.name,
            "category": comp_def.category.value,
            "description": comp_def.description,
            "props_count": len(comp_def.props),
            "events": comp_def.events,
            "dependencies": comp_def.dependencies,
        }
        result["components"].append(comp_info)

        # 保存文件
        base_path = f"components/{comp_def.category.value}/{comp_def.name}"
        result["files"][f"{base_path}/{comp_def.name}.tsx"] = package.code
        result["files"][f"{base_path}/{comp_def.name}.test.tsx"] = package.test_code
        result["files"][f"{base_path}/{comp_def.name}.stories.tsx"] = package.story_code or ""
        result["files"][f"{base_path}/index.ts"] = package.index_code

    return result


def get_component_suggestions(prd_content: str) -> List[Dict[str, Any]]:
    """
    获取组件建议

    Args:
        prd_content: PRD文档内容

    Returns:
        组件建议列表
    """
    extractor = PRDComponentExtractor(prd_content)
    components = extractor.extract()

    suggestions = []
    for comp in components:
        suggestions.append({
            "name": comp.name,
            "category": comp.category.value,
            "description": comp.description,
            "priority": "high" if comp.category in [ComponentCategory.FORM, ComponentCategory.DATA_DISPLAY] else "medium",
            "estimated_effort": "2h" if len(comp.props) < 5 else "4h",
        })

    return suggestions