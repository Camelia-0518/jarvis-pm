"use client";

import { useState } from "react";

// 埋点事件模板
interface TrackingEvent {
  id: string;
  eventName: string;
  description: string;
  properties: string[];
  trigger: string;
  priority: "P0" | "P1" | "P2";
}

// 核心指标定义
interface CoreMetric {
  id: string;
  name: string;
  definition: string;
  calculation: string;
  target: string;
  dataSource: string;
}

// 分析看板
interface DashboardWidget {
  id: string;
  title: string;
  type: "number" | "trend" | "funnel" | "table";
  metric: string;
  timeRange: string;
}

// 医疗场景埋点模板
const DEFAULT_TRACKING_EVENTS: TrackingEvent[] = [
  {
    id: "1",
    eventName: "slice_apply_start",
    description: "用户开始切片借阅申请",
    properties: ["user_id", "user_type", "source_page", "timestamp"],
    trigger: "点击[开始申请]按钮",
    priority: "P0",
  },
  {
    id: "2",
    eventName: "slice_apply_submit",
    description: "用户提交借阅申请",
    properties: ["user_id", "apply_id", "slice_count", "deposit_amount", "timestamp"],
    trigger: "提交申请表单",
    priority: "P0",
  },
  {
    id: "3",
    eventName: "slice_apply_complete",
    description: "申请流程完成",
    properties: ["user_id", "apply_id", "duration_seconds", "timestamp"],
    trigger: "申请成功页展示",
    priority: "P0",
  },
  {
    id: "4",
    eventName: "audit_approve",
    description: "病理科审核通过",
    properties: ["apply_id", "auditor_id", "audit_duration_hours", "timestamp"],
    trigger: "审核通过操作",
    priority: "P0",
  },
  {
    id: "5",
    eventName: "payment_success",
    description: "用户支付成功",
    properties: ["user_id", "apply_id", "amount", "payment_method", "timestamp"],
    trigger: "支付回调成功",
    priority: "P0",
  },
  {
    id: "6",
    eventName: "slice_pickup",
    description: "用户领取切片",
    properties: ["user_id", "apply_id", "pickup_method", "timestamp"],
    trigger: "领取确认",
    priority: "P1",
  },
  {
    id: "7",
    eventName: "slice_return",
    description: "用户归还切片",
    properties: ["user_id", "apply_id", "return_condition", "timestamp"],
    trigger: "归还确认",
    priority: "P1",
  },
  {
    id: "8",
    eventName: "refund_apply",
    description: "用户申请退款",
    properties: ["user_id", "apply_id", "refund_reason", "timestamp"],
    trigger: "点击退款申请",
    priority: "P1",
  },
];

// 核心指标定义
const CORE_METRICS: CoreMetric[] = [
  {
    id: "1",
    name: "线上申请率",
    definition: "线上申请数 / 总借阅申请数",
    calculation: "线上申请数 ÷ (线上申请数 + 线下申请数) × 100%",
    target: "≥ 80%",
    dataSource: "申请系统 + 病理科台账",
  },
  {
    id: "2",
    name: "平均审核时长",
    definition: "从提交申请到审核通过的平均时间",
    calculation: "SUM(审核通过时间 - 提交时间) ÷ 申请总数",
    target: "≤ 24小时",
    dataSource: "申请系统",
  },
  {
    id: "3",
    name: "申请完成率",
    definition: "完成全部流程的申请占比",
    calculation: "完成申请数 ÷ 开始申请数 × 100%",
    target: "≥ 70%",
    dataSource: "埋点数据",
  },
  {
    id: "4",
    name: "平均处理时长",
    definition: "从申请到领取的平均总时长",
    calculation: "SUM(领取时间 - 申请时间) ÷ 完成申请数",
    target: "≤ 3天",
    dataSource: "申请系统",
  },
  {
    id: "5",
    name: "用户满意度",
    definition: "对服务评价为满意以上的用户占比",
    calculation: "满意评价数 ÷ 总评价数 × 100%",
    target: "≥ 90%",
    dataSource: "评价系统",
  },
  {
    id: "6",
    name: "退款率",
    definition: "申请退款的订单占比",
    calculation: "退款申请数 ÷ 支付成功数 × 100%",
    target: "≤ 5%",
    dataSource: "支付系统",
  },
];

// 看板配置
const DASHBOARD_WIDGETS: DashboardWidget[] = [
  { id: "1", title: "今日申请数", type: "number", metric: "apply_count_daily", timeRange: "今日" },
  { id: "2", title: "平均审核时长", type: "number", metric: "audit_duration_avg", timeRange: "近7天" },
  { id: "3", title: "申请趋势", type: "trend", metric: "apply_count", timeRange: "近30天" },
  { id: "4", title: "转化漏斗", type: "funnel", metric: "conversion_funnel", timeRange: "近7天" },
  { id: "5", title: "各环节流失", type: "table", metric: "drop_off_analysis", timeRange: "近7天" },
];

// A/B测试设计
interface ABTest {
  id: string;
  name: string;
  hypothesis: string;
  variable: string;
  metrics: string[];
  sampleSize: string;
  duration: string;
}

const AB_TEST_TEMPLATES: ABTest[] = [
  {
    id: "1",
    name: "申请流程优化",
    hypothesis: "简化申请流程从5步到3步可以提升完成率",
    variable: "流程步骤数",
    metrics: ["申请完成率", "平均完成时长"],
    sampleSize: "每组500用户",
    duration: "2周",
  },
  {
    id: "2",
    name: "押金提示优化",
    hypothesis: "在申请前明确展示押金规则可以减少退款率",
    variable: "押金提示文案和位置",
    metrics: ["退款率", "申请完成率"],
    sampleSize: "每组300用户",
    duration: "1周",
  },
];

export default function DataAnalyticsToolkit() {
  const [trackingEvents, setTrackingEvents] = useState<TrackingEvent[]>(DEFAULT_TRACKING_EVENTS);
  const [selectedEvent, setSelectedEvent] = useState<TrackingEvent | null>(null);

  return (
    <div className="space-y-6">
      {/* 埋点设计检查清单 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          📊 埋点设计检查清单
        </h3>

        <div className="space-y-3">
          {trackingEvents.map((event) => (
            <div
              key={event.id}
              onClick={() => setSelectedEvent(event)}
              className="cursor-pointer rounded-lg border border-slate-200 p-3 hover:border-sky-300 dark:border-slate-700"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      event.priority === "P0"
                        ? "bg-rose-100 text-rose-700"
                        : event.priority === "P1"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {event.priority}
                  </span>
                  <span className="font-mono text-sm text-slate-700 dark:text-slate-300">
                    {event.eventName}
                  </span>
                </div>
                <span className="text-xs text-slate-500">{event.trigger}</span>
              </div>
              <p className="mt-1 text-xs text-slate-500">{event.description}</p>
            </div>
          ))}
        </div>

        <button className="mt-4 flex items-center gap-2 text-sm text-sky-600 hover:text-sky-700">
          <span>+</span> 添加埋点事件
        </button>
      </div>

      {/* 埋点详情 */}
      {selectedEvent && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-4 dark:border-sky-800 dark:bg-sky-900/20">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-sky-900 dark:text-sky-100">
              {selectedEvent.eventName}
            </h4>
            <button
              onClick={() => setSelectedEvent(null)}
              className="text-sky-600 hover:text-sky-800"
            >
              ✕
            </button>
          </div>
          <p className="mt-1 text-sm text-sky-700">{selectedEvent.description}</p>
          <div className="mt-3">
            <div className="text-xs font-medium text-sky-800">属性列表:</div>
            <div className="mt-1 flex flex-wrap gap-2">
              {selectedEvent.properties.map((prop) => (
                <span
                  key={prop}
                  className="rounded bg-white px-2 py-0.5 text-xs text-sky-700 dark:bg-sky-900/30"
                >
                  {prop}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 核心指标定义 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          🎯 核心指标定义
        </h3>

        <div className="space-y-3">
          {CORE_METRICS.map((metric) => (
            <div
              key={metric.id}
              className="rounded-lg bg-slate-50 p-3 dark:bg-slate-700/50"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-800 dark:text-slate-200">
                  {metric.name}
                </span>
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                  目标: {metric.target}
                </span>
              </div>
              <div className="mt-2 grid gap-1 text-xs text-slate-600">
                <div>
                  <span className="font-medium">定义:</span> {metric.definition}
                </div>
                <div>
                  <span className="font-medium">计算:</span> {metric.calculation}
                </div>
                <div>
                  <span className="font-medium">数据源:</span> {metric.dataSource}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 数据看板模板 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          📈 数据看板配置
        </h3>

        <div className="grid grid-cols-2 gap-3">
          {DASHBOARD_WIDGETS.map((widget) => (
            <div
              key={widget.id}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {widget.title}
                </span>
                <span className="text-xs text-slate-400">{widget.type}</span>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {widget.metric} · {widget.timeRange}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* A/B测试设计 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          🧪 A/B测试设计
        </h3>

        <div className="space-y-4">
          {AB_TEST_TEMPLATES.map((test) => (
            <div
              key={test.id}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="font-medium text-slate-800 dark:text-slate-200">
                {test.name}
              </div>
              <div className="mt-2 space-y-1 text-xs text-slate-600">
                <div>
                  <span className="font-medium">假设:</span> {test.hypothesis}
                </div>
                <div>
                  <span className="font-medium">变量:</span> {test.variable}
                </div>
                <div>
                  <span className="font-medium">指标:</span> {test.metrics.join(", ")}
                </div>
                <div className="flex gap-4">
                  <span>
                    <span className="font-medium">样本:</span> {test.sampleSize}
                  </span>
                  <span>
                    <span className="font-medium">周期:</span> {test.duration}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 迭代建议生成 */}
      <div className="rounded-lg border border-purple-200 bg-purple-50 p-4 dark:border-purple-800 dark:bg-purple-900/20">
        <h3 className="mb-3 font-semibold text-purple-900 dark:text-purple-100">
          💡 数据驱动迭代建议
        </h3>

        <div className="space-y-2 text-sm text-purple-800">
          <p>基于数据分析，建议关注以下优化方向：</p>
          <ul className="list-inside list-disc space-y-1">
            <li>如果申请完成率 &lt; 70%，重点优化流程体验</li>
            <li>如果平均审核时长 &gt; 24h，推动病理科效率提升</li>
            <li>如果退款率 &gt; 5%，优化押金说明和预期管理</li>
            <li>如果第3步流失率最高，重点分析该环节问题</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
