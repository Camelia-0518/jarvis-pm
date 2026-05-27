"use client";

import { useState } from "react";

// 里程碑模板
interface Milestone {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  progress: number;
  status: "pending" | "in-progress" | "completed" | "delayed";
  owner: string;
}

// 风险项
interface Risk {
  id: string;
  description: string;
  probability: "high" | "medium" | "low";
  impact: "high" | "medium" | "low";
  mitigation: string;
  status: "open" | "mitigated" | "occurred";
}

// 站会报告模板
interface StandupReport {
  date: string;
  yesterday: string[];
  today: string[];
  blockers: string[];
  risks: string[];
}

// 医疗项目常见风险清单
const COMMON_RISKS: Omit<Risk, "id">[] = [
  {
    description: "多院区政策差异导致需求变更",
    probability: "high",
    impact: "high",
    mitigation: "提前与各院区信息科确认政策要求",
    status: "open",
  },
  {
    description: "HIS系统接口对接延期",
    probability: "medium",
    impact: "high",
    mitigation: "提前申请接口文档，安排技术预研",
    status: "open",
  },
  {
    description: "医务科合规审查不通过",
    probability: "medium",
    impact: "high",
    mitigation: "PRD阶段就引入医务科评审，预留修改时间",
    status: "open",
  },
  {
    description: "患者隐私合规问题",
    probability: "low",
    impact: "high",
    mitigation: "等保测评前置，数据脱敏方案预评审",
    status: "open",
  },
];

export default function ProjectManagementToolkit() {
  const [milestones, setMilestones] = useState<Milestone[]>([
    {
      id: "1",
      name: "需求调研与PRD撰写",
      startDate: "2026-04-07",
      endDate: "2026-04-14",
      progress: 80,
      status: "in-progress",
      owner: "产品",
    },
    {
      id: "2",
      name: "PRD评审与定稿",
      startDate: "2026-04-15",
      endDate: "2026-04-18",
      progress: 0,
      status: "pending",
      owner: "产品+业务",
    },
    {
      id: "3",
      name: "技术方案设计",
      startDate: "2026-04-18",
      endDate: "2026-04-25",
      progress: 0,
      status: "pending",
      owner: "开发",
    },
    {
      id: "4",
      name: "开发实施",
      startDate: "2026-04-26",
      endDate: "2026-05-17",
      progress: 0,
      status: "pending",
      owner: "开发",
    },
    {
      id: "5",
      name: "测试与验收",
      startDate: "2026-05-18",
      endDate: "2026-05-24",
      progress: 0,
      status: "pending",
      owner: "测试+产品",
    },
  ]);

  const [risks, setRisks] = useState<Risk[]>(
    COMMON_RISKS.map((r, i) => ({ ...r, id: `${i + 1}` }))
  );

  const [standupReport, setStandupReport] = useState<StandupReport>({
    date: new Date().toISOString().split("T")[0],
    yesterday: ["完成病理科用户访谈", "整理用户旅程地图"],
    today: ["完善PRD第三章业务流程", "准备评审材料"],
    blockers: ["需要财务科确认押金金额标准"],
    risks: ["评审时间未确定，可能影响排期"],
  });

  const getStatusColor = (status: Milestone["status"]) => {
    const colors = {
      pending: "bg-slate-100 text-slate-600 dark:bg-slate-700",
      "in-progress": "bg-sky-100 text-sky-700 dark:bg-sky-900/30",
      completed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30",
      delayed: "bg-rose-100 text-rose-700 dark:bg-rose-900/30",
    };
    return colors[status];
  };

  const getRiskLevel = (probability: string, impact: string) => {
    if (probability === "high" && impact === "high") return { label: "极高", color: "bg-rose-100 text-rose-700" };
    if (probability === "high" || impact === "high") return { label: "高", color: "bg-orange-100 text-orange-700" };
    if (probability === "medium" && impact === "medium") return { label: "中", color: "bg-amber-100 text-amber-700" };
    return { label: "低", color: "bg-emerald-100 text-emerald-700" };
  };

  return (
    <div className="space-y-6">
      {/* 里程碑规划 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          📅 里程碑规划
        </h3>

        <div className="space-y-3">
          {milestones.map((m, index) => (
            <div key={m.id} className="relative">
              {/* 时间线 */}
              {index < milestones.length - 1 && (
                <div className="absolute left-4 top-8 h-full w-0.5 bg-slate-200 dark:bg-slate-700" />
              )}

              <div className="flex items-start gap-3">
                {/* 状态点 */}
                <div
                  className={`z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
                    m.status === "completed"
                      ? "bg-emerald-500 text-white"
                      : m.status === "in-progress"
                      ? "bg-sky-500 text-white"
                      : m.status === "delayed"
                      ? "bg-rose-500 text-white"
                      : "bg-slate-300 text-slate-600"
                  }`}
                >
                  {m.status === "completed" ? "✓" : index + 1}
                </div>

                {/* 内容 */}
                <div className="flex-1 rounded-lg bg-slate-50 p-3 dark:bg-slate-700/50">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-slate-800 dark:text-slate-200">
                        {m.name}
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {m.startDate} ~ {m.endDate} · 负责人: {m.owner}
                      </div>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${getStatusColor(
                        m.status
                      )}`}
                    >
                      {m.status === "in-progress"
                        ? "进行中"
                        : m.status === "completed"
                        ? "已完成"
                        : m.status === "delayed"
                        ? "延期"
                        : "待开始"}
                    </span>
                  </div>

                  {/* 进度条 */}
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>进度</span>
                      <span>{m.progress}%</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-slate-200 dark:bg-slate-600">
                      <div
                        className="h-2 rounded-full bg-sky-500 transition-all"
                        style={{ width: `${m.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 风险管理 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          ⚠️ 风险管理
        </h3>

        <div className="space-y-3">
          {risks.map((risk) => {
            const level = getRiskLevel(risk.probability, risk.impact);
            return (
              <div
                key={risk.id}
                className={`rounded-lg p-3 ${
                  risk.status === "mitigated"
                    ? "bg-emerald-50 dark:bg-emerald-900/10"
                    : risk.status === "occurred"
                    ? "bg-rose-50 dark:bg-rose-900/10"
                    : "bg-slate-50 dark:bg-slate-700/50"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {risk.description}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${level.color}`}
                      >
                        {level.label}
                      </span>
                    </div>
                    <div className="mt-1 flex gap-4 text-xs text-slate-500">
                      <span>概率: {risk.probability === "high" ? "高" : risk.probability === "medium" ? "中" : "低"}</span>
                      <span>影响: {risk.impact === "high" ? "高" : risk.impact === "medium" ? "中" : "低"}</span>
                    </div>
                    <div className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                      <span className="font-medium">应对措施:</span> {risk.mitigation}
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                      risk.status === "mitigated"
                        ? "bg-emerald-100 text-emerald-700"
                        : risk.status === "occurred"
                        ? "bg-rose-100 text-rose-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {risk.status === "mitigated" ? "已缓解" : risk.status === "occurred" ? "已发生" : "待处理"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 站会报告生成器 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          📢 站会报告生成器
        </h3>

        <div className="space-y-4">
          {/* 日期选择 */}
          <div>
            <label className="mb-1 block text-sm text-slate-600">日期</label>
            <input
              type="date"
              value={standupReport.date}
              onChange={(e) =>
                setStandupReport({ ...standupReport, date: e.target.value })
              }
              className="rounded border border-slate-300 px-3 py-1 text-sm dark:border-slate-600 dark:bg-slate-700"
            />
          </div>

          {/* 昨日完成 */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              昨日完成
            </label>
            <ul className="space-y-1">
              {standupReport.yesterday.map((item, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                  <span className="text-emerald-500">✓</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* 今日计划 */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              今日计划
            </label>
            <ul className="space-y-1">
              {standupReport.today.map((item, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                  <span className="text-sky-500">○</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* 阻塞项 */}
          {standupReport.blockers.length > 0 && (
            <div className="rounded-lg bg-rose-50 p-3 dark:bg-rose-900/10">
              <label className="mb-2 block text-sm font-medium text-rose-800 dark:text-rose-200">
                🚧 阻塞项（需要协调）
              </label>
              <ul className="space-y-1">
                {standupReport.blockers.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-rose-700">
                    <span>•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 风险预警 */}
          {standupReport.risks.length > 0 && (
            <div className="rounded-lg bg-amber-50 p-3 dark:bg-amber-900/10">
              <label className="mb-2 block text-sm font-medium text-amber-800 dark:text-amber-200">
                ⚠️ 风险预警
              </label>
              <ul className="space-y-1">
                {standupReport.risks.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-amber-700">
                    <span>•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <button className="mt-4 w-full rounded-lg bg-sky-600 py-2 text-sm font-medium text-white hover:bg-sky-700">
          📋 复制站会报告
        </button>
      </div>
    </div>
  );
}
