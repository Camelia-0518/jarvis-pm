"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useProjectStore } from "@/stores/projectStore";
import { prdApi, projectApi, workflowApi, type PRDSummary, type ProjectHealthItem } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";
import { toast } from "sonner";
import { confirm } from "@/components/ui/ConfirmDialog";
import PersonaPanel from "./PersonaPanel";
import CompetitorPanel from "./CompetitorPanel";
import RequirementPanel from "./RequirementPanel";
import PRDWizard from "./PRDWizard";
import ToolPanel from "./ToolPanel";

const TOOLS = [
  { id: "research", name: "用户研究", icon: "🎯" },
  { id: "stakeholder", name: "干系人分析", icon: "👥" },
  { id: "competitor", name: "竞品分析", icon: "⚔️" },
  { id: "data", name: "数据分析", icon: "📊" },
  { id: "review", name: "评审材料", icon: "📋" },
  { id: "prototype", name: "原型设计", icon: "🎨" },
  { id: "memory", name: "语义检索", icon: "🧠" },
];

function WorkspaceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const projectId = searchParams.get("id");
  const { currentProject, fetchProject } = useProjectStore();
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"prds" | "personas" | "competitors" | "requirements">("prds");
  const [showPRDWizard, setShowPRDWizard] = useState(false);
  const [projectPRDs, setProjectPRDs] = useState<PRDSummary[]>([]);
  const [projectHealth, setProjectHealth] = useState<ProjectHealthItem | null>(null);

  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      prdApi.list({ projectId }).then((res) => setProjectPRDs(res?.items || [])).catch(() => setProjectPRDs([]));
      projectApi.healthDetail(projectId).then(setProjectHealth).catch(() => setProjectHealth(null));
    }
  }, [projectId, fetchProject]);

  const handlePRDCreated = (prdId: string) => {
    setShowPRDWizard(false);
    if (projectId) {
      prdApi.list({ projectId }).then((res) => setProjectPRDs(res?.items || [])).catch(() => {});
    }
    router.push(`/prd/${prdId}`);
  };

  const handleDeletePRD = async (prdId: string, prdTitle: string) => {
    const confirmed = await confirm({
      title: "删除 PRD",
      message: `确定要删除 PRD "${prdTitle}" 吗？此操作不可恢复。`,
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await prdApi.delete(prdId);
      setProjectPRDs((prev) => prev.filter((p) => p.id !== prdId));
    } catch (err: unknown) {
      toast.error("删除失败: " + (err instanceof Error ? err.message : "未知错误"));
    }
  };

  const refreshHealth = () => {
    if (projectId) {
      projectApi.healthDetail(projectId).then(setProjectHealth).catch(() => {});
    }
  };

  const handleQuickFix = async (chainId: string, label: string) => {
    if (!projectId || !currentProject) return;
    const toastId = toast.loading(`正在执行：${label}...`);
    try {
      const proj = currentProject;
      // Enrich context with existing PRD titles if available
      const prdContext = projectPRDs.length > 0
        ? `已有哪些文档：${projectPRDs.map(p => p.title).join("、")}。\n项目背景：${proj.description || proj.name}`
        : (proj.description || proj.name);
      const inputs: Record<string, string> = {
        idea: proj.description || proj.name,
        targetUsers: "产品团队（含医护人员和患者）",
        industry: proj.industry || "medical",
        constraints: "须符合等保三级要求",
        teamSize: "5",
        requirementAnalysis: prdContext,
        prdContent: prdContext,
      };
      const res = await workflowApi.executeChain({
        chain_id: chainId,
        inputs,
        project_id: projectId,
      });
      const execId = res.execution_id;

      // Poll until complete, then refresh health with retry
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const status = await workflowApi.getExecution(execId);
          if (status.status === "completed") {
            clearInterval(poll);
            toast.success(`${label} 完成！页面即将刷新...`, { id: toastId });
            // Delay to let DB commit propagate, then retry health fetch
            const doRefresh = async (retries: number) => {
              await new Promise(r => setTimeout(r, 1500));
              await refreshHealth();
              await prdApi.list({ projectId }).then((r) => setProjectPRDs(r?.items || [])).catch(() => {});
              // Double-check health after another delay
              if (retries > 0) {
                setTimeout(() => { refreshHealth(); }, 2000);
              }
            };
            doRefresh(2);
          } else if (status.status === "failed") {
            clearInterval(poll);
            toast.error(`${label} 失败`, { id: toastId });
          } else if (attempts > 120) {
            clearInterval(poll);
            toast.error(`${label} 超时`, { id: toastId });
          }
        } catch {
          if (attempts > 120) { clearInterval(poll); toast.error("轮询超时", { id: toastId }); }
        }
      }, 3000);
    } catch (err: unknown) {
      toast.error("启动失败: " + (err instanceof Error ? err.message : "未知错误"));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <button
          onClick={() => setShowPRDWizard(true)}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          + 新建 PRD
        </button>
      </NavHeader>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-3">
          <div className="space-y-6">
            <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                工具箱
              </h2>
              <div className="grid grid-cols-2 gap-3">
                {TOOLS.map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => setActiveTool(tool.id)}
                    className={`flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors ${
                      activeTool === tool.id
                        ? "border-sky-300 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                        : "border-slate-200 hover:border-sky-300 hover:bg-sky-50 dark:border-slate-700 dark:hover:border-sky-700 dark:hover:bg-sky-900/20"
                    }`}
                  >
                    <span className="text-2xl">{tool.icon}</span>
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                      {tool.name}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {projectHealth && (
              <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                    项目健康度
                  </h2>
                  <button
                    onClick={() => router.push(`/dashboard`)}
                    className="text-xs text-sky-600 hover:text-sky-700 font-medium"
                    title="返回仪表盘使用技能链修复"
                  >
                    修复 →
                  </button>
                </div>

                {/* Score gauge */}
                <div className="flex items-center gap-3 mb-3">
                  <div className={`text-3xl font-bold ${
                    projectHealth.risk_level === "on_track" ? "text-emerald-600" :
                    projectHealth.risk_level === "at_risk" ? "text-amber-600" : "text-rose-600"
                  }`}>
                    {projectHealth.health_score}
                  </div>
                  <div className="text-sm flex-1">
                    <div className={`font-medium ${
                      projectHealth.risk_level === "on_track" ? "text-emerald-700" :
                      projectHealth.risk_level === "at_risk" ? "text-amber-700" : "text-rose-700"
                    }`}>
                      {projectHealth.risk_level === "on_track" ? "✅ 正常" :
                       projectHealth.risk_level === "at_risk" ? "⚠️ 需关注" : "🚨 严重风险"}
                    </div>
                    {/* Mini progress bar */}
                    <div className="mt-1 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          projectHealth.health_score >= 70 ? "bg-emerald-500" :
                          projectHealth.health_score >= 40 ? "bg-amber-500" : "bg-rose-500"
                        }`}
                        style={{ width: `${projectHealth.health_score}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Score breakdown — collapsed by default */}
                <details className="mb-3 text-xs">
                  <summary className="cursor-pointer text-slate-500 hover:text-slate-700 select-none">
                    分数明细
                  </summary>
                  <div className="mt-2 space-y-1 pl-2 border-l-2 border-slate-200 dark:border-slate-700">
                    {Object.entries(projectHealth.score_breakdown || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-slate-500">{k}</span>
                        <span className={`font-medium ${Number(v) < 0 ? "text-rose-600" : "text-emerald-600"}`}>
                          {Number(v) > 0 ? "+" : ""}{v}
                        </span>
                      </div>
                    ))}
                  </div>
                </details>

                {/* Key metrics with progress bars */}
                <div className="space-y-2.5 text-sm">
                  {projectHealth.metrics && (
                    <>
                      <div>
                        <div className="flex justify-between mb-0.5">
                          <span className="text-slate-500">里程碑</span>
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {projectHealth.metrics.milestones_completed || 0}/{projectHealth.metrics.milestones_total || 0}
                          </span>
                        </div>
                        <div className="h-1 rounded-full bg-slate-200 dark:bg-slate-700">
                          <div className="h-full rounded-full bg-sky-500 transition-all"
                            style={{ width: `${projectHealth.metrics.milestone_progress_pct || 0}%` }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between mb-0.5">
                          <span className="text-slate-500">问题解决率</span>
                          <span className={`font-medium ${(projectHealth.metrics.issue_resolution_rate || 100) < 50 ? "text-rose-600" : "text-slate-700 dark:text-slate-300"}`}>
                            {projectHealth.metrics.issue_resolution_rate || 100}%
                          </span>
                        </div>
                        <div className="h-1 rounded-full bg-slate-200 dark:bg-slate-700">
                          <div className={`h-full rounded-full transition-all ${(projectHealth.metrics.issue_resolution_rate || 100) >= 80 ? "bg-emerald-500" : (projectHealth.metrics.issue_resolution_rate || 100) >= 50 ? "bg-amber-500" : "bg-rose-500"}`}
                            style={{ width: `${projectHealth.metrics.issue_resolution_rate || 100}%` }} />
                        </div>
                      </div>
                      <div className="flex justify-between pt-1">
                        <span className="text-slate-500">PRD 总量</span>
                        <span className="font-medium">
                          {projectHealth.metrics.total_prds || 0}
                          <span className="text-slate-400 text-xs ml-1">
                            (已发布 {projectHealth.metrics.published_prds || 0})
                          </span>
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">活跃风险</span>
                        <span className={`font-medium ${(projectHealth.metrics.high_risks || 0) > 2 ? "text-rose-600" : ""}`}>
                          {projectHealth.metrics.active_risks || 0}
                          {(projectHealth.metrics.high_risks || 0) > 0 && (
                            <span className="text-rose-500 text-xs ml-1">(高 {projectHealth.metrics.high_risks})</span>
                          )}
                        </span>
                      </div>
                    </>
                  )}
                </div>

                {/* Smart action list — only shows what's needed */}
                {(() => {
                  const m = projectHealth.metrics || {};
                  const hasPRDs = (m.total_prds || 0) > 0;
                  const hasPlan = (m.milestones_total || 0) > 0;
                  const issuesOk = (m.open_issues || 0) <= 5;
                  const risksOk = (m.high_risks || 0) <= 2;
                  const progressOk = (m.milestone_progress_pct || 0) >= 30 || (m.milestones_total || 0) === 0;
                  const healthy = projectHealth.risk_level === "on_track";

                  const items: Array<{ label: string; ok: boolean; okText: string; needText: string; action?: { type: "chain"; chain: string; label: string } | { type: "tab"; tab: string; label: string } | { type: "info"; label: string }; icon: string }> = [
                    {
                      label: "PRD 文档",
                      ok: hasPRDs,
                      okText: `✅ ${m.total_prds} 个 PRD`,
                      needText: "暂无 PRD",
                      action: { type: "chain", chain: "quick-prd", label: "生成 PRD" },
                      icon: "📝",
                    },
                    {
                      label: "交付计划",
                      ok: hasPlan,
                      okText: `✅ 里程碑 ${m.milestones_completed || 0}/${m.milestones_total || 0}`,
                      needText: "暂无交付计划",
                      action: { type: "chain", chain: "full-delivery", label: "生成计划" },
                      icon: "📋",
                    },
                    {
                      label: "批注问题",
                      ok: issuesOk,
                      okText: `✅ 仅 ${m.open_issues || 0} 个待解决`,
                      needText: `${m.open_issues || 0} 个待解决 — 进入 PRD 逐条处理`,
                      icon: "⚠️",
                    },
                    {
                      label: "项目风险",
                      ok: risksOk,
                      okText: `✅ 风险可控`,
                      needText: `${m.high_risks || 0} 个高风险`,
                      action: risksOk ? undefined : { type: "chain", chain: "compliance-audit", label: "合规审查" },
                      icon: "🔒",
                    },
                    {
                      label: "项目进度",
                      ok: progressOk,
                      okText: `✅ 进度 ${m.milestone_progress_pct || 0}%`,
                      needText: `进度 ${m.milestone_progress_pct || 0}% — 需手动推进`,
                      icon: "📊",
                    },
                  ];

                  if (healthy && hasPRDs && hasPlan && issuesOk && risksOk) {
                    return (
                      <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                        <div className="text-xs text-center py-2 text-emerald-600 dark:text-emerald-400 font-medium">
                          ✅ 项目健康，无需修复
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                      <h3 className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
                        {healthy ? "项目状态" : `${items.filter(i => !i.ok).length} 项需要处理`}
                      </h3>
                      <div className="space-y-1">
                        {items.map((item, i) => (
                          <div
                            key={i}
                            className={`text-xs px-2 py-1.5 rounded flex items-center justify-between gap-2 ${
                              item.ok
                                ? "bg-slate-50/50 dark:bg-slate-800/50 text-slate-400 dark:text-slate-500"
                                : "bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-400"
                            }`}
                          >
                            <span>
                              {item.icon} {item.ok ? item.okText : item.needText}
                            </span>
                            {!item.ok && item.action && (() => {
                              const action = item.action;
                              if (action.type === "chain") {
                                return (
                                  <button
                                    onClick={() => handleQuickFix(action.chain, action.label)}
                                    className="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-white dark:bg-slate-600 text-sky-600 dark:text-sky-400 hover:bg-sky-100 dark:hover:bg-slate-500 transition-colors"
                                  >
                                    {action.label}
                                  </button>
                                );
                              }
                              if (action.type === "tab") {
                                return (
                                  <button
                                    onClick={() => setActiveTab("prds")}
                                    className="flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-white dark:bg-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-100 transition-colors"
                                  >
                                    {action.label}
                                  </button>
                                );
                              }
                              return (
                                <span className="text-[10px] text-slate-400 dark:text-slate-500">
                                  {action.label}
                                </span>
                              );
                            })()}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
            <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                项目统计
              </h2>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">PRD 数量</span>
                  <span className="font-medium">{projectPRDs.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">行业</span>
                  <span className="font-medium">{currentProject?.industry || "其他"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 dark:text-slate-400">状态</span>
                  <span className="font-medium">{currentProject?.status || "active"}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="mb-4 flex gap-2">
              {[
                { id: "prds" as const, label: "PRD 文档", icon: "📝" },
                { id: "personas" as const, label: "用户画像", icon: "👤" },
                { id: "competitors" as const, label: "竞品信息", icon: "⚔️" },
                { id: "requirements" as const, label: "需求池", icon: "📋" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? "bg-sky-600 text-white"
                      : "bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  }`}
                >
                  <span>{tab.icon}</span>
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              ))}
            </div>

            {activeTab === "prds" && (
              <>
                <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                    PRD 文档
                  </h2>

                  {projectPRDs.length === 0 ? (
                    <div className="text-center py-12">
                      <div className="text-4xl mb-4">📝</div>
                      <div className="text-slate-600 dark:text-slate-300">暂无 PRD 文档</div>
                      <div className="text-sm text-slate-400 mt-2">点击"+ 新建 PRD"创建第一份文档</div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {projectPRDs.map((prd) => (
                        <div
                          key={prd.id}
                          className="group flex items-center justify-between rounded-lg border border-slate-200 p-4 hover:border-sky-300 hover:bg-sky-50 dark:border-slate-700 dark:hover:border-sky-700 dark:hover:bg-sky-900/20"
                        >
                          <Link href={`/prd/${prd.id}`} className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h3 className="font-medium text-slate-900 dark:text-white truncate">
                                {prd.title}
                              </h3>
                              {prd.doc_type && prd.doc_type !== "prd" && (
                                <span className={`flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                  prd.doc_type === "discovery" ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400" :
                                  prd.doc_type === "audit" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" :
                                  prd.doc_type === "charter" ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400" :
                                  prd.doc_type === "status_report" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
                                  prd.doc_type === "ai_model" ? "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400" :
                                  prd.doc_type === "devops" ? "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300" :
                                  prd.doc_type === "playbook" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" :
                                  prd.doc_type === "retrospective" ? "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400" :
                                  "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
                                }`}>
                                  {prd.doc_type === "discovery" ? "洞察" :
                                   prd.doc_type === "audit" ? "审查" :
                                   prd.doc_type === "charter" ? "章程" :
                                   prd.doc_type === "status_report" ? "周报" :
                                   prd.doc_type === "ai_model" ? "AI产品" :
                                   prd.doc_type === "devops" ? "DevOps" :
                                   prd.doc_type === "playbook" ? "方法" :
                                   prd.doc_type === "retrospective" ? "复盘" :
                                   prd.doc_type === "stakeholder_brief" ? "简报" : prd.doc_type}
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                              版本 {prd.version} · {prd.status}
                            </p>
                          </Link>
                          <div className="flex items-center gap-2 ml-4">
                            <span className="text-slate-400">→</span>
                            <button
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                handleDeletePRD(prd.id, prd.title);
                              }}
                              className="opacity-0 group-hover:opacity-100 transition-opacity text-xs text-rose-600 hover:text-rose-700 px-2 py-1 rounded hover:bg-rose-50 dark:hover:bg-rose-900/20"
                              title="删除 PRD"
                            >
                              删除
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {activeTool && (
                  <div className="mt-6 rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                        {TOOLS.find((t) => t.id === activeTool)?.name}
                      </h2>
                      <button
                        onClick={() => setActiveTool(null)}
                        className="text-slate-400 hover:text-slate-600"
                      >
                        ✕
                      </button>
                    </div>
                    <ToolPanel toolId={activeTool} projectId={projectId} prds={projectPRDs} />
                  </div>
                )}
              </>
            )}

            {activeTab === "personas" && projectId && (
              <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <PersonaPanel projectId={projectId} />
              </div>
            )}

            {activeTab === "competitors" && projectId && (
              <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <CompetitorPanel projectId={projectId} />
              </div>
            )}

            {activeTab === "requirements" && projectId && (
              <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <RequirementPanel projectId={projectId} />
              </div>
            )}
          </div>
        </div>
      </main>

      <PRDWizard
        projectId={projectId || ""}
        projectName={currentProject?.name || ""}
        projectDescription={currentProject?.description}
        isOpen={showPRDWizard}
        onClose={() => setShowPRDWizard(false)}
        onCreated={handlePRDCreated}
      />
    </div>
  );
}

export default function Workspace() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">加载中...</div>}>
      <WorkspaceContent />
    </Suspense>
  );
}
