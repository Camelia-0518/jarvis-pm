"use client";

import { useState } from "react";
import type { ChecklistItem } from "@/lib/api";

interface Props {
  items: ChecklistItem[];
  state: Record<string, { checked: boolean; note: string }>;
  onToggle: (itemId: string, checked: boolean) => void;
  onNoteChange: (itemId: string, note: string) => void;
  loading: boolean;
  saving: boolean;
  result: string | null;
  aiReviewLoading: boolean;
  onAIReview: () => void;
  onSubmit: () => void;
}

export default function ReviewPanel({
  items: rawItems,
  state: rawState,
  onToggle,
  onNoteChange,
  loading,
  saving,
  result,
  aiReviewLoading,
  onAIReview,
  onSubmit,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);

  // Bulletproof: guard against corrupted data from old PRDs / broken localStorage
  const items = Array.isArray(rawItems) ? rawItems : [];
  const state = rawState && typeof rawState === "object" && !Array.isArray(rawState) ? rawState : {};

  const checkedCount = Object.values(state).filter((s) => s?.checked).length;
  const categories = Array.from(new Set(items.map((i) => i?.category || "其他")));

  return (
    <div className="mt-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="mb-1 flex w-full items-center justify-between px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <span className="flex items-center gap-1.5">
          评审检查
          {items.length > 0 && (
            <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
              {checkedCount}/{items.length}
            </span>
          )}
        </span>
        <span>{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div className="space-y-2">
          {loading ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">加载中...</div>
          ) : items.length === 0 ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">暂无检查项</div>
          ) : (
            <div className="space-y-2">
              {categories.map((cat) => (
                <div key={cat}>
                  <div className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    {cat}
                  </div>
                  <div className="space-y-1">
                    {items
                      .filter((i) => i.category === cat)
                      .map((item) => {
                        const itemState = state[item.id] || { checked: false, note: "" };
                        return (
                          <div
                            key={item.id}
                            className="rounded-md px-2.5 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800"
                          >
                            <label className="flex items-start gap-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={itemState.checked}
                                onChange={(e) => onToggle(item.id, e.target.checked)}
                                className="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                              />
                              <div className="flex-1">
                                <span
                                  className={`text-xs ${
                                    itemState.checked
                                      ? "text-slate-400 line-through"
                                      : "text-slate-700 dark:text-slate-300"
                                  }`}
                                >
                                  {item.text}
                                  {item.required && <span className="ml-1 text-rose-500">*</span>}
                                </span>
                                <input
                                  type="text"
                                  value={itemState.note}
                                  onChange={(e) => onNoteChange(item.id, e.target.value)}
                                  placeholder="备注..."
                                  className="mt-1 w-full rounded border-0 bg-transparent px-0 py-0 text-[11px] text-slate-500 placeholder:text-slate-300 focus:ring-0 dark:text-slate-400 dark:placeholder:text-slate-600"
                                />
                              </div>
                            </label>
                          </div>
                        );
                      })}
                  </div>
                </div>
              ))}
              <button
                onClick={onAIReview}
                disabled={aiReviewLoading}
                className="w-full rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-sky-700 disabled:opacity-50"
              >
                {aiReviewLoading ? "AI 评审中..." : "🤖 AI 自动评审"}
              </button>
              <button
                onClick={onSubmit}
                disabled={saving}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors duration-150 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                {saving ? "提交中..." : "提交评审结果"}
              </button>
              {result && (
                <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {result}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
