"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useDeliveryStore } from "@/stores/deliveryStore";
import { useProjectStore } from "@/stores/projectStore";
import { deliveryApi, type DeliveryDashboardData } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";
import MethodologyPanel from "@/components/delivery/MethodologyPanel";
import DeliverySummaryCard from "@/components/delivery/DeliverySummaryCard";
import { devError } from "@/utils/logger";
import { toast } from "sonner";

export default function DeliveryDashboard() {
  const { plans, fetchPlans, isLoadingList, generatePlan, isGenerating, generationProgress } = useDeliveryStore();
  const { projects = [], fetchProjects } = useProjectStore();
  const [dashboard, setDashboard] = useState<DeliveryDashboardData | null>(null);
  const [showGenerator, setShowGenerator] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [teamSize, setTeamSize] = useState(5);
  const [selectedPRDId, setSelectedPRDId] = useState("");
  const [projectPRDs, setProjectPRDs] = useState<{ id: string; title: string }[]>([]);

  useEffect(() => {
    fetchProjects();
    fetchPlans();
    deliveryApi.getDashboard().then(setDashboard).catch((err: unknown) => { devError("Failed to load delivery dashboard", err); });
  }, [fetchProjects, fetchPlans]);

  const handleGenerate = async () => {
    if (!selectedProjectId) {
      toast.error("请选择项目");
      return;
    }
    const planId = await generatePlan({
      project_id: selectedProjectId,
      prd_id: selectedPRDId || undefined,
      team_size: teamSize,
    });
    if (planId) {
      toast.success("交付计划生成成功！");
      setShowGenerator(false);
      fetchPlans();
      deliveryApi.getDashboard().then(setDashboard).catch((err: unknown) => { devError("Failed to load delivery dashboard", err); });
    } else {
      toast.error("生成失败，请重试");
    }
  };

  const handleLoadPRDs = async (projectId: string) => {
    setSelectedProjectId(projectId);
    setSelectedPRDId("");
    if (!projectId) {
      setProjectPRDs([]);
      return;
    }
    try {
      // Fetch PRDs for this project by listing all PRDs and filtering
      const { prdApi } = await import("@/lib/api");
      const result = await prdApi.list({ projectId, limit: 20 });
      setProjectPRDs((result.items || []).map((p: { id: string; title: string }) => ({ id: p.id, title: p.title })));
    } catch {
      setProjectPRDs([]);
    }
  };

  const selectedProject = projects.find((p) => p.name);

  const statusLabel = (s: string) => {
    const map: Record<string, string> = { draft: "草稿", in_progress: "进行中", at_risk: "有风险", completed: "已完成" };
    return map[s] || s;
  };
  const statusColor = (s: string) => {
    const map: Record<string, string> = {
      draft: "bg-slate-100 text-slate-600",
      in_progress: "bg-blue-100 text-blue-700",
      at_risk: "bg-red-100 text-red-700",
      completed: "bg-green-100 text-green-700",
    };
    return map[s] || "bg-slate-100";
  };

  const healthDot = (color: string) => {
    const map: Record<string, string> = {
      red: "bg-red-500",
      yellow: "bg-yellow-500",
      green: "bg-green-500",
    };
    return map[color] || "bg-slate-400";
  };

  const healthBorder = (color: string) => {
    const map: Record<string, string> = {
      red: "border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/30",
      yellow: "border-yellow-200 bg-yellow-50/50 dark:border-yellow-800 dark:bg-yellow-950/30",
      green: "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/30",
    };
    return map[color] || "";
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <button
          onClick={() => setShowGenerator(true)}
            disabled={isGenerating}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {isGenerating ? generationProgress : "+ 生成交付计划"}
          </button>
      </NavHeader>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {/* Dashboard Cards */}
        {dashboard && (
          <>
            {/* Row 1: Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                <div className="text-xs text-slate-500 mb-1">交付计划</div>
                <div className="text-2xl font-bold text-slate-800 dark:text-slate-200">{dashboard.total_plans}</div>
                <div className="text-xs text-slate-400 mt-1 flex gap-2 flex-wrap">
                  {dashboard.completed > 0 && <span className="text-green-600">{dashboard.completed} 完成</span>}
                  {dashboard.in_progress > 0 && <span className="text-blue-600">{dashboard.in_progress} 进行中</span>}
                  {dashboard.draft > 0 && <span className="text-slate-400">{dashboard.draft} 草稿</span>}
                  {dashboard.at_risk > 0 && <span className="text-red-600">{dashboard.at_risk} 有风险</span>}
                </div>
              </div>
              <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                <div className="text-xs text-slate-500 mb-1">任务进度</div>
                <div className="text-2xl font-bold text-slate-800 dark:text-slate-200">
                  {dashboard.total_tasks > 0 ? `${Math.round(dashboard.task_completion_rate * 100)}%` : "—"}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {dashboard.completed_tasks}/{dashboard.total_tasks} 完成
                  {dashboard.in_progress_tasks > 0 && ` · ${dashboard.in_progress_tasks} 进行中`}
                </div>
              </div>
              <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                <div className="text-xs text-slate-500 mb-1">阶段进度</div>
                <div className="text-2xl font-bold text-slate-800 dark:text-slate-200">
                  {dashboard.total_phases > 0 ? `${dashboard.avg_phase_progress}%` : "—"}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {dashboard.total_phases} 个阶段
                  {dashboard.overdue_phases > 0 && (
                    <span className="text-red-500 ml-1">{dashboard.overdue_phases} 个逾期</span>
                  )}
                </div>
              </div>
              <div className="rounded-xl border bg-white dark:bg-slate-950 p-4">
                <div className="text-xs text-slate-500 mb-1">风险总数</div>
                <div className="text-2xl font-bold text-slate-800 dark:text-slate-200">{dashboard.total_risks}</div>
                <div className="text-xs text-slate-400 mt-1">
                  平均 {dashboard.health_detail?.risk.avg_risks_per_plan ?? 0} 个/计划
                  {dashboard.high_risks > 0 && (
                    <span className="text-red-500 ml-1">{dashboard.high_risks} 个高/极高</span>
                  )}
                </div>
              </div>
            </div>

            {/* Row 2: Health scores with breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              <div className={`rounded-xl border p-4 ${healthBorder(dashboard.delivery_health)}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-semibold text-slate-700 dark:text-slate-300">交付健康度</div>
                  <div className="flex items-center gap-1.5">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${healthDot(dashboard.delivery_health)}`} />
                    <span className={`text-sm font-bold ${
                      dashboard.delivery_health === "green" ? "text-green-700 dark:text-green-400"
                      : dashboard.delivery_health === "yellow" ? "text-yellow-700 dark:text-yellow-400"
                      : "text-red-700 dark:text-red-400"
                    }`}>
                      {dashboard.delivery_health === "green" ? "健康" : dashboard.delivery_health === "yellow" ? "需关注" : "有风险"}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-lg bg-white/60 dark:bg-slate-900/60 p-2">
                    <div className="text-lg font-bold text-slate-700 dark:text-slate-300">
                      {Math.round((dashboard.health_detail?.delivery.active_ratio ?? 0) * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-400">活跃率<br />(非草稿占比)</div>
                  </div>
                  <div className="rounded-lg bg-white/60 dark:bg-slate-900/60 p-2">
                    <div className="text-lg font-bold text-slate-700 dark:text-slate-300">
                      {Math.round((dashboard.health_detail?.delivery.task_completion ?? 0) * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-400">任务完成率</div>
                  </div>
                  <div className="rounded-lg bg-white/60 dark:bg-slate-900/60 p-2">
                    <div className={`text-lg font-bold ${dashboard.overdue_phases > 0 ? "text-red-600" : "text-slate-700 dark:text-slate-300"}`}>
                      {dashboard.overdue_phases}
                    </div>
                    <div className="text-[10px] text-slate-400">逾期阶段</div>
                  </div>
                </div>
              </div>

              <div className={`rounded-xl border p-4 ${healthBorder(dashboard.risk_health)}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm font-semibold text-slate-700 dark:text-slate-300">风险健康度</div>
                  <div className="flex items-center gap-1.5">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${healthDot(dashboard.risk_health)}`} />
                    <span className={`text-sm font-bold ${
                      dashboard.risk_health === "green" ? "text-green-700 dark:text-green-400"
                      : dashboard.risk_health === "yellow" ? "text-yellow-700 dark:text-yellow-400"
                      : "text-red-700 dark:text-red-400"
                    }`}>
                      {dashboard.risk_health === "green" ? "安全" : dashboard.risk_health === "yellow" ? "需关注" : "危险"}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-lg bg-white/60 dark:bg-slate-900/60 p-2">
                    <div className={`text-lg font-bold ${dashboard.at_risk > 0 ? "text-red-600" : "text-slate-700 dark:text-slate-300"}`}>
                      {dashboard.at_risk}
                    </div>
                    <div className="text-[10px] text-slate-400">告急计划</div>
                  </div>
                  <div className="rounded-lg bg-white/60 dark:bg-slate-900/60 p-2">
                    <div className={`text-lg font-bold ${(dashboard.health_detail?.risk.high_risk_ratio ?? 0) > 0.4 ? "text-red-600" : "text-slate-700 dark:text-slate-300"}`}>
                      {Math.round((dashboard.health_detail?.risk.high_risk_ratio ?? 0) * 100)}%
                    </div>
                    <div className="text-[10px] text-slate-400">高风险占比</div>
                  </div>
                  <div className="rounded-lg bg-white/60 dark:bg-slate-900/60 p-2">
                    <div className="text-lg font-bold text-slate-700 dark:text-slate-300">
                      {dashboard.health_detail?.risk.avg_risks_per_plan ?? 0}
                    </div>
                    <div className="text-[10px] text-slate-400">平均风险/计划</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Blockage / Risk / Next Action summary */}
            <DeliverySummaryCard
              data={{
                highRiskCount: dashboard.high_risks,
                totalRisks: dashboard.total_risks,
                overduePhases: dashboard.overdue_phases,
                taskCompletionRate: dashboard.task_completion_rate,
                atRiskPlans: dashboard.at_risk,
                failedJobsCount: 0,
              }}
            />
          </>
        )}

        {/* Plans list */}
        <div className="rounded-xl border bg-white dark:bg-slate-950">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">交付计划列表</h2>
          </div>
          {isLoadingList ? (
            <div className="p-8 text-center text-slate-500">加载中...</div>
          ) : plans.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-slate-500 mb-3">还没有交付计划</p>
              <button
                onClick={() => setShowGenerator(true)}
                className="text-sm text-sky-600 hover:text-sky-700 font-medium"
              >
                生成第一个交付计划 →
              </button>
            </div>
          ) : (
            <div className="divide-y">
              {plans.map((plan) => (
                <Link
                  key={plan.id}
                  href={`/delivery/${plan.id}`}
                  className="flex items-center justify-between p-4 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{plan.title}</h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                      <span>{plan.wbs_task_count} 任务</span>
                      <span>{plan.risk_count} 风险</span>
                      <span>{plan.milestone_count} 里程碑</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${statusColor(plan.status)}`}>
                      {statusLabel(plan.status)}
                    </span>
                    <span className="text-xs text-slate-400">
                      {plan.created_at ? new Date(plan.created_at).toLocaleDateString("zh-CN") : ""}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Delivery Methodology */}
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <MethodologyPanel />
      </section>

      {/* Generator Modal */}
      {showGenerator && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-slate-950 rounded-xl shadow-xl w-full max-w-md p-6 mx-4">
            <h3 className="text-lg font-semibold mb-4">生成交付计划</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">选择项目</label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => handleLoadPRDs(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
                >
                  <option value="">-- 选择项目 --</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {projectPRDs.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    关联PRD（可选）
                  </label>
                  <select
                    value={selectedPRDId}
                    onChange={(e) => setSelectedPRDId(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
                  >
                    <option value="">-- 不关联 --</option>
                    {projectPRDs.map((p) => (
                      <option key={p.id} value={p.id}>{p.title}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  团队规模：{teamSize} 人
                </label>
                <input
                  type="range"
                  min={2}
                  max={20}
                  value={teamSize}
                  onChange={(e) => setTeamSize(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              {isGenerating && (
                <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-3 text-sm text-blue-700 dark:text-blue-300">
                  {generationProgress}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating || !selectedProjectId}
                  className="flex-1 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  {isGenerating ? "生成中..." : "开始生成"}
                </button>
                <button
                  onClick={() => setShowGenerator(false)}
                  disabled={isGenerating}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
