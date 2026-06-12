"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { useProjectStore } from "@/stores/projectStore";
import { retrospectiveApi } from "@/lib/api";

export default function RetrospectivePanel() {
  const { projects } = useProjectStore();
  const [title, setTitle] = useState("");
  const [whatWentWell, setWhatWentWell] = useState("");
  const [whatWentWrong, setWhatWentWrong] = useState("");
  const [surprises, setSurprises] = useState("");
  const [plannedDays, setPlannedDays] = useState<number | null>(null);
  const [actualDays, setActualDays] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const handleSubmit = async () => {
    if (!title.trim()) {
      toast.error("请输入复盘标题");
      return;
    }
    if (projects.length === 0) {
      toast.error("请先创建一个项目");
      return;
    }

    setLoading(true);
    try {
      const created = await retrospectiveApi.create({
        project_id: projects[0].id,
        title,
        lessons: [
          { id: "went-well", category: "well", lesson: whatWentWell, action_item: "" },
          { id: "went-wrong", category: "wrong", lesson: whatWentWrong, action_item: "" },
          { id: "surprises", category: "surprise", lesson: surprises, action_item: "" },
        ],
      });

      toast.success("复盘记录已创建");
      // Auto-run AI analysis
      const aiData = await retrospectiveApi.aiAnalyze(created.id);
      setAiResult((aiData.data as Record<string, string>)?.summary || "分析完成");

      setTitle("");
      setWhatWentWell("");
      setWhatWentWrong("");
      setSurprises("");
      setPlannedDays(null);
      setActualDays(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "保存失败";
      toast.error(`保存失败：${msg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          项目复盘
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-sm text-sky-600 hover:text-sky-700 dark:text-sky-400"
        >
          {showForm ? "收起" : "新建复盘"}
        </button>
      </div>

      {!showForm && aiResult && (
        <div>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <div className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">
              {aiResult}
            </div>
          </div>
          <Link
            href="/assets"
            className="mt-3 inline-block text-sm text-sky-600 hover:text-sky-700 dark:text-sky-400"
          >
            沉淀经验到资产中心 →
          </Link>
        </div>
      )}

      {!showForm && !aiResult && (
        <p className="text-sm text-slate-400 text-center py-8">
          项目结束后在此进行复盘分析，AI 将自动提取经验教训
        </p>
      )}

      {showForm && (
        <div className="space-y-4">
          <input
            type="text"
            placeholder="复盘标题（如：XX医院HIS系统一期上线复盘）"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          />

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-emerald-700 dark:text-emerald-400 mb-1">
                做得好的
              </label>
              <textarea
                placeholder="哪些做法值得保留和推广"
                value={whatWentWell}
                onChange={(e) => setWhatWentWell(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-red-700 dark:text-red-400 mb-1">
                需改进的
              </label>
              <textarea
                placeholder="哪些地方出了问题"
                value={whatWentWrong}
                onChange={(e) => setWhatWentWrong(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-amber-700 dark:text-amber-400 mb-1">
                意料之外
              </label>
              <textarea
                placeholder="计划外的情况"
                value={surprises}
                onChange={(e) => setSurprises(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                计划人天
              </label>
              <input
                type="number"
                placeholder="如 120"
                value={plannedDays ?? ""}
                onChange={(e) => setPlannedDays(e.target.value ? Number(e.target.value) : null)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                实际人天
              </label>
              <input
                type="number"
                placeholder="如 145"
                value={actualDays ?? ""}
                onChange={(e) => setActualDays(e.target.value ? Number(e.target.value) : null)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              />
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {loading ? "AI 分析中..." : "保存并 AI 分析"}
          </button>
        </div>
      )}
    </div>
  );
}
