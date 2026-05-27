"use client";

import { useState, useEffect } from "react";
import { skillsApi, type SkillExecutionRecord } from "@/lib/api";
import { useProjectStore } from "@/stores/projectStore";

export default function AnalyticsPanel() {
  const { projects } = useProjectStore();
  const [recentSkills, setRecentSkills] = useState<Array<{
    id: string;
    name: string;
    status: string;
    time: string;
  }>>([]);
  const [skillStats, setSkillStats] = useState({ aiCalls: 0 });

  useEffect(() => {
    async function fetchSkillData() {
      try {
        const executions = await skillsApi.getExecutions({ limit: 50 });
        const records = Array.isArray(executions) ? executions : [];

        const mapped = records.slice(0, 5).map((item: SkillExecutionRecord) => ({
          id: item.id || `skill-${Math.random()}`,
          name: item.skillName || item.skillId || "技能执行",
          status: item.status || "completed",
          time: item.completedAt
            ? new Date(item.completedAt).toLocaleString()
            : item.createdAt
            ? new Date(item.createdAt).toLocaleString()
            : "-",
        }));
        setRecentSkills(mapped);
        setSkillStats({ aiCalls: records.length });
      } catch {
        setRecentSkills([]);
      }
    }
    fetchSkillData();
  }, []);

  return (
    <div className="mb-8 rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        📊 项目数据看板
      </h2>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700/50">
          <div className="text-2xl font-bold text-sky-600">{projects.length}</div>
          <div className="text-sm text-slate-600 dark:text-slate-400">总项目数</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700/50">
          <div className="text-2xl font-bold text-emerald-600">
            {projects.filter((p) => p.status === "active").length}
          </div>
          <div className="text-sm text-slate-600 dark:text-slate-400">进行中</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700/50">
          <div className="text-2xl font-bold text-violet-600">
            {projects.reduce((acc, p) => acc + (p.prd_count || 0), 0)}
          </div>
          <div className="text-sm text-slate-600 dark:text-slate-400">PRD 总数</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700/50">
          <div className="text-2xl font-bold text-amber-600">{skillStats.aiCalls}</div>
          <div className="text-sm text-slate-600 dark:text-slate-400">AI 调用次数</div>
        </div>
      </div>

      {projects.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
            行业分布
          </h3>
          <div className="space-y-2">
            {Object.entries(
              projects.reduce((acc, p) => {
                const industry = p.industry || "其他";
                acc[industry] = (acc[industry] || 0) + 1;
                return acc;
              }, {} as Record<string, number>)
            )
              .sort(([, a], [, b]) => b - a)
              .map(([industry, count]) => {
                const total = projects.length;
                const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                const labelMap: Record<string, string> = {
                  medical: "医疗健康",
                  saas: "SaaS",
                  ecommerce: "电商",
                  other: "其他",
                };
                return (
                  <div key={industry} className="flex items-center gap-3">
                    <span className="w-16 text-xs text-slate-500 dark:text-slate-400">
                      {labelMap[industry] || industry}
                    </span>
                    <div className="flex-1 rounded-full bg-slate-100 dark:bg-slate-700">
                      <div
                        className="h-2 rounded-full bg-sky-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-xs text-slate-600 dark:text-slate-400">
                      {count}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {recentSkills.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
            最近 AI 活动
          </h3>
          <div className="space-y-2">
            {recentSkills.slice(0, 5).map((skill) => (
              <div
                key={skill.id}
                className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-700/50"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      skill.status === "completed"
                        ? "bg-emerald-500"
                        : skill.status === "running"
                        ? "bg-sky-500"
                        : "bg-slate-400"
                    }`}
                  />
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {skill.name}
                  </span>
                </div>
                <span className="text-xs text-slate-400">{skill.time}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
