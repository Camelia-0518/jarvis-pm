"use client";

import { useState } from "react";
import ReviewPanel from "./ReviewPanel";
import AnnotationPanel from "./AnnotationPanel";
import RevisionTaskPanel from "./RevisionTaskPanel";
import ExportPanel from "./ExportPanel";
import VersionPanel from "./VersionPanel";
import QualityScorePanel from "./QualityScorePanel";
import { jobsApi, JobInfo } from "@/lib/api";

type TabId = "review" | "annotations" | "tasks" | "versions" | "export" | "jobs";

interface Props {
  prdId: string;
  projectId: string;
  markdown: string;
  versions: Array<{ id: string; version_number: number; title: string; created_at: string }>;
  annotations: Array<{ id: string; content: string; annotation_type: string; status: string; chapter_num: string | null; chapter_title: string | null }>;
  onRefreshAnnotations: () => void;
  onRefreshTasks: () => void;
}

export default function WorkspaceTabs({ prdId, projectId, markdown, versions, annotations, onRefreshAnnotations, onRefreshTasks }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("review");
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [jobsLoaded, setJobsLoaded] = useState(false);

  const loadJobs = async () => {
    if (jobsLoaded) return;
    try {
      const res = await jobsApi.list({ prd_id: prdId, limit: 20 });
      setJobs(res.items);
    } catch { /* ignore */ }
    setJobsLoaded(true);
  };

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: "review", label: "评审", icon: "&#9745;" },
    { id: "annotations", label: "批注", icon: "&#9998;" },
    { id: "tasks", label: "修订任务", icon: "&#128736;" },
    { id: "versions", label: "版本", icon: "&#128196;" },
    { id: "export", label: "导出", icon: "&#128229;" },
    { id: "jobs", label: "任务", icon: "&#9881;" },
  ];

  return (
    <div className="flex h-full flex-col border-l border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      {/* Tab bar */}
      <div className="flex shrink-0 overflow-x-auto border-b border-gray-200 px-2 dark:border-gray-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => { setActiveTab(t.id); if (t.id === "jobs") loadJobs(); }}
            className={`shrink-0 border-b-2 px-3 py-2.5 text-xs font-medium transition ${
              activeTab === t.id
                ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            }`}
          >
            <span dangerouslySetInnerHTML={{ __html: t.icon }} className="mr-1" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === "review" && (
          <div className="space-y-6">
            {/* TODO: ReviewPanel expects { items, state, onToggle, … } — needs data piped from parent */}
            <ReviewPanel {...({ prdId, projectId, markdown } as any)} />
            <div className="border-t border-gray-200 pt-4 dark:border-gray-700">
              <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">质量评分</h4>
              <QualityScorePanel prdId={prdId} content={markdown} />
            </div>
          </div>
        )}
        {activeTab === "annotations" && (
          /* TODO: AnnotationPanel expects { annotations: Annotation[], stats, filter, … } */
          <AnnotationPanel {...({ prdId, annotations, onRefresh: onRefreshAnnotations } as any)} />
        )}
        {activeTab === "tasks" && (
          /* TODO: RevisionTaskPanel expects { tasks, stats, filter, … } */
          <RevisionTaskPanel {...({ prdId, onRefresh: onRefreshTasks } as any)} />
        )}
        {activeTab === "versions" && (
          <VersionPanel prdId={prdId} versions={versions} onRestore={async () => {}} />
        )}
        {activeTab === "export" && (
          /* TODO: ExportPanel expects { onExport, onClose } */
          <ExportPanel {...({ prdId, title: markdown ? "PRD" : "", markdown } as any)} />
        )}
        {activeTab === "jobs" && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">关联任务</h3>
            {jobs.length === 0 ? (
              <p className="text-xs text-gray-500">暂无关联任务</p>
            ) : (
              jobs.map((j) => {
                const statusColors: Record<string, string> = {
                  queued: "text-yellow-600", running: "text-blue-600", succeeded: "text-green-600", failed: "text-red-600",
                };
                return (
                  <div key={j.id} className="rounded-lg border border-gray-200 p-2 text-xs dark:border-gray-700">
                    <div className="flex items-center justify-between">
                      <span className={`font-medium ${statusColors[j.status || ""] || ""}`}>{j.status}</span>
                      <span className="text-gray-500">{j.duration_ms != null ? `${(j.duration_ms / 1000).toFixed(1)}s` : "-"}</span>
                    </div>
                    {j.error_message && <p className="mt-1 text-red-500 truncate">{j.error_message.slice(0, 80)}</p>}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
