"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { projectApi, type ProjectHealthResponse, type ProjectHealthItem } from "@/lib/api";
import { devError } from "@/utils/logger";

const RISK_CONFIG = {
  on_track: { label: "正常", color: "bg-emerald-500", bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700" },
  at_risk: { label: "关注", color: "bg-amber-500", bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700" },
  critical: { label: "风险", color: "bg-rose-500", bg: "bg-rose-50", border: "border-rose-200", text: "text-rose-700" },
};

const SEVERITY_ICON: Record<string, string> = {
  high: "🔴",
  medium: "🟡",
  critical: "🚨",
  low: "🟢",
};

export default function ProjectHealthPanel() {
  const [health, setHealth] = useState<ProjectHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);

  useEffect(() => {
    projectApi.health()
      .then(setHealth)
      .catch((err: unknown) => { devError("Failed to load project health", err); setHealth(null); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">项目健康监控</h2>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-slate-100 dark:bg-slate-700" />
          ))}
        </div>
      </div>
    );
  }

  if (!health || health.projects.length === 0) return null;

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          项目健康监控
        </h2>
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-600 dark:text-slate-400">正常 {health.summary.on_track}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            <span className="text-slate-600 dark:text-slate-400">关注 {health.summary.at_risk}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
            <span className="text-slate-600 dark:text-slate-400">风险 {health.summary.critical}</span>
          </span>
        </div>
      </div>

      {/* Summary bar */}
      <div className="mb-6 rounded-lg bg-slate-50 p-4 dark:bg-slate-700/50">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-600 dark:text-slate-400">
            平均健康度
          </span>
          <span className="text-2xl font-bold text-sky-600">
            {health.summary.average_health_score}
            <span className="text-sm font-normal text-slate-400">/100</span>
          </span>
        </div>
        <div className="mt-2 h-2 w-full rounded-full bg-slate-200 dark:bg-slate-600">
          <div
            className="h-2 rounded-full bg-sky-500 transition-all"
            style={{ width: `${health.summary.average_health_score}%` }}
          />
        </div>
      </div>

      {/* Project list */}
      <div className="space-y-3">
        {health.projects.map((project) => (
          <ProjectHealthCard
            key={project.project_id}
            project={project}
            expanded={expandedProject === project.project_id}
            onToggle={() =>
              setExpandedProject(
                expandedProject === project.project_id ? null : project.project_id
              )
            }
          />
        ))}
      </div>
    </div>
  );
}

function ProjectHealthCard({
  project,
  expanded,
  onToggle,
}: {
  project: ProjectHealthItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const cfg = RISK_CONFIG[project.risk_level];

  return (
    <div className={`rounded-lg border ${cfg.border} ${cfg.bg} dark:bg-opacity-10`}>
      <div className="flex items-center gap-3 p-4">
        <div className={`h-3 w-3 rounded-full ${cfg.color} flex-shrink-0`} />
        <Link
          href={`/workspace?id=${project.project_id}`}
          className="flex-1 min-w-0"
        >
          <h3 className="font-medium text-slate-900 dark:text-white truncate">
            {project.project_name}
          </h3>
          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            <span>📄 {project.metrics.total_prds} PRD</span>
            {project.metrics.has_delivery_plan && (
              <span>📋 {project.metrics.delivery_status || "计划中"}</span>
            )}
            {project.metrics.days_since_update != null && (
              <span>{project.metrics.days_since_update}天前更新</span>
            )}
          </div>
        </Link>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-xs font-medium ${cfg.text}`}>{cfg.label}</span>
          <div className="text-right">
            <span className="text-sm font-bold text-slate-700 dark:text-slate-300">
              {project.health_score}
            </span>
          </div>
          {project.bottlenecks.length > 0 && (
            <button
              onClick={onToggle}
              className="ml-2 text-xs text-sky-600 hover:text-sky-700 dark:text-sky-400"
            >
              {expanded ? "收起" : "详情"}
            </button>
          )}
        </div>
      </div>

      {/* Expanded bottlenecks */}
      {expanded && project.bottlenecks.length > 0 && (
        <div className="border-t border-slate-200 dark:border-slate-700 px-4 py-3 space-y-2">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            AI 风险识别
          </p>
          {project.bottlenecks.map((b, i) => (
            <div
              key={i}
              className="flex items-start gap-2 text-sm"
            >
              <span>{SEVERITY_ICON[b.severity] || "⚪"}</span>
              <span className="text-slate-700 dark:text-slate-300">{b.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
