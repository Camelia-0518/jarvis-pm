"use client";

import { useEffect, useState } from "react";
import { systemApi, jobsApi, JobInfo } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";

interface HealthData {
  status: string;
  database: string;
  feature_tiers: { total_endpoints: number; by_tier: Record<string, number>; production_pct: number };
}

const THRESHOLDS = {
  QUEUE_CRITICAL: 20,
  QUEUE_WARN: 10,
  FAILED_CRITICAL: 10,
  FAILED_WARN: 5,
  STUCK_CRITICAL: 5,
  STUCK_WARN: 1,
};

function thresholdColor(value: number, warn: number, critical: number): string {
  if (value >= critical) return "text-red-600";
  if (value >= warn) return "text-amber-600";
  return "text-green-600";
}

function thresholdBg(value: number, warn: number, critical: number): string {
  if (value >= critical) return "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20";
  if (value >= warn) return "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20";
  return "border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900";
}

type Alert = { level: "critical" | "warning"; message: string };

export default function SystemPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Operational metrics
  const [queuedCount, setQueuedCount] = useState(0);
  const [runningCount, setRunningCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [stuckJobs, setStuckJobs] = useState<JobInfo[]>([]);
  const [recentFailed, setRecentFailed] = useState<JobInfo[]>([]);
  const [allFailed, setAllFailed] = useState<JobInfo[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const [h, queued, running, failed, stuck, recentF, allF] = await Promise.all([
          systemApi.health(),
          jobsApi.list({ status: "queued", limit: 1 }),
          jobsApi.list({ status: "running", limit: 100 }),
          jobsApi.list({ status: "failed", limit: 100 }),
          jobsApi.list({ status: "running", limit: 100 }),
          jobsApi.list({ status: "failed", limit: 5 }),
          jobsApi.list({ status: "failed", limit: 50 }),
        ]);
        setHealth(h);
        setQueuedCount(queued.total);
        setRunningCount(running.total);
        setFailedCount(failed.total);
        // Stuck: running > 10 min
        const now = Date.now();
        const stuckList = (running.items || []).filter((j: JobInfo) =>
          j.started_at && (now - new Date(j.started_at).getTime()) > 600_000
        );
        setStuckJobs(stuckList);
        setRecentFailed(recentF.items);
        setAllFailed(allF.items);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "加载失败");
      }
      setLoading(false);
    })();
  }, []);

  // Generate alerts
  const alerts: Alert[] = [];
  if (stuckJobs.length >= THRESHOLDS.STUCK_CRITICAL) {
    alerts.push({ level: "critical", message: `${stuckJobs.length} 个任务运行超过 10 分钟，可能已卡住` });
  } else if (stuckJobs.length >= THRESHOLDS.STUCK_WARN) {
    alerts.push({ level: "warning", message: `${stuckJobs.length} 个任务运行超过 10 分钟` });
  }
  if (queuedCount >= THRESHOLDS.QUEUE_CRITICAL) {
    alerts.push({ level: "critical", message: `队列积压 ${queuedCount} 个任务` });
  } else if (queuedCount >= THRESHOLDS.QUEUE_WARN) {
    alerts.push({ level: "warning", message: `队列积压 ${queuedCount} 个任务` });
  }
  if (failedCount >= THRESHOLDS.FAILED_CRITICAL) {
    alerts.push({ level: "critical", message: `累计 ${failedCount} 个失败任务，需立即处理` });
  } else if (failedCount >= THRESHOLDS.FAILED_WARN) {
    alerts.push({ level: "warning", message: `${failedCount} 个失败任务，建议检查` });
  }

  if (loading) {
    return <div className="min-h-screen bg-gray-50 dark:bg-gray-950"><NavHeader /><main className="mx-auto max-w-4xl px-4 py-8"><p className="text-gray-500">加载中...</p></main></div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <NavHeader />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">系统状态</h1>
        <p className="mb-6 text-sm text-gray-500">
          {health?.status === "ok" ? "所有服务运行正常" : "部分服务异常"}
        </p>

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="mb-6 space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className={`rounded-lg border px-4 py-3 text-sm font-medium ${
                a.level === "critical"
                  ? "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
                  : "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400"
              }`}>
                {a.level === "critical" ? "🔴" : "🟡"} {a.message}
              </div>
            ))}
          </div>
        )}

        {error && <p className="mb-4 text-red-600">{error}</p>}

        {/* Core health */}
        {health && (
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="服务状态" value={health.status === "ok" ? "正常" : "异常"} ok={health.status === "ok"} />
            <StatCard label="数据库" value={health.database === "ok" ? "正常" : "异常"} ok={health.database === "ok"} />
            <StatCard label="生产态覆盖率" value={`${health.feature_tiers.production_pct}%`} ok={health.feature_tiers.production_pct > 70} />
          </div>
        )}

        {/* Operational metrics */}
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className={`rounded-xl border p-4 ${thresholdBg(queuedCount, THRESHOLDS.QUEUE_WARN, THRESHOLDS.QUEUE_CRITICAL)}`}>
            <p className="text-xs text-gray-500">队列积压</p>
            <p className={`mt-1 text-2xl font-bold ${thresholdColor(queuedCount, THRESHOLDS.QUEUE_WARN, THRESHOLDS.QUEUE_CRITICAL)}`}>
              {queuedCount}
            </p>
            <p className="text-xs text-gray-400">
              {queuedCount >= THRESHOLDS.QUEUE_CRITICAL ? "严重积压" : queuedCount >= THRESHOLDS.QUEUE_WARN ? "需关注" : "正常"}
            </p>
          </div>
          <div className={`rounded-xl border p-4 ${runningCount > 0 ? "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20" : "border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"}`}>
            <p className="text-xs text-gray-500">执行中 Worker</p>
            <p className="mt-1 text-2xl font-bold text-blue-600">{runningCount}</p>
            <p className="text-xs text-gray-400">活跃任务数</p>
          </div>
          <div className={`rounded-xl border p-4 ${thresholdBg(failedCount, THRESHOLDS.FAILED_WARN, THRESHOLDS.FAILED_CRITICAL)}`}>
            <p className="text-xs text-gray-500">累计失败</p>
            <p className={`mt-1 text-2xl font-bold ${thresholdColor(failedCount, THRESHOLDS.FAILED_WARN, THRESHOLDS.FAILED_CRITICAL)}`}>
              {failedCount}
            </p>
            <p className="text-xs text-gray-400">
              {failedCount >= THRESHOLDS.FAILED_CRITICAL ? "需要立即处理" : failedCount >= THRESHOLDS.FAILED_WARN ? "建议检查" : "正常"}
            </p>
          </div>
          <div className={`rounded-xl border p-4 ${thresholdBg(stuckJobs.length, THRESHOLDS.STUCK_WARN, THRESHOLDS.STUCK_CRITICAL)}`}>
            <p className="text-xs text-gray-500">卡住任务</p>
            <p className={`mt-1 text-2xl font-bold ${thresholdColor(stuckJobs.length, THRESHOLDS.STUCK_WARN, THRESHOLDS.STUCK_CRITICAL)}`}>
              {stuckJobs.length}
            </p>
            <p className="text-xs text-gray-400">
              {stuckJobs.length >= THRESHOLDS.STUCK_CRITICAL ? "严重" : stuckJobs.length > 0 ? "需关注" : "正常"}
            </p>
          </div>
        </div>

        {/* Feature tiers */}
        {health && (
          <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">功能分级分布</h2>
            <p className="mb-3 text-sm text-gray-500">总端点: {health.feature_tiers.total_endpoints}</p>
            <div className="space-y-2">
              {Object.entries(health.feature_tiers.by_tier).map(([tier, count]) => {
                const labels: Record<string, string> = { production: "生产态", experimental: "实验态", demo: "演示态", stub: "占位" };
                const colors: Record<string, string> = { production: "bg-green-500", experimental: "bg-yellow-500", demo: "bg-orange-500", stub: "bg-red-500" };
                const pct = health.feature_tiers.total_endpoints > 0 ? (count / health.feature_tiers.total_endpoints) * 100 : 0;
                return (
                  <div key={tier} className="flex items-center gap-3">
                    <span className="w-20 text-sm text-gray-600 dark:text-gray-400">{labels[tier] || tier}</span>
                    <div className="flex-1 rounded-full bg-gray-200 dark:bg-gray-700 h-2.5">
                      <div className={`h-2.5 rounded-full ${colors[tier] || "bg-gray-400"}`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-sm text-gray-500 w-8 text-right">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Stuck jobs */}
        {stuckJobs.length > 0 && (
          <div className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-6 dark:border-amber-800 dark:bg-amber-900/20">
            <h2 className="mb-3 text-lg font-semibold text-amber-900 dark:text-amber-200">
              ⚠ 卡住任务 ({stuckJobs.length})
            </h2>
            <div className="space-y-2">
              {stuckJobs.map((j) => (
                <div key={j.id} className="flex items-center justify-between text-sm text-amber-800 dark:text-amber-300">
                  <span className="font-mono text-xs">{j.id.slice(0, 12)}...</span>
                  <span>{j.job_type}</span>
                  <span>{j.started_at ? `${Math.round((Date.now() - new Date(j.started_at).getTime()) / 60000)} 分钟` : "-"}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent failed */}
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">最近失败任务</h2>
          {recentFailed.length === 0 ? (
            <p className="text-sm text-gray-500">暂无失败任务</p>
          ) : (
            <div className="space-y-2">
              {recentFailed.map((j) => (
                <div key={j.id} className="flex items-center justify-between border-b border-gray-100 py-2 text-sm dark:border-gray-800">
                  <div>
                    <span className="font-medium text-gray-900 dark:text-white">{j.job_type}</span>
                    <span className="ml-2 text-red-600">{j.error_message?.slice(0, 60) || "-"}</span>
                  </div>
                  <span className="text-gray-500">{j.created_at ? new Date(j.created_at).toLocaleString("zh-CN") : "-"}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* All failed error breakdown */}
        {allFailed.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">失败原因分析</h2>
            <div className="space-y-2">
              {(() => {
                const byErr: Record<string, number> = {};
                allFailed.forEach((j) => {
                  const key = j.error_code || j.failure_type || "未知";
                  byErr[key] = (byErr[key] || 0) + 1;
                });
                return Object.entries(byErr).sort(([, a], [, b]) => b - a).slice(0, 5).map(([key, count]) => (
                  <div key={key} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-xs text-gray-600 dark:text-gray-400">{key}</span>
                    <span className="font-medium text-gray-900 dark:text-white">{count} 次</span>
                  </div>
                ));
              })()}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${ok ? "text-green-600" : "text-red-600"}`}>{value}</p>
    </div>
  );
}
