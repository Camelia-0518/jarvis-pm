"use client";

import { useState } from "react";

// 低保真页面组件模板
interface PageTemplate {
  id: string;
  name: string;
  icon: string;
  description: string;
  elements: string[];
}

const PAGE_TEMPLATES: PageTemplate[] = [
  {
    id: "list",
    name: "列表页",
    icon: "📋",
    description: "数据列表展示，支持搜索和筛选",
    elements: ["搜索栏", "筛选条件", "数据列表", "分页器", "批量操作"],
  },
  {
    id: "detail",
    name: "详情页",
    icon: "📄",
    description: "信息详情展示，支持状态显示",
    elements: ["基本信息区", "状态标签", "操作按钮", "历史记录", "关联信息"],
  },
  {
    id: "form",
    name: "表单页",
    icon: "📝",
    description: "信息录入和编辑",
    elements: ["表单字段", "必填校验", "步骤指示器", "保存/提交", "草稿箱"],
  },
  {
    id: "flow",
    name: "流程页",
    icon: "🔄",
    description: "多步骤流程引导",
    elements: ["步骤条", "当前步骤", "下一步/上一步", "进度提示", "完成确认"],
  },
  {
    id: "dashboard",
    name: "仪表盘",
    icon: "📊",
    description: "数据概览和统计",
    elements: ["关键指标卡", "趋势图表", "待办事项", "快捷入口", "通知提醒"],
  },
];

// 原型页面
interface PrototypePage {
  id: string;
  name: string;
  type: string;
  description: string;
  linkedPRDSection?: string;
}

// 交互说明
interface Interaction {
  id: string;
  element: string;
  trigger: string;
  action: string;
  result: string;
  exception?: string;
}

// 移动端适配检查项
interface MobileCheckItem {
  id: string;
  category: string;
  item: string;
  importance: "P0" | "P1" | "P2";
  checked: boolean;
}

const MOBILE_CHECKLIST: MobileCheckItem[] = [
  { id: "1", category: "布局", item: "核心内容一屏内展示", importance: "P0", checked: true },
  { id: "2", category: "布局", item: "按钮大小适合手指点击（≥44px）", importance: "P0", checked: true },
  { id: "3", category: "输入", item: "数字输入调用数字键盘", importance: "P0", checked: false },
  { id: "4", category: "输入", item: "表单字段支持自动填充", importance: "P1", checked: false },
  { id: "5", category: "性能", item: "页面加载时间 < 3秒", importance: "P0", checked: false },
  { id: "6", category: "性能", item: "图片支持懒加载", importance: "P1", checked: false },
  { id: "7", category: "体验", item: "下拉刷新支持", importance: "P1", checked: true },
  { id: "8", category: "体验", item: "空状态有引导提示", importance: "P0", checked: false },
  { id: "9", category: "兼容", item: "适配iOS/Android主流机型", importance: "P0", checked: false },
  { id: "10", category: "兼容", item: "支持微信内置浏览器", importance: "P0", checked: true },
];

export default function PrototypeToolkit() {
  const [pages, setPages] = useState<PrototypePage[]>([
    { id: "1", name: "申请首页", type: "dashboard", description: "展示申请入口和状态" },
    { id: "2", name: "填写申请", type: "form", description: "患者信息录入" },
    { id: "3", name: "确认支付", type: "flow", description: "押金支付流程" },
    { id: "4", name: "申请记录", type: "list", description: "历史申请列表" },
    { id: "5", name: "申请详情", type: "detail", description: "申请进度和详情" },
  ]);

  const [interactions, setInteractions] = useState<Interaction[]>([
    {
      id: "1",
      element: "提交申请按钮",
      trigger: "点击",
      action: "校验表单完整性",
      result: "校验通过进入支付页，失败提示错误信息",
      exception: "网络异常时提示重试",
    },
    {
      id: "2",
      element: "保存草稿按钮",
      trigger: "点击",
      action: "保存当前填写内容",
      result: "提示保存成功，可后续继续编辑",
    },
  ]);

  const [selectedPage, setSelectedPage] = useState<PrototypePage | null>(null);
  const [activeTab, setActiveTab] = useState<"pages" | "interactions" | "mobile">("pages");

  return (
    <div className="space-y-6">
      {/* 页面结构 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          🎨 页面结构规划
        </h3>

        <div className="grid grid-cols-2 gap-3">
          {pages.map((page, index) => (
            <div
              key={page.id}
              onClick={() => setSelectedPage(page)}
              className={`cursor-pointer rounded-lg border p-3 transition-colors ${
                selectedPage?.id === page.id
                  ? "border-sky-500 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                  : "border-slate-200 hover:border-slate-300 dark:border-slate-700"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-medium dark:bg-slate-700">
                  {index + 1}
                </span>
                <span className="font-medium text-slate-800 dark:text-slate-200">
                  {page.name}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-500">{page.description}</div>
            </div>
          ))}
        </div>

        <button className="mt-4 flex items-center gap-2 text-sm text-sky-600 hover:text-sky-700">
          <span>+</span> 添加页面
        </button>
      </div>

      {/* 选中页面详情 */}
      {selectedPage && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 dark:border-sky-800 dark:bg-sky-900/20">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-sky-900 dark:text-sky-100">
              {selectedPage.name}
            </h4>
            <button
              onClick={() => setSelectedPage(null)}
              className="text-sky-600 hover:text-sky-800"
            >
              ✕
            </button>
          </div>

          <div className="mt-3 space-y-3">
            <div>
              <label className="text-xs font-medium text-sky-800 dark:text-sky-200">
                关联PRD章节
              </label>
              <select className="mt-1 w-full rounded border border-sky-300 bg-white px-2 py-1 text-sm dark:border-sky-700 dark:bg-slate-800">
                <option>4.1 用户申请功能</option>
                <option>4.2 病理科审核功能</option>
                <option>4.3 押金管理功能</option>
                <option>4.4 申请记录查询</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-sky-800 dark:text-sky-200">
                页面类型
              </label>
              <div className="mt-1 text-sm text-sky-700">
                {PAGE_TEMPLATES.find((t) => t.id === selectedPage.type)?.name || "自定义"}
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-sky-800 dark:text-sky-200">
                建议包含元素
              </label>
              <div className="mt-1 flex flex-wrap gap-2">
                {PAGE_TEMPLATES.find((t) => t.id === selectedPage.type)?.elements.map((el) => (
                  <span
                    key={el}
                    className="rounded bg-white px-2 py-0.5 text-xs text-sky-700 dark:bg-sky-900/30"
                  >
                    {el}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 标签切换 */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        {[
          { id: "pages", label: "页面模板", icon: "🎨" },
          { id: "interactions", label: "交互说明", icon: "👆" },
          { id: "mobile", label: "移动适配", icon: "📱" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-1 px-4 py-2 text-sm font-medium ${
              activeTab === tab.id
                ? "border-b-2 border-sky-500 text-sky-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* 页面模板 */}
      {activeTab === "pages" && (
        <div className="grid grid-cols-2 gap-3">
          {PAGE_TEMPLATES.map((template) => (
            <div
              key={template.id}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="text-2xl">{template.icon}</div>
              <div className="mt-1 font-medium text-slate-800 dark:text-slate-200">
                {template.name}
              </div>
              <div className="text-xs text-slate-500">{template.description}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {template.elements.slice(0, 3).map((el) => (
                  <span
                    key={el}
                    className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700"
                  >
                    {el}
                  </span>
                ))}
                {template.elements.length > 3 && (
                  <span className="text-xs text-slate-400">+{template.elements.length - 3}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 交互说明 */}
      {activeTab === "interactions" && (
        <div className="space-y-3">
          {interactions.map((interaction) => (
            <div
              key={interaction.id}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="flex items-center gap-2">
                <span className="rounded bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700">
                  {interaction.element}
                </span>
                <span className="text-xs text-slate-400">{interaction.trigger}</span>
              </div>
              <div className="mt-2 grid gap-1 text-xs text-slate-600">
                <div>
                  <span className="font-medium">系统行为:</span> {interaction.action}
                </div>
                <div>
                  <span className="font-medium">预期结果:</span> {interaction.result}
                </div>
                {interaction.exception && (
                  <div className="text-rose-600">
                    <span className="font-medium">异常处理:</span> {interaction.exception}
                  </div>
                )}
              </div>
            </div>
          ))}

          <button className="flex items-center gap-2 text-sm text-sky-600 hover:text-sky-700">
            <span>+</span> 添加交互说明
          </button>
        </div>
      )}

      {/* 移动端适配 */}
      {activeTab === "mobile" && (
        <div className="space-y-4">
          {["布局", "输入", "性能", "体验", "兼容"].map((category) => (
            <div key={category}>
              <h4 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                {category}
              </h4>
              <div className="space-y-2">
                {MOBILE_CHECKLIST.filter((item) => item.category === category).map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700"
                  >
                    <input
                      type="checkbox"
                      checked={item.checked}
                      className="h-4 w-4 rounded border-slate-300"
                      readOnly
                    />
                    <span className="flex-1 text-sm text-slate-700 dark:text-slate-300">
                      {item.item}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-xs ${
                        item.importance === "P0"
                          ? "bg-rose-100 text-rose-700"
                          : item.importance === "P1"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {item.importance}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 原型与PRD联动说明 */}
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-900/20">
        <h4 className="font-medium text-emerald-900 dark:text-emerald-100">
          🔗 原型与PRD联动指南
        </h4>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-emerald-800 dark:text-emerald-200">
          <li>每个页面原型关联PRD第4章对应功能规格</li>
          <li>交互说明对应PRD第3章业务流程</li>
          <li>移动端检查清单对应PRD第6章合规要求</li>
          <li>原型评审时可直接跳转PRD查看详细规则</li>
        </ul>
      </div>
    </div>
  );
}
