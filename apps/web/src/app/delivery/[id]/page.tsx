"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NavHeader from "@/components/global/NavHeader";
import { useDeliveryStore } from "@/stores/deliveryStore";
import KanbanBoard from "@/components/delivery/KanbanBoard";
import GanttChart from "@/components/delivery/GanttChart";
import RiskMatrix from "@/components/delivery/RiskMatrix";
import StakeholderPanel from "@/components/delivery/StakeholderPanel";
import DeliverySummaryCard from "@/components/delivery/DeliverySummaryCard";
import type { DeliveryPlanDetail, MilestonePhase, WbsTask } from "@/lib/api";

type Tab = "plan" | "wbs" | "gantt" | "risks" | "stakeholders";

/** Extract a section from markdown by heading name. */
function extractMdSection(md: string, heading: string): string {
  if (!md) return "";
  const lines = md.split("\n");
  // Match "## 标题" or "## 一、标题" etc.
  const headingRe = new RegExp(`^#{1,3}\\s+.*${heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);
  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (start === -1 && headingRe.test(lines[i])) {
      start = i;
    } else if (start >= 0 && /^#{1,3}\s/.test(lines[i]) && !headingRe.test(lines[i])) {
      return lines.slice(start, i).join("\n");
    }
  }
  if (start >= 0) return lines.slice(start).join("\n");
  return md;
}

/** Markdown section map by tab. */
const MARKDOWN_SECTIONS: Record<Tab, string[]> = {
  plan: ["项目概览", "里程碑计划"],
  wbs: ["WBS", "工作分解"],
  gantt: ["甘特图", "排期"],
  risks: ["风险", "风险分析", "风险矩阵"],
  stakeholders: ["干系人", "沟通计划", "RACI"],
};

function getTabMarkdown(plan: DeliveryPlanDetail, tab: Tab): string {
  // Prefer tab-specific markdown first
  const specificMap: Record<string, string | undefined> = {
    risks: plan.risk_markdown,
    stakeholders: plan.stakeholder_markdown,
  };
  const specific = specificMap[tab];
  if (specific) return specific;

  // Extract relevant sections from plan_markdown
  const sections = MARKDOWN_SECTIONS[tab];
  const parts = sections.map((s) => extractMdSection(plan.plan_markdown, s)).filter(Boolean);
  if (parts.length > 0) return parts.join("\n\n");
  return plan.plan_markdown;
}

/** Convert relative date strings like "第N周" to ISO date strings. */
function parseDate(raw: string, fallbackWeeks: number): string {
  if (!raw) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw;
  const weekMatch = raw.match(/第\s*(\d+)/);
  if (weekMatch) {
    const d = new Date();
    d.setDate(d.getDate() + (parseInt(weekMatch[1], 10) - 1) * 7);
    return d.toISOString().slice(0, 10);
  }
  const numMatch = raw.match(/^(\d+)$/);
  if (numMatch) {
    const d = new Date();
    d.setDate(d.getDate() + (parseInt(numMatch[1], 10) - 1) * 7);
    return d.toISOString().slice(0, 10);
  }
  const d = new Date();
  d.setDate(d.getDate() + fallbackWeeks * 7);
  return d.toISOString().slice(0, 10);
}

function parseDuration(raw: unknown): number {
  if (typeof raw === "number") return Math.max(1, raw);
  if (typeof raw !== "string") return 1;
  const num = parseFloat(raw.match(/\d+\.?\d*/)?.[0] || "1");
  if (raw.includes("月")) return Math.max(1, Math.round(num * 4));
  if (raw.includes("天") || raw.includes("日")) return Math.max(1, Math.round(num / 7));
  return Math.max(1, Math.round(num));
}

const PHASE_TASK_TEMPLATES: Record<string, string[]> = {
  "项目启动": ["项目章程编写与审批", "组建项目团队并明确角色", "召开项目启动会", "确定沟通机制与周报模板"],
  "需求分析": ["业务需求调研与访谈", "需求规格说明书编写", "需求评审与签字确认", "UI/UX原型设计与评审"],
  "系统设计": ["系统架构设计", "数据库设计与评审", "接口规范定义", "安全方案设计"],
  "开发实施": ["迭代1：核心功能开发", "迭代2：扩展功能开发", "迭代3：集成联调", "代码评审与单元测试"],
  "测试验证": ["功能测试(SIT)", "集成测试", "性能与压力测试", "用户验收测试(UAT)"],
  "部署上线": ["生产环境部署", "数据迁移与校验", "灰度发布", "正式上线切换"],
  "培训与交接": ["管理员培训", "操作员培训", "培训考核", "运维文档移交", "项目验收"],
  "运维保障": ["上线后陪跑", "问题跟踪修复", "月度运维报告", "知识库沉淀"],
};

function generateWbsFromPhases(phases: MilestonePhase[]): WbsTask[] {
  const tasks: WbsTask[] = [];
  let tid = 1;
  for (const phase of phases) {
    const phaseName: string = phase.name || "";
    let templates: string[] | undefined;
    for (const [key, tmpl] of Object.entries(PHASE_TASK_TEMPLATES)) {
      if (phaseName.includes(key)) { templates = tmpl; break; }
    }
    const taskNames = templates || (phase.deliverables || []).slice(0, 4);
    const finalNames = taskNames.length > 0 ? taskNames : [`${phaseName}任务1`, `${phaseName}任务2`, `${phaseName}任务3`];
    finalNames.forEach((name: string) => {
      const effortDays = Math.max(2, Math.min(15, name.length * 2 + 3));
      tasks.push({
        id: `WBS-${String(tid).padStart(3, "0")}`,
        phase_id: phase.phase_id,
        phase_name: phaseName,
        name,
        effort_days: effortDays,
        dependencies: tid > 1 ? [tasks[tasks.length - 1]?.id].filter(Boolean) : [],
        role: "开发工程师",
        priority: "P1",
        phase: "一期",
        status: "todo",
      });
      tid++;
    });
  }
  return tasks;
}

function normalizePlan(raw: DeliveryPlanDetail): DeliveryPlanDetail {
  const plan = { ...raw };

  // Normalize phases
  const rawPhases = Array.isArray(plan.milestones)
    ? plan.milestones
    : plan.milestones?.phases || [];
  const normalizedPhases: MilestonePhase[] = [];
  if (rawPhases.length > 0) {
    normalizedPhases.push(
      ...rawPhases.map(
        (p: MilestonePhase, i: number) => {
          const dur = parseDuration(p.duration_weeks ?? p.duration);
          return {
            ...p,
            start: parseDate(p.start || p.startDate || "", i * 2),
            end: parseDate(p.end || p.endDate || "", i * 2 + dur),
            duration_weeks: dur,
            phase_id: p.phase_id || `phase-${i + 1}`,
            name: p.name || `阶段${i + 1}`,
            deliverables: Array.isArray(p.deliverables) ? p.deliverables : [],
            milestone: p.milestone || `${p.name || `阶段${i + 1}`}完成`,
            checkpoint: Boolean(p.checkpoint),
            progress: typeof p.progress === "number" ? p.progress : 0,
          };
        }
      )
    );
      const base = (Array.isArray(plan.milestones) ? {} : plan.milestones || {}) as Record<string, unknown>;
    plan.milestones = { ...base, phases: normalizedPhases } as typeof plan.milestones;
  }

  // Generate WBS tasks from phases if wbs is empty
  const wbs = plan.wbs || {};
  const existingTasks = (wbs as Record<string, unknown>).tasks as unknown[] | undefined;
  if (!existingTasks || existingTasks.length === 0) {
    const generatedTasks = generateWbsFromPhases(normalizedPhases);
    plan.wbs = {
          ...(wbs as Record<string, unknown>),
      tasks: generatedTasks,
      total_tasks: generatedTasks.length,
          total_effort_days: generatedTasks.reduce((s, t) => s + (t.effort_days || 0), 0),
    };
  }

  // Normalize risks
  const risks = Array.isArray(plan.risks) ? plan.risks : [];
  if (risks.length > 0) {
      plan.risks = risks.map((r, i) => ({
      ...r,
      id: r.id || `RSK-${i + 1}`,
      risk: r.risk || r.description || "",
      prevention: r.prevention || r.mitigation || "",
      probability: typeof r.probability === "number" ? r.probability : 0.5,
      impact: typeof r.impact === "number" ? r.impact : 0.5,
      risk_score: typeof r.risk_score === "number" ? r.risk_score : 0.25,
      risk_level: r.risk_level || "中",
      category: r.category || "",
      contingency: r.contingency || "",
      trigger: r.trigger || "",
      owner: r.owner || "",
    }));
  }

  return plan;
}

export default function DeliveryPlanDetail() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { currentPlan, fetchPlan, isLoadingPlan, planError, updateTask, updatePhase } = useDeliveryStore();
  const [activeTab, setActiveTab] = useState<Tab>("plan");
  const [markdownView, setMarkdownView] = useState(false);

  const plan = useMemo(() => currentPlan ? normalizePlan(currentPlan) : null, [currentPlan]);

  useEffect(() => {
    if (id) fetchPlan(id);
  }, [id, fetchPlan]);

  const handleTaskUpdate = useCallback(
    (taskId: string, patch: Record<string, unknown>) => {
      if (id) updateTask(id, taskId, patch);
    },
    [id, updateTask]
  );

  const handlePhaseUpdate = useCallback(
    (phaseId: string, patch: Record<string, unknown>) => {
      if (id) updatePhase(id, phaseId, patch);
    },
    [id, updatePhase]
  );

  const handlePhaseProgress = useCallback(
    (phaseId: string, progress: number) => {
      if (id) updatePhase(id, phaseId, { progress });
    },
    [id, updatePhase]
  );

  // Handle Gantt item update — translates to task updates
  const handleGanttUpdate = useCallback(
    (itemId: string, patch: Record<string, unknown>) => {
      if (id) updateTask(id, itemId, patch);
    },
    [id, updateTask]
  );

  if (isLoadingPlan) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-slate-500">加载中...</div>
      </div>
    );
  }

  if (planError || !plan) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{planError || "未找到交付计划"}</p>
          <Link href="/delivery" className="text-sky-600 hover:text-sky-700 text-sm font-medium">
            ← 返回交付中心
          </Link>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; count?: string }[] = [
    { key: "plan", label: "交付计划" },
    { key: "wbs", label: "WBS看板", count: String(plan.wbs?.total_tasks ?? 0) },
    { key: "gantt", label: "甘特图" },
    { key: "risks", label: "风险管理", count: String(plan.risks?.length ?? 0) },
    { key: "stakeholders", label: "干系人" },
  ];

  const statusLabel = (s: string) => {
    const map: Record<string, string> = { draft: "草稿", in_progress: "进行中", at_risk: "有风险", completed: "已完成" };
    return map[s] || s;
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <h1 className="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[200px]">
          {plan.title}
        </h1>
        <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
          {statusLabel(plan.status)}
        </span>
      </NavHeader>

      {/* Summary bar */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard label="WBS 任务" value={`${plan.wbs?.tasks?.length ?? 0}`} color="text-blue-600" />
          <SummaryCard label="风险项" value={`${plan.risks?.length ?? 0}`} color={(plan.risks ?? []).some((r) => r.risk_level === "高" || r.risk_level === "high") ? "text-red-600" : "text-amber-600"} />
          <SummaryCard label="里程碑" value={`${plan.milestones?.phases?.length ?? 0} 阶段`} color="text-purple-600" />
          <SummaryCard label="干系人" value={`${plan.stakeholders?.length ?? 0}`} color="text-green-600" />
        </div>

        {/* Blockage / Risk / Next Action summary */}
        <div className="mt-4">
          <DeliverySummaryCard
            variant="detail"
            data={{
              planId: id,
              projectId: plan.project_id,
              planStatus: plan.status,
              highRiskCount: (plan.risks ?? []).filter((r) => r.risk_level === "高" || r.risk_level === "high").length,
              totalRisks: plan.risks?.length ?? 0,
              overduePhases: (plan.milestones?.phases ?? []).filter((p: { progress?: number; end?: string }) => (p.progress ?? 0) < 100 && p.end && new Date(p.end) < new Date()).length,
              taskCompletionRate: plan.wbs?.total_tasks ? (plan.wbs.tasks.filter((t: { status?: string }) => t.status === "done" || t.status === "completed").length / plan.wbs.total_tasks) : 0,
              atRiskPlans: 0,
            }}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b bg-white dark:bg-slate-950 sticky top-0 z-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-6 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setActiveTab(tab.key); setMarkdownView(false); }}
                className={`flex items-center gap-1.5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.key
                    ? "border-sky-600 text-sky-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab.label}
                {tab.count && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {/* ========== Plan tab ========== */}
        {activeTab === "plan" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">交付计划概览</h2>
              <button
                onClick={() => setMarkdownView(!markdownView)}
                className="text-sm text-sky-600 hover:text-sky-700 font-medium"
              >
                {markdownView ? "卡片视图" : "Markdown视图"}
              </button>
            </div>

            {markdownView ? (
              <div className="prose prose-sm max-w-none dark:prose-invert bg-white dark:bg-slate-950 rounded-xl border p-6">
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 dark:text-slate-300">
                  {getTabMarkdown(plan, "plan")}
                </pre>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Milestones with progress bars */}
                <div className="rounded-xl border bg-white dark:bg-slate-950 p-6">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">里程碑时间线</h3>
                  <div className="relative">
                    {plan.milestones?.phases?.map((phase, i) => {
                                          const progress = phase.progress || 0;
                      return (
                        <div key={phase.phase_id} className="flex gap-4 pb-6 relative">
                          <div className="flex flex-col items-center">
                            <div className={`w-3 h-3 rounded-full border-2 ${
                              progress >= 100 ? "bg-green-500 border-green-500"
                              : progress > 0 ? "bg-sky-500 border-sky-500"
                              : phase.checkpoint ? "border-sky-300 bg-white dark:bg-slate-900"
                              : "bg-white border-slate-300 dark:bg-slate-900 dark:border-slate-600"
                            }`} />
                            {i < (plan.milestones?.phases?.length ?? 0) - 1 && (
                              <div className={`w-0.5 h-full mt-1 ${
                                progress >= 100 ? "bg-green-200 dark:bg-green-800"
                                : progress > 0 ? "bg-sky-200 dark:bg-sky-800"
                                : "bg-slate-200 dark:bg-slate-700"
                              }`} />
                            )}
                          </div>
                          <div className="flex-1 min-w-0 pb-2">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="text-sm font-medium text-slate-800 dark:text-slate-200">
                                {phase.name}
                              </h4>
                              {phase.checkpoint && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-300">
                                  评审点
                                </span>
                              )}
                              <span className="text-[10px] text-slate-400 ml-auto">{progress}%</span>
                            </div>
                            <div className="text-xs text-slate-500 mb-1.5">
                              {phase.start} ~ {phase.end} · {phase.duration_weeks}周
                            </div>
                            {/* Progress bar */}
                            <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all duration-300 ${
                                  progress >= 100 ? "bg-green-500" : progress > 50 ? "bg-sky-500" : "bg-sky-400"
                                }`}
                                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
                              />
                            </div>
                            {/* Progress slider */}
                            <input
                              type="range"
                              min={0}
                              max={100}
                              value={progress}
                              onChange={(e) => handlePhaseProgress(phase.phase_id, parseInt(e.target.value, 10))}
                              className="w-full h-1 mt-1 appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-sky-500 [&::-webkit-slider-thumb]:opacity-0 hover:[&::-webkit-slider-thumb]:opacity-100"
                            />
                            <div className="flex flex-wrap gap-1 mt-1">
                              {phase.deliverables.slice(0, 3).map((d, j) => (
                                <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                                  {d.length > 20 ? d.slice(0, 20) + "..." : d}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {plan.resources && (
                    <div className="mt-2 pt-4 border-t border-slate-200 dark:border-slate-700">
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {plan.resources.recommendation}
                      </p>
                    </div>
                  )}
                </div>

                {/* Summary stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">总任务</div>
                    <div className="text-xl font-bold">{plan.wbs?.total_tasks ?? 0}</div>
                  </div>
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">总工作量</div>
                    <div className="text-xl font-bold">{plan.wbs?.total_effort_days ?? 0}<span className="text-sm font-normal text-slate-400">人天</span></div>
                  </div>
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">风险数</div>
                    <div className="text-xl font-bold">{plan.risks?.length ?? 0}</div>
                  </div>
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">干系人</div>
                    <div className="text-xl font-bold">{plan.stakeholders?.length ?? 0}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========== WBS (Kanban) tab ========== */}
        {activeTab === "wbs" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
                WBS 任务看板
              </h2>
              <button
                onClick={() => setMarkdownView(!markdownView)}
                className="text-sm text-sky-600 hover:text-sky-700 font-medium"
              >
                {markdownView ? "看板视图" : "Markdown视图"}
              </button>
            </div>
            {markdownView ? (
              <div className="prose prose-sm max-w-none dark:prose-invert bg-white dark:bg-slate-950 rounded-xl border p-6">
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 dark:text-slate-300">
                  {getTabMarkdown(plan, "wbs")}
                </pre>
              </div>
            ) : plan.wbs?.tasks?.length ? (
              <KanbanBoard tasks={plan.wbs.tasks} onTaskUpdate={handleTaskUpdate} />
            ) : (
              <p className="text-sm text-slate-500">暂无WBS数据</p>
            )}
          </div>
        )}

        {/* ========== Gantt tab ========== */}
        {activeTab === "gantt" && (() => {
          const ganttItems = plan.gantt?.items?.length
            ? { items: plan.gantt.items, start_date: plan.gantt.start_date, total_days: plan.gantt.total_days }
            : null;
          const phases = plan.milestones?.phases || [];
          const derivedItems = ganttItems ? null : phases.length > 0 ? (() => {
            const firstStart = phases[0]?.start || new Date().toISOString().slice(0, 10);
            const firstDate = new Date(firstStart).getTime();
            const lastEnd = phases.reduce((latest, p) => {
              const d = new Date(p.end).getTime();
              return d > latest ? d : latest;
            }, firstDate);
            const totalDays = Math.ceil((lastEnd - firstDate) / (1000 * 60 * 60 * 24));
            const items = phases.map((p, i) => ({
              id: p.phase_id || `phase-${i}`,
              name: p.name,
              phase: p.name,
              start_offset_days: Math.floor((new Date(p.start).getTime() - firstDate) / (1000 * 60 * 60 * 24)),
              duration_weeks: p.duration_weeks || 2,
              dependencies: [] as string[],
              priority: p.checkpoint ? "high" : "medium",
              role: "",
              phase_label: p.name,
            }));
            return { items, start_date: firstStart, total_days: totalDays || 90 };
          })() : null;

          const chartData = ganttItems || derivedItems;

          return (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">甘特图</h2>
                <button
                  onClick={() => setMarkdownView(!markdownView)}
                  className="text-sm text-sky-600 hover:text-sky-700 font-medium"
                >
                  {markdownView ? "图表视图" : "Markdown视图"}
                </button>
              </div>
              {markdownView ? (
                <div className="prose prose-sm max-w-none dark:prose-invert bg-white dark:bg-slate-950 rounded-xl border p-6">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 dark:text-slate-300">
                    {getTabMarkdown(plan, "gantt")}
                  </pre>
                </div>
              ) : chartData ? (
                <GanttChart
                  items={chartData.items}
                  startDate={chartData.start_date}
                  totalDays={chartData.total_days}
                  onItemUpdate={handleGanttUpdate}
                />
              ) : (
                <p className="text-sm text-slate-500">暂无甘特图数据</p>
              )}
            </div>
          );
        })()}

        {/* ========== Risks tab ========== */}
        {activeTab === "risks" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">风险分析</h2>
              <button
                onClick={() => setMarkdownView(!markdownView)}
                className="text-sm text-sky-600 hover:text-sky-700 font-medium"
              >
                {markdownView ? "图表视图" : "Markdown视图"}
              </button>
            </div>
            {markdownView ? (
              <div className="prose prose-sm max-w-none dark:prose-invert bg-white dark:bg-slate-950 rounded-xl border p-6">
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 dark:text-slate-300">
                  {getTabMarkdown(plan, "risks")}
                </pre>
              </div>
            ) : plan.risks?.length ? (
              <RiskMatrix risks={plan.risks} matrix={plan.risk_matrix} />
            ) : (
              <p className="text-sm text-slate-500">暂无风险数据</p>
            )}
          </div>
        )}

        {/* ========== Stakeholders tab ========== */}
        {activeTab === "stakeholders" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">干系人与沟通计划</h2>
              <button
                onClick={() => setMarkdownView(!markdownView)}
                className="text-sm text-sky-600 hover:text-sky-700 font-medium"
              >
                {markdownView ? "图表视图" : "Markdown视图"}
              </button>
            </div>
            {markdownView ? (
              <div className="prose prose-sm max-w-none dark:prose-invert bg-white dark:bg-slate-950 rounded-xl border p-6">
                <pre className="whitespace-pre-wrap font-sans text-sm text-slate-700 dark:text-slate-300">
                  {getTabMarkdown(plan, "stakeholders")}
                </pre>
              </div>
            ) : plan.stakeholders?.length ? (
              <StakeholderPanel
                stakeholders={plan.stakeholders}
                raci={plan.raci}
                communicationPlan={plan.communication_plan}
              />
            ) : (
              <p className="text-sm text-slate-500">暂无干系人数据</p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
