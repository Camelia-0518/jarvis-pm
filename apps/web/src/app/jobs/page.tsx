"use client";

import { useEffect, useState, useCallback, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { jobsApi, JobInfo } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";
import { SkeletonCard } from "@/components/ui/Skeleton";
import Link from "next/link";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  queued: { label: "排队中", color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200" },
  running: { label: "执行中", color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" },
  succeeded: { label: "已完成", color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" },
  failed: { label: "失败", color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" },
  cancelled: { label: "已取消", color: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200" },
};

const JOB_TYPE_LABELS: Record<string, string> = {
  compliance_check: "合规检查", re_review: "再评审", prd_generation: "PRD生成",
  prototype_generation: "原型生成", export: "导出", general: "通用任务",
};

const FAILURE_TYPE_LABELS: Record<string, string> = {
  business: "业务错误", system: "系统错误", timeout: "超时",
  dependency: "依赖失败", validation: "校验失败", unknown: "未知",
};

function formatDuration(ms: number | null): string {
  if (ms == null) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(ts: string | null): string {
  if (!ts) return "-";
  return new Date(ts).toLocaleString("zh-CN");
}

function JobsContent() {
  const searchParams = useSearchParams();

  // Read context from URL
  const contextProjectId = searchParams.get("project_id") || "";
  const contextPrdId = searchParams.get("prd_id") || "";
  const contextTaskId = searchParams.get("task_id") || "";
  const contextStatus = searchParams.get("status") || "";

  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(contextStatus);
  const [typeFilter, setTypeFilter] = useState("");
  const [selectedJob, setSelectedJob] = useState<JobInfo | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [view, setView] = useState<"list" | "stats">("list");

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const p: Record<string, string | number | undefined> = { limit: 100 };
      if (statusFilter) p.status = statusFilter;
      if (typeFilter) p.job_type = typeFilter;
      if (contextProjectId) p.project_id = contextProjectId;
      if (contextPrdId) p.prd_id = contextPrdId;
      const res = await jobsApi.list(p);
      // Client-side filter for task_id if needed
      let items = res.items;
      if (contextTaskId) {
        items = items.filter((j: JobInfo) => j.task_id === contextTaskId);
      }
      setJobs(items);
      setTotal(contextTaskId ? items.length : res.total);
    } catch { /* ignore */ }
    setLoading(false);
  }, [statusFilter, typeFilter, contextProjectId, contextPrdId, contextTaskId]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  // Context banner label
  const contextLabel = useMemo(() => {
    const parts: string[] = [];
    if (contextProjectId) parts.push("指定项目");
    if (contextPrdId) parts.push("指定 PRD");
    if (contextTaskId) parts.push("指定任务");
    if (parts.length === 0) return null;
    return `当前查看：${parts.join(" → ")} 的任务`;
  }, [contextProjectId, contextPrdId, contextTaskId]);

  const handleRetry = async (id: string) => {
    setRetrying(id);
    try { await jobsApi.retry(id); await fetchJobs(); } catch { /* ignore */ }
    setRetrying(null);
  };

  // ── Computed stats ──
  const stats = useMemo(() => {
    const totalJobs = jobs.length;
    const succeeded = jobs.filter((j) => j.status === "succeeded").length;
    const failed = jobs.filter((j) => j.status === "failed").length;
    const running = jobs.filter((j) => j.status === "running").length;
    const queued = jobs.filter((j) => j.status === "queued").length;
    const durations = jobs.filter((j) => j.duration_ms != null).map((j) => j.duration_ms!);
    const avgDuration = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : null;

    // By failure_type
    const byFailure: Record<string, number> = {};
    jobs.filter((j) => j.failure_type).forEach((j) => {
      const ft = j.failure_type || "unknown";
      byFailure[ft] = (byFailure[ft] || 0) + 1;
    });

    // By error_code
    const byErrorCode: Record<string, number> = {};
    jobs.filter((j) => j.error_code).forEach((j) => {
      const ec = j.error_code || "unknown";
      byErrorCode[ec] = (byErrorCode[ec] || 0) + 1;
    });

    // Timeout / stuck
    const stuckJobs = jobs.filter((j) => j.status === "running" && j.started_at &&
      (Date.now() - new Date(j.started_at).getTime()) > 600_000); // 10 min
    const retryJobs = jobs.filter((j) => j.attempt > 1);

    return {
      totalJobs, succeeded, failed, running, queued,
      successRate: totalJobs > 0 ? Math.round((succeeded / (succeeded + failed || 1)) * 100) : 0,
      avgDuration, byFailure, byErrorCode,
      stuckCount: stuckJobs.length,
      retryCount: retryJobs.length,
    };
  }, [jobs]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <NavHeader />
      <main className="mx-auto max-w-7xl px-4 py-8">
        {contextLabel && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-800 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
            {contextLabel}
          </div>
        )}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">任务中心</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">共 {total} 个任务</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setView("list")}
              className={`rounded-lg px-3 py-2 text-sm ${view === "list" ? "bg-blue-600 text-white" : "bg-white text-gray-700 border dark:bg-gray-800 dark:text-gray-300"}`}>列表</button>
            <button onClick={() => setView("stats")}
              className={`rounded-lg px-3 py-2 text-sm ${view === "stats" ? "bg-blue-600 text-white" : "bg-white text-gray-700 border dark:bg-gray-800 dark:text-gray-300"}`}>统计</button>
          </div>
        </div>

        {/* Stats bar (always visible) */}
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          <MiniCard label="排队" value={stats.queued} color="text-yellow-600" />
          <MiniCard label="执行中" value={stats.running} color="text-blue-600" />
          <MiniCard label="已完成" value={stats.succeeded} color="text-green-600" />
          <MiniCard label="失败" value={stats.failed} color="text-red-600" />
          <MiniCard label="成功率" value={`${stats.successRate}%`}
            color={stats.successRate >= 90 ? "text-green-600" : stats.successRate >= 70 ? "text-amber-600" : "text-red-600"} />
          <MiniCard label="平均耗时" value={stats.avgDuration ? formatDuration(stats.avgDuration) : "-"} color="text-gray-600" />
        </div>

        {/* Alert bar */}
        {(stats.stuckCount > 0 || stats.retryCount > 0) && (
          <div className="mb-4 flex gap-3">
            {stats.stuckCount > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400">
                ⚠ {stats.stuckCount} 个任务运行超过 10 分钟，可能已卡住
              </div>
            )}
            {stats.retryCount > 0 && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
                🔄 {stats.retryCount} 个任务已重试
              </div>
            )}
          </div>
        )}

        {view === "stats" && (
          <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Failure type breakdown */}
            <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
              <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">失败类型分布</h3>
              {Object.keys(stats.byFailure).length === 0 ? (
                <p className="text-sm text-gray-500">暂无失败数据</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(stats.byFailure).sort(([, a], [, b]) => b - a).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400">{FAILURE_TYPE_LABELS[type] || type}</span>
                      <span className="font-medium text-gray-900 dark:text-white">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Error code breakdown */}
            <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
              <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">错误码 Top 5</h3>
              {Object.keys(stats.byErrorCode).length === 0 ? (
                <p className="text-sm text-gray-500">暂无错误码数据</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(stats.byErrorCode).sort(([, a], [, b]) => b - a).slice(0, 5).map(([code, count]) => (
                    <div key={code} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-xs text-gray-600 dark:text-gray-400">{code}</span>
                      <span className="font-medium text-gray-900 dark:text-white">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-4 flex gap-3">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
            <option value="">全部状态</option>
            {Object.entries(STATUS_MAP).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
            <option value="">全部类型</option>
            {Object.entries(JOB_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>

        {/* Job list */}
        {loading ? (
          <div className="space-y-3">{[1, 2, 3].map((i) => <SkeletonCard key={i} />)}</div>
        ) : jobs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 bg-white py-16 text-center dark:border-gray-700 dark:bg-gray-900">
            <p className="text-gray-500 dark:text-gray-400">暂无任务</p>
            <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">系统任务将在执行后自动出现在这里</p>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => {
              const status = STATUS_MAP[job.status || ""] || { label: job.status || "-", color: "bg-gray-100" };
              const isStuck = job.status === "running" && job.started_at && (Date.now() - new Date(job.started_at).getTime()) > 600_000;
              return (
                <div key={job.id} onClick={() => setSelectedJob(job)}
                  className="cursor-pointer rounded-xl border border-gray-200 bg-white p-4 transition hover:shadow-md dark:border-gray-800 dark:bg-gray-900">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${status.color}`}>{status.label}</span>
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {JOB_TYPE_LABELS[job.job_type || ""] || job.job_type}
                      </span>
                      {job.failure_type && (
                        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-800">
                          {FAILURE_TYPE_LABELS[job.failure_type] || job.failure_type}
                        </span>
                      )}
                      {job.error_code && (
                        <span className="font-mono text-xs text-gray-400">{job.error_code}</span>
                      )}
                      {isStuck && <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">卡住</span>}
                      {job.attempt > 1 && <span className="text-xs text-gray-400">已重试 {job.attempt - 1} 次</span>}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>尝试 {job.attempt}/{job.max_attempts}</span>
                      <span>{formatDuration(job.duration_ms)}</span>
                      <span>{formatTime(job.created_at)}</span>
                    </div>
                  </div>
                  {job.error_message && (
                    <p className="mt-2 text-xs text-red-600 dark:text-red-400 truncate">{job.error_message}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Detail modal */}
        {selectedJob && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSelectedJob(null)}>
            <div className="max-h-[80vh] w-full max-w-lg overflow-auto rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-900" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900 dark:text-white">任务详情</h3>
                <button onClick={() => setSelectedJob(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
              </div>
              <dl className="space-y-2 text-sm">
                <DetailRow label="ID" value={selectedJob.id} />
                <DetailRow label="类型" value={JOB_TYPE_LABELS[selectedJob.job_type || ""] || selectedJob.job_type} />
                <DetailRow label="状态" value={STATUS_MAP[selectedJob.status || ""]?.label || selectedJob.status} />
                {selectedJob.failure_type && <DetailRow label="失败类型" value={FAILURE_TYPE_LABELS[selectedJob.failure_type] || selectedJob.failure_type} />}
                {selectedJob.error_code && <DetailRow label="错误码" value={selectedJob.error_code} />}
                {selectedJob.error_message && <DetailRow label="错误信息" value={selectedJob.error_message} />}
                <DetailRow label="耗时" value={formatDuration(selectedJob.duration_ms)} />
                <DetailRow label="尝试次数" value={`${selectedJob.attempt}/${selectedJob.max_attempts}`} />
                {selectedJob.retryable && selectedJob.next_retry_at && (
                  <DetailRow label="下次重试" value={formatTime(selectedJob.next_retry_at)} />
                )}
                <DetailRow label="开始时间" value={formatTime(selectedJob.started_at)} />
                <DetailRow label="完成时间" value={formatTime(selectedJob.completed_at)} />
              </dl>
              <div className="mt-4 flex gap-2">
                {selectedJob.retryable && (
                  <button onClick={() => { handleRetry(selectedJob.id); setSelectedJob(null); }}
                    disabled={retrying === selectedJob.id}
                    className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                    {retrying === selectedJob.id ? "重试中..." : "重新执行"}
                  </button>
                )}
                <Link href="/audit" className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-center text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  查看审计日志
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 dark:bg-gray-950"><NavHeader /><main className="mx-auto max-w-7xl px-4 py-8"><p className="text-gray-500">加载中...</p></main></div>}>
      <JobsContent />
    </Suspense>
  );
}

function MiniCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-0.5 text-lg font-bold ${color}`}>{value}</p>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between border-b border-gray-100 py-1 dark:border-gray-800">
      <span className="text-gray-500">{label}</span>
      <span className="max-w-[60%] truncate text-right text-gray-900 dark:text-white">{value || "-"}</span>
    </div>
  );
}
