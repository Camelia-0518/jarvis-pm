"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import NavHeader from "@/components/global/NavHeader";
import { useDeliveryStore } from "@/stores/deliveryStore";
import KanbanBoard from "@/components/delivery/KanbanBoard";
import GanttChart from "@/components/delivery/GanttChart";
import RiskMatrix from "@/components/delivery/RiskMatrix";
import StakeholderPanel from "@/components/delivery/StakeholderPanel";

type Tab = "plan" | "wbs" | "gantt" | "risks" | "stakeholders";

export default function DeliveryPlanDetail() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { currentPlan, fetchPlan, isLoadingPlan, planError } = useDeliveryStore();
  const [activeTab, setActiveTab] = useState<Tab>("plan");
  const [markdownView, setMarkdownView] = useState(false);

  useEffect(() => {
    if (id) fetchPlan(id);
  }, [id]);

  if (isLoadingPlan) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-slate-500">加载中...</div>
      </div>
    );
  }

  if (planError || !currentPlan) {
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
    { key: "wbs", label: "WBS看板", count: String(currentPlan.wbs?.total_tasks ?? 0) },
    { key: "gantt", label: "甘特图" },
    { key: "risks", label: "风险管理", count: String(currentPlan.risks?.length ?? 0) },
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
          {currentPlan.title}
        </h1>
        <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
          {statusLabel(currentPlan.status)}
        </span>
      </NavHeader>

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
        {/* Plan tab */}
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
                  {currentPlan.plan_markdown}
                </pre>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Milestones */}
                <div className="rounded-xl border bg-white dark:bg-slate-950 p-6">
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-4">里程碑时间线</h3>
                  <div className="relative">
                    {currentPlan.milestones?.phases?.map((phase, i) => (
                      <div key={phase.phase_id} className="flex gap-4 pb-6 relative">
                        <div className="flex flex-col items-center">
                          <div className={`w-3 h-3 rounded-full border-2 ${
                            phase.checkpoint
                              ? "bg-sky-500 border-sky-500"
                              : "bg-white border-slate-300 dark:bg-slate-900 dark:border-slate-600"
                          }`} />
                          {i < (currentPlan.milestones?.phases?.length ?? 0) - 1 && (
                            <div className="w-0.5 h-full bg-slate-200 dark:bg-slate-700 mt-1" />
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
                          </div>
                          <div className="text-xs text-slate-500">
                            {phase.start} ~ {phase.end} · {phase.duration_weeks}周
                          </div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {phase.deliverables.slice(0, 3).map((d, j) => (
                              <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                                {d.length > 20 ? d.slice(0, 20) + "..." : d}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {currentPlan.resources && (
                    <div className="mt-2 pt-4 border-t border-slate-200 dark:border-slate-700">
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {currentPlan.resources.recommendation}
                      </p>
                    </div>
                  )}
                </div>

                {/* Summary stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">总任务</div>
                    <div className="text-xl font-bold">{currentPlan.wbs?.total_tasks ?? 0}</div>
                  </div>
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">总工作量</div>
                    <div className="text-xl font-bold">{currentPlan.wbs?.total_effort_days ?? 0}<span className="text-sm font-normal text-slate-400">人天</span></div>
                  </div>
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">风险数</div>
                    <div className="text-xl font-bold">{currentPlan.risks?.length ?? 0}</div>
                  </div>
                  <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                    <div className="text-xs text-slate-500">干系人</div>
                    <div className="text-xl font-bold">{currentPlan.stakeholders?.length ?? 0}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* WBS (Kanban) tab */}
        {activeTab === "wbs" && (
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4">
              WBS 任务看板
            </h2>
            {currentPlan.wbs?.tasks ? (
              <KanbanBoard tasks={currentPlan.wbs.tasks} />
            ) : (
              <p className="text-sm text-slate-500">暂无WBS数据</p>
            )}
          </div>
        )}

        {/* Gantt tab */}
        {activeTab === "gantt" && (
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4">甘特图</h2>
            {currentPlan.gantt?.items ? (
              <GanttChart
                items={currentPlan.gantt.items}
                startDate={currentPlan.gantt.start_date}
                totalDays={currentPlan.gantt.total_days}
              />
            ) : (
              <p className="text-sm text-slate-500">暂无甘特图数据</p>
            )}
          </div>
        )}

        {/* Risks tab */}
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
                  {currentPlan.risk_markdown}
                </pre>
              </div>
            ) : (
              currentPlan.risks && currentPlan.risk_matrix ? (
                <RiskMatrix risks={currentPlan.risks} matrix={currentPlan.risk_matrix} />
              ) : (
                <p className="text-sm text-slate-500">暂无风险数据</p>
              )
            )}
          </div>
        )}

        {/* Stakeholders tab */}
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
                  {currentPlan.stakeholder_markdown}
                </pre>
              </div>
            ) : (
              <StakeholderPanel
                stakeholders={currentPlan.stakeholders || []}
                raci={currentPlan.raci}
                communicationPlan={currentPlan.communication_plan}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
