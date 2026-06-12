"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { useProjectStore } from "@/stores/projectStore";
import { projectApi, skillsApi, jobsApi, type Project, type SkillExecutionRecord, type JobInfo } from "@/lib/api";
import { toast } from "sonner";
import { confirm } from "@/components/ui/ConfirmDialog";
import { SkeletonProjectList } from "@/components/ui/Skeleton";
import NavHeader from "@/components/global/NavHeader";
import SkillPanel from "./SkillPanel";
import AnalyticsPanel from "./AnalyticsPanel";
import ProjectHealthPanel from "./ProjectHealthPanel";
import RetrospectivePanel from "./RetrospectivePanel";
import NewProjectModal from "./NewProjectModal";
import FeedbackModal from "./FeedbackModal";

export default function Dashboard() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { projects = [], fetchProjects, isLoading, error } = useProjectStore();
  const [showSkillPanel, setShowSkillPanel] = useState(false);
  const [showAnalyticsPanel, setShowAnalyticsPanel] = useState(false);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [skillStats, setSkillStats] = useState({
    aiCalls: 0,
    reviewCount: "-",
    reportCount: "-",
  });

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useEffect(() => {
    if (isLoading) return;
    async function fetchSkillData() {
      try {
        const executions = await skillsApi.getExecutions({ limit: 50 });
        const records = Array.isArray(executions) ? executions : [];

        const reviewCount = records.filter((r) =>
          /review|agenda|qa|risks/.test((r.skillId || r.skillName || ""))
        ).length;
        const reportCount = records.filter((r) =>
          /standup|report/.test((r.skillId || r.skillName || ""))
        ).length;

        setSkillStats({
          aiCalls: records.length,
          reviewCount: reviewCount > 0 ? String(reviewCount) : "-",
          reportCount: reportCount > 0 ? String(reportCount) : "-",
        });
      } catch {
        // ignore
      }
    }
    fetchSkillData();
  }, [isLoading]);

  const stats = {
    savedTime: skillStats.aiCalls > 0 ? String(skillStats.aiCalls) : "-",
    prdCount: projects.reduce((acc, p) => acc + (p.prd_count || 0), 0).toString(),
    reviewCount: skillStats.reviewCount,
    reportCount: skillStats.reportCount,
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <button
          onClick={() => setShowFeedbackModal(true)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          <span className="md:hidden">💬</span>
          <span className="hidden md:inline">💬 反馈</span>
        </button>
        <button
          onClick={() => setShowSkillPanel(!showSkillPanel)}
          className="rounded-lg border border-slate-300 bg-white px-3 md:px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          <span className="md:hidden">⚡</span>
          <span className="hidden md:inline">⚡ 技能面板</span>
        </button>
        <button
          onClick={() => setShowNewProjectModal(true)}
          className="rounded-lg bg-sky-600 px-3 md:px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          <span className="md:hidden">+</span>
          <span className="hidden md:inline">+ 新建项目</span>
        </button>
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-sky-100 flex items-center justify-center text-sm font-medium text-sky-700 dark:bg-sky-900/30 dark:text-sky-400">
            {user?.name?.[0] || "U"}
          </div>
        </div>
      </NavHeader>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Welcome */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            欢迎回来，{user?.name || "产品经理"} 👋
          </h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">
            今天想从哪里开始？
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-4 p-4 rounded-lg bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400">
            {error}
          </div>
        )}

        {/* Skill Panel */}
        {showSkillPanel && <SkillPanel />}

        {/* Quick Actions */}
        <div className="mb-8 grid gap-4 sm:grid-cols-4">
          <QuickActionCard icon="🚀" title="新建 PRD" description="从模板或空白开始" href="/workspace" />
          <button
            onClick={() => setShowAnalyticsPanel(!showAnalyticsPanel)}
            className="flex items-center gap-4 rounded-xl bg-white p-4 shadow-sm transition-shadow hover:shadow-md text-left dark:bg-slate-800"
          >
            <span className="text-3xl">📊</span>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white">数据分析</h3>
              <p className="text-sm text-slate-600 dark:text-slate-400">查看项目统计</p>
            </div>
          </button>
        </div>

        {/* Analytics Panel */}
        {showAnalyticsPanel && <AnalyticsPanel />}

        {/* Retrospective Panel */}
        <RetrospectivePanel />

        {/* Recent Activity */}
        <RecentJobs />

        {/* Projects */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              进行中的项目
            </h2>
            <span className="text-sm text-slate-500">共 {projects.length} 个项目</span>
          </div>

          {isLoading ? (
            <SkeletonProjectList count={4} />
          ) : projects.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl shadow-sm dark:bg-slate-800">
              <div className="text-4xl mb-4">📁</div>
              <div className="text-slate-600 dark:text-slate-300">暂无项目</div>
              <div className="text-sm text-slate-400 mt-2">点击&ldquo;+ 新建项目&rdquo;开始创建</div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onDelete={async (id) => {
                    const deletedProject = projects.find((p) => p.id === id);
                    try {
                      await projectApi.delete(id);
                      fetchProjects();
                      toast.success("项目已删除", {
                        action: {
                          label: "撤销",
                          onClick: async () => {
                            try {
                              await projectApi.update(id, { status: "active" });
                              fetchProjects();
                              toast.success("已恢复项目");
                            } catch {
                              toast.error("恢复失败");
                            }
                          },
                        },
                      });
                    } catch {
                      toast.error("删除失败，请重试");
                    }
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Project Health Monitoring */}
        <div className="mt-8">
          <ProjectHealthPanel />
        </div>

        {/* Stats */}
        <div className="mt-8 rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            AI 助手使用统计
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <StatCard label="AI 技能调用" value={stats.savedTime} />
            <StatCard label="PRD 生成" value={stats.prdCount} />
            <StatCard label="评审准备" value={stats.reviewCount} />
            <StatCard label="站会报告" value={stats.reportCount} />
          </div>
        </div>
      </main>

      <FeedbackModal isOpen={showFeedbackModal} onClose={() => setShowFeedbackModal(false)} />
      <NewProjectModal isOpen={showNewProjectModal} onClose={() => setShowNewProjectModal(false)} />
    </div>
  );
}

function RecentJobs() {
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  useEffect(() => {
    (async () => {
      try { const res = await jobsApi.list({ limit: 5 }); setJobs(res.items || []); } catch { /* */ }
    })();
  }, []);
  if (!jobs.length) return null;
  const sc: Record<string, string> = { queued: "text-yellow-600", running: "text-blue-600", succeeded: "text-green-600", failed: "text-red-600" };
  return (
    <div className="mb-8 rounded-xl bg-white p-5 shadow-sm dark:bg-slate-800">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">最近动态</h2>
        <Link href="/jobs" className="text-sm text-sky-600 hover:text-sky-700">全部 →</Link>
      </div>
      <div className="space-y-2">
        {jobs.map((j) => (
          <div key={j.id} className="flex items-center justify-between border-b border-gray-100 py-1.5 text-sm dark:border-gray-700">
            <div className="flex items-center gap-2">
              <span className={`text-xs font-medium ${sc[j.status || ""] || ""}`}>{j.status}</span>
              <span className="text-gray-600 dark:text-gray-400">{j.job_type}</span>
            </div>
            <span className="text-xs text-gray-400">{j.created_at ? new Date(j.created_at).toLocaleString("zh-CN") : ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickActionCard({
  icon,
  title,
  description,
  href,
}: {
  icon: string;
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-4 rounded-xl bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-slate-800"
    >
      <span className="text-3xl">{icon}</span>
      <div>
        <h3 className="font-semibold text-slate-900 dark:text-white">{title}</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400">{description}</p>
      </div>
    </Link>
  );
}

function ProjectCard({
  project,
  onDelete,
}: {
  project: Project;
  onDelete?: (id: string) => void;
}) {
  return (
    <div className="relative group rounded-xl bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:bg-slate-800">
      <Link href={`/workspace?id=${project.id}`} className="block">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">{project.name}</h3>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
              {project.description || "暂无描述"}
            </p>
          </div>
          <span
            className={`rounded-full px-2 py-1 text-xs font-medium ${
              project.status === "active"
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                : "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
            }`}
          >
            {project.status === "active" ? "进行中" : "已归档"}
          </span>
        </div>

        <div className="mt-4 flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
          <span>📄 {project.prd_count} 个 PRD</span>
          <span>🏭 {project.industry || "其他"}</span>
        </div>

        <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
          更新于 {new Date(project.updated_at || project.created_at).toLocaleDateString()}
        </p>
      </Link>

      {onDelete && (
        <button
          onClick={async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const confirmed = await confirm({
              title: "删除项目",
              message: `确定要删除项目 "${project.name}" 吗？此操作不可恢复。`,
              type: "danger",
            });
            if (confirmed) {
              onDelete(project.id);
            }
          }}
          className="absolute top-4 right-20 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-rose-600 hover:text-rose-700 px-2 py-1 rounded hover:bg-rose-50 dark:hover:bg-rose-900/20"
          title="删除项目"
        >
          删除
        </button>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold text-sky-600">{value}</p>
      <p className="text-sm text-slate-600 dark:text-slate-400">{label}</p>
    </div>
  );
}
