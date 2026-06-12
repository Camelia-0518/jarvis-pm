"use client";

import Link from "next/link";

interface SummaryData {
  planId?: string;
  projectId?: string;
  planStatus?: string;
  highRiskCount: number;
  totalRisks: number;
  overduePhases: number;
  taskCompletionRate: number;
  atRiskPlans: number;
  failedJobsCount?: number;
}

interface Props {
  data: SummaryData;
  variant?: "list" | "detail";
}

export default function DeliverySummaryCard({ data, variant = "list" }: Props) {
  const {
    planId,
    projectId,
    planStatus,
    highRiskCount,
    totalRisks,
    overduePhases,
    taskCompletionRate,
    atRiskPlans,
    failedJobsCount = 0,
  } = data;

  const hasBlockers = highRiskCount > 0 || overduePhases > 0 || failedJobsCount > 0;
  const hasRisks = totalRisks > 0;
  const isStable = !hasBlockers && !hasRisks;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3 mb-6">
      {/* Blockage */}
      <div className={`rounded-xl border p-4 ${hasBlockers ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20" : "border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm">{hasBlockers ? "🔴" : "🟢"}</span>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">当前阻塞</h3>
        </div>
        {hasBlockers ? (
          <div className="space-y-1 text-xs">
            {highRiskCount > 0 && (
              <p className="text-red-700 dark:text-red-400">{highRiskCount} 个高/极高风险</p>
            )}
            {overduePhases > 0 && (
              <p className="text-red-700 dark:text-red-400">{overduePhases} 个里程碑逾期</p>
            )}
            {failedJobsCount > 0 && (
              <Link href={`/jobs?status=failed${projectId ? `&project_id=${projectId}` : ""}`} className="block text-red-600 hover:underline dark:text-red-400">
                {failedJobsCount} 个失败任务 →
              </Link>
            )}
          </div>
        ) : (
          <p className="text-xs text-green-600 dark:text-green-400">无阻塞项</p>
        )}
      </div>

      {/* Risk */}
      <div className={`rounded-xl border p-4 ${hasRisks ? "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20" : "border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"}`}>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm">{hasRisks ? "🟡" : "🟢"}</span>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">当前风险</h3>
        </div>
        {hasRisks ? (
          <div className="space-y-1 text-xs">
            <p className="text-gray-700 dark:text-gray-300">
              共 {totalRisks} 个风险，其中 {highRiskCount} 个高危
            </p>
            <p className="text-gray-600 dark:text-gray-400">
              任务完成率 {Math.round(taskCompletionRate * 100)}%
            </p>
            {variant === "list" && atRiskPlans > 0 && (
              <p className="text-amber-700 dark:text-amber-400">{atRiskPlans} 个计划有风险</p>
            )}
            {variant === "detail" && (
              <p className="text-amber-700 dark:text-amber-400">
                高风险占比 {totalRisks > 0 ? Math.round((highRiskCount / totalRisks) * 100) : 0}%
              </p>
            )}
          </div>
        ) : (
          <p className="text-xs text-green-600 dark:text-green-400">无风险项</p>
        )}
      </div>

      {/* Next action */}
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm">→</span>
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-200">下一建议动作</h3>
        </div>
        <div className="space-y-1 text-xs">
          {hasBlockers && (
            <p className="text-blue-700 dark:text-blue-400">
              优先处理阻塞项，降低交付风险
            </p>
          )}
          {hasRisks && planId && (
            <>
              <Link href={`/delivery/${planId}?tab=risks`} className="block text-blue-600 hover:underline dark:text-blue-400">
                查看风险矩阵 →
              </Link>
              <Link href={`/delivery/${planId}?tab=stakeholders`} className="block text-blue-600 hover:underline dark:text-blue-400">
                检查干系人计划 →
              </Link>
            </>
          )}
          {isStable && planStatus && planStatus !== "completed" && (
            <p className="text-blue-700 dark:text-blue-400">
              计划进展顺利，继续保持
            </p>
          )}
          {planStatus === "completed" && (
            <p className="text-emerald-700 dark:text-emerald-400">
              计划已完成，可以创建复盘记录
            </p>
          )}
          {!planId && (
            <>
              {atRiskPlans > 0 ? (
                <p className="text-blue-700 dark:text-blue-400">
                  优先处理 {atRiskPlans} 个有风险的计划
                </p>
              ) : (
                <Link href="/delivery" className="block text-blue-600 hover:underline dark:text-blue-400">
                  查看全部交付计划 →
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
