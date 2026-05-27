"use client";

import { useState } from "react";
import { evaluationApi, type PRDQualityResult } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  prdId: string;
  content: string;
  onRegenerate?: () => void;
}

const GRADE_COLORS: Record<string, string> = {
  A: "text-emerald-600 dark:text-emerald-400",
  B: "text-sky-600 dark:text-sky-400",
  C: "text-amber-600 dark:text-amber-400",
  D: "text-orange-600 dark:text-orange-400",
  F: "text-rose-600 dark:text-rose-400",
};

const GRADE_BG: Record<string, string> = {
  A: "bg-emerald-50 dark:bg-emerald-900/20",
  B: "bg-sky-50 dark:bg-sky-900/20",
  C: "bg-amber-50 dark:bg-amber-900/20",
  D: "bg-orange-50 dark:bg-orange-900/20",
  F: "bg-rose-50 dark:bg-rose-900/20",
};

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 80
      ? "bg-emerald-500"
      : score >= 60
        ? "bg-amber-500"
        : "bg-rose-500";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-600 dark:text-slate-400">{label}</span>
        <span className={`font-medium ${score >= 80 ? "text-emerald-600" : score >= 60 ? "text-amber-600" : "text-rose-600"}`}>
          {score}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-700">
        <div
          className={`h-1.5 rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

export default function QualityScorePanel({ prdId, content, onRegenerate }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [result, setResult] = useState<PRDQualityResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleEvaluate = async () => {
    if (!content.trim() || content.trim().length < 50) {
      toast.error("PRD 内容太短，无法评测");
      return;
    }
    setLoading(true);
    try {
      const res = await evaluationApi.evaluatePRD(content, prdId);
      setResult(res);
      toast.success(`评测完成：总分 ${res.overall_score}，等级 ${res.grade}`);
    } catch (err: unknown) {
      toast.error("评测失败：" + (err instanceof Error ? err.message : "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="mb-1 flex w-full items-center justify-between px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <span className="flex items-center gap-1.5">
          AI 质量评分
          {result && (
            <span
              className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${GRADE_BG[result.grade]} ${GRADE_COLORS[result.grade]}`}
            >
              {result.grade} · {result.overall_score}
            </span>
          )}
        </span>
        <span>{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div className="space-y-3 px-2.5">
          <button
            onClick={handleEvaluate}
            disabled={loading}
            className="w-full rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? "评测中..." : "🤖 AI 自动评测 PRD"}
          </button>

          {result && (
            <div className="space-y-3">
              {/* Overall score */}
              <div className={`rounded-lg p-3 text-center ${GRADE_BG[result.grade]}`}>
                <div className={`text-3xl font-bold ${GRADE_COLORS[result.grade]}`}>
                  {result.overall_score}
                </div>
                <div className={`text-sm font-medium ${GRADE_COLORS[result.grade]}`}>
                  等级 {result.grade}
                </div>
              </div>

              {/* Dimension scores */}
              <div className="space-y-2">
                <ScoreBar label="完整性" score={result.completeness_score} />
                <ScoreBar label="准确性" score={result.accuracy_score} />
                <ScoreBar label="可用性" score={result.usability_score} />
                <ScoreBar label="合规性" score={result.compliance_score} />
              </div>

              {/* Low score warning + regenerate */}
              {result.overall_score < 60 && onRegenerate && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-[11px] text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400">
                  <p className="mb-1">⚠️ 评分较低，建议重新生成</p>
                  <button
                    onClick={onRegenerate}
                    className="w-full rounded bg-rose-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-rose-700"
                  >
                    🔄 切换模型重试
                  </button>
                </div>
              )}

              {/* Suggestions */}
              {result.suggestions.length > 0 && (
                <div className="space-y-1">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">改进建议</div>
                  {result.suggestions.map((s, i) => (
                    <div
                      key={i}
                      className="rounded bg-slate-50 px-2 py-1 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                    >
                      {s}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
