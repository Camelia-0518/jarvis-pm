"use client";

import { useState } from "react";

// 评审议程
interface AgendaItem {
  id: string;
  time: string;
  duration: string;
  topic: string;
  owner: string;
  goal: string;
}

// 决策点
interface DecisionPoint {
  id: string;
  topic: string;
  options: string[];
  recommendation: string;
  status: "pending" | "approved" | "rejected" | "deferred";
}

// 风险项
interface Risk {
  id: string;
  description: string;
  probability: "high" | "medium" | "low";
  impact: "high" | "medium" | "low";
  mitigation: string;
  owner: string;
}

export default function ReviewMaterialGenerator() {
  const [meetingInfo, setMeetingInfo] = useState({
    title: "切片借阅平台PRD评审会",
    date: "2026-04-15",
    time: "14:00",
    location: "第三会议室",
    duration: "90分钟",
  });

  const [agenda, setAgenda] = useState<AgendaItem[]>([
    {
      id: "1",
      time: "14:00-14:10",
      duration: "10分钟",
      topic: "项目背景与目标",
      owner: "产品经理",
      goal: "统一对项目价值的认知",
    },
    {
      id: "2",
      time: "14:10-14:25",
      duration: "15分钟",
      topic: "用户故事与业务流程",
      owner: "产品经理",
      goal: "确认需求理解正确",
    },
    {
      id: "3",
      time: "14:25-14:45",
      duration: "20分钟",
      topic: "功能规格与原型",
      owner: "产品经理",
      goal: "确认功能范围",
    },
    {
      id: "4",
      time: "14:45-15:00",
      duration: "15分钟",
      topic: "合规与安全",
      owner: "产品经理",
      goal: "获得医务科/信息科确认",
    },
    {
      id: "5",
      time: "15:00-15:25",
      duration: "25分钟",
      topic: "讨论与决策",
      owner: "全体",
      goal: "形成决议",
    },
    {
      id: "6",
      time: "15:25-15:30",
      duration: "5分钟",
      topic: "总结与下一步",
      owner: "产品经理",
      goal: "明确待办事项",
    },
  ]);

  const [decisions, setDecisions] = useState<DecisionPoint[]>([
    {
      id: "1",
      topic: "押金金额标准",
      options: ["统一200元/片", "按切片类型差异化", "按院区差异化"],
      recommendation: "按院区差异化，江西/浙江200元，临夏150元",
      status: "pending",
    },
    {
      id: "2",
      topic: "审核时效承诺",
      options: ["24小时", "48小时", "工作日24小时"],
      recommendation: "工作日24小时，非工作日顺延",
      status: "pending",
    },
    {
      id: "3",
      topic: "快递配送支持",
      options: ["一期支持", "二期支持", "暂不支持"],
      recommendation: "二期支持，一期先跑通自取流程",
      status: "pending",
    },
    {
      id: "4",
      topic: "HIS对接方式",
      options: ["实时接口", "定时同步", "一期先用Excel导入"],
      recommendation: "实时接口，提前2周启动对接",
      status: "pending",
    },
  ]);

  const [risks, setRisks] = useState<Risk[]>([
    {
      id: "1",
      description: "HIS系统接口对接延期",
      probability: "medium",
      impact: "high",
      mitigation: "提前2周启动对接，预留缓冲时间；如延期先用Excel导入方式过渡",
      owner: "信息科",
    },
    {
      id: "2",
      description: "病理科审核工作量增加",
      probability: "medium",
      impact: "medium",
      mitigation: "系统提供自动核验功能，减少人工核对；试运行期收集反馈优化",
      owner: "病理科",
    },
    {
      id: "3",
      description: "患者接受度低，线上申请率低",
      probability: "low",
      impact: "high",
      mitigation: "保留线下窗口作为备选；加强宣传和引导；持续优化线上体验",
      owner: "产品经理",
    },
    {
      id: "4",
      description: "医务科合规审查不通过",
      probability: "low",
      impact: "high",
      mitigation: "PRD阶段就引入医务科评审，预留1周修改时间",
      owner: "医务科",
    },
  ]);

  const [activeTab, setActiveTab] = useState<"agenda" | "decisions" | "risks" | "qa">("agenda");

  const getStatusColor = (status: DecisionPoint["status"]) => {
    const colors = {
      pending: "bg-amber-100 text-amber-700",
      approved: "bg-emerald-100 text-emerald-700",
      rejected: "bg-rose-100 text-rose-700",
      deferred: "bg-slate-100 text-slate-700",
    };
    return colors[status];
  };

  const getRiskLevel = (p: string, i: string) => {
    if (p === "high" && i === "high") return { label: "极高", color: "bg-rose-100 text-rose-700" };
    if (p === "high" || i === "high") return { label: "高", color: "bg-orange-100 text-orange-700" };
    if (p === "medium" && i === "medium") return { label: "中", color: "bg-amber-100 text-amber-700" };
    return { label: "低", color: "bg-emerald-100 text-emerald-700" };
  };

  return (
    <div className="space-y-6">
      {/* 会议信息 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">📅 会议信息</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <label className="block text-slate-500">会议主题</label>
            <input
              type="text"
              value={meetingInfo.title}
              onChange={(e) => setMeetingInfo({ ...meetingInfo, title: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700"
            />
          </div>
          <div>
            <label className="block text-slate-500">会议地点</label>
            <input
              type="text"
              value={meetingInfo.location}
              onChange={(e) => setMeetingInfo({ ...meetingInfo, location: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700"
            />
          </div>
          <div>
            <label className="block text-slate-500">会议日期</label>
            <input
              type="date"
              value={meetingInfo.date}
              onChange={(e) => setMeetingInfo({ ...meetingInfo, date: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700"
            />
          </div>
          <div>
            <label className="block text-slate-500">会议时间</label>
            <input
              type="time"
              value={meetingInfo.time}
              onChange={(e) => setMeetingInfo({ ...meetingInfo, time: e.target.value })}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700"
            />
          </div>
        </div>
      </div>

      {/* 标签切换 */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        {[
          { id: "agenda", label: "评审议程", icon: "📋" },
          { id: "decisions", label: "决策清单", icon: "✓" },
          { id: "risks", label: "风险预案", icon: "⚠️" },
          { id: "qa", label: "预设Q&A", icon: "💬" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as "agenda" | "decisions" | "risks" | "qa")}
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

      {/* 评审议程 */}
      {activeTab === "agenda" && (
        <div className="space-y-3">
          {agenda.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800"
            >
              <div className="flex h-10 w-10 shrink-0 flex-col items-center justify-center rounded bg-sky-100 text-xs dark:bg-sky-900/30">
                <span className="font-medium text-sky-700 dark:text-sky-300">{item.time.split("-")[0]}</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-800 dark:text-slate-200">{item.topic}</span>
                  <span className="text-xs text-slate-500">{item.duration}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">主讲: {item.owner}</div>
                <div className="mt-1 text-xs text-sky-600">目标: {item.goal}</div>
              </div>
            </div>
          ))}
          <button className="w-full rounded-lg border border-dashed border-slate-300 py-2 text-sm text-slate-500 hover:border-slate-400">
            + 添加议程项
          </button>
        </div>
      )}

      {/* 决策清单 */}
      {activeTab === "decisions" && (
        <div className="space-y-3">
          {decisions.map((decision) => (
            <div
              key={decision.id}
              className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-medium text-slate-800 dark:text-slate-200">{decision.topic}</div>
                  <div className="mt-2 space-y-1">
                    {decision.options.map((opt, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-slate-600">
                        <input type="radio" name={decision.id} className="rounded border-slate-300" />
                        <span>{opt}</span>
                        {opt === decision.recommendation && (
                          <span className="rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-700">推荐</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs ${getStatusColor(decision.status)}`}>
                  {decision.status === "pending"
                    ? "待决策"
                    : decision.status === "approved"
                    ? "已通过"
                    : decision.status === "rejected"
                    ? "已否决"
                    : "暂缓"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 风险预案 */}
      {activeTab === "risks" && (
        <div className="space-y-3">
          {risks.map((risk) => {
            const level = getRiskLevel(risk.probability, risk.impact);
            return (
              <div
                key={risk.id}
                className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800 dark:text-slate-200">{risk.description}</span>
                      <span className={`rounded px-1.5 py-0.5 text-xs ${level.color}`}>{level.label}</span>
                    </div>
                    <div className="mt-1 flex gap-4 text-xs text-slate-500">
                      <span>概率: {risk.probability === "high" ? "高" : risk.probability === "medium" ? "中" : "低"}</span>
                      <span>影响: {risk.impact === "high" ? "高" : risk.impact === "medium" ? "中" : "低"}</span>
                      <span>负责人: {risk.owner}</span>
                    </div>
                    <div className="mt-2 text-sm text-slate-600">
                      <span className="font-medium">应对措施:</span> {risk.mitigation}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 预设Q&A */}
      {activeTab === "qa" && (
        <div className="space-y-3">
          <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
            <div className="flex items-center gap-2">
              <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700">医务科</span>
              <span className="text-xs text-slate-400">合规</span>
            </div>
            <div className="mt-2 font-medium text-slate-800 dark:text-slate-200">Q: 线上化后如何确保医疗合规？</div>
            <div className="mt-1 text-sm text-slate-600">
              A: 系统设置了多重合规检查：①申请时自动核验患者身份和病历信息；②审核流程设置双人复核机制；③所有操作留痕可追溯；④接入医务科审核节点。
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
            <div className="flex items-center gap-2">
              <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700">信息科</span>
              <span className="text-xs text-slate-400">技术</span>
            </div>
            <div className="mt-2 font-medium text-slate-800 dark:text-slate-200">Q: HIS系统对接复杂吗？</div>
            <div className="mt-1 text-sm text-slate-600">
              A: 对接相对简单，主要需要患者基本信息查询接口和病历信息查询接口。预计2周完成对接开发。
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
            <div className="flex items-center gap-2">
              <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700">财务科</span>
              <span className="text-xs text-slate-400">财务</span>
            </div>
            <div className="mt-2 font-medium text-slate-800 dark:text-slate-200">Q: 押金怎么管理？能原路退回吗？</div>
            <div className="mt-1 text-sm text-slate-600">
              A: 押金进入医院财务指定账户，不经过第三方。支持原路退回，退款申请后7个工作日内退回原支付账户。
            </div>
          </div>
        </div>
      )}

      {/* 导出按钮 */}
      <div className="flex gap-3">
        <button className="flex-1 rounded-lg bg-sky-600 py-2 text-sm font-medium text-white hover:bg-sky-700">
          📋 复制全部材料
        </button>
        <button className="flex-1 rounded-lg border border-slate-300 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300">
          📄 导出Markdown
        </button>
      </div>
    </div>
  );
}
