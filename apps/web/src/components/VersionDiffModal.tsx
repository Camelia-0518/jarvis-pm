"use client";

import { useMemo } from "react";

interface Props {
  isOpen: boolean;
  oldVersion: string;
  newVersion: string;
  oldContent: string;
  newContent: string;
  onClose: () => void;
}

function diffLines(oldText: string, newText: string): Array<{ type: "same" | "add" | "remove"; text: string }> {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const result: Array<{ type: "same" | "add" | "remove"; text: string }> = [];
  let i = 0,
    j = 0;

  while (i < oldLines.length || j < newLines.length) {
    if (i >= oldLines.length) {
      result.push({ type: "add", text: newLines[j] });
      j++;
    } else if (j >= newLines.length) {
      result.push({ type: "remove", text: oldLines[i] });
      i++;
    } else if (oldLines[i] === newLines[j]) {
      result.push({ type: "same", text: oldLines[i] });
      i++;
      j++;
    } else {
      const oldInNew = newLines.indexOf(oldLines[i], j);
      const newInOld = oldLines.indexOf(newLines[j], i);

      if (oldInNew !== -1 && (newInOld === -1 || oldInNew - j <= newInOld - i)) {
        for (let k = j; k < oldInNew; k++) {
          result.push({ type: "add", text: newLines[k] });
        }
        j = oldInNew;
      } else if (newInOld !== -1) {
        for (let k = i; k < newInOld; k++) {
          result.push({ type: "remove", text: oldLines[k] });
        }
        i = newInOld;
      } else {
        result.push({ type: "remove", text: oldLines[i] });
        result.push({ type: "add", text: newLines[j] });
        i++;
        j++;
      }
    }
  }
  return result;
}

export default function VersionDiffModal({
  isOpen,
  oldVersion,
  newVersion,
  oldContent,
  newContent,
  onClose,
}: Props) {
  const diff = useMemo(() => diffLines(oldContent, newContent), [oldContent, newContent]);

  const stats = useMemo(() => {
    const added = diff.filter((d) => d.type === "add").length;
    const removed = diff.filter((d) => d.type === "remove").length;
    const same = diff.filter((d) => d.type === "same").length;
    return { added, removed, same };
  }, [diff]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="flex h-[85vh] w-full max-w-4xl flex-col rounded-xl bg-white shadow-2xl dark:bg-slate-900">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-3 dark:border-slate-700">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">版本对比</h3>
            <div className="mt-0.5 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
              <span className="text-rose-600 dark:text-rose-400">{oldVersion}</span>
              <span>→</span>
              <span className="text-emerald-600 dark:text-emerald-400">{newVersion}</span>
              <span className="mx-1">·</span>
              <span className="text-emerald-600 dark:text-emerald-400">+{stats.added}</span>
              <span className="text-rose-600 dark:text-rose-400">−{stats.removed}</span>
              <span>≈{stats.same}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {/* Legend */}
        <div className="flex gap-4 border-b px-4 py-2 text-xs dark:border-slate-700">
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 rounded bg-emerald-50 dark:bg-emerald-900/20"></div>
            <span className="text-emerald-700 dark:text-emerald-400">新增</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 rounded bg-rose-50 dark:bg-rose-900/20"></div>
            <span className="text-rose-700 dark:text-rose-400">删除</span>
          </div>
        </div>

        {/* Diff body */}
        <div className="flex-1 overflow-auto px-4 py-2">
          <div className="space-y-0.5 text-xs font-mono">
            {diff.map((line, idx) => (
              <div
                key={idx}
                className={`flex rounded-sm px-2 py-0.5 ${
                  line.type === "add"
                    ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-900/10 dark:text-emerald-300"
                    : line.type === "remove"
                      ? "bg-rose-50 text-rose-900 dark:bg-rose-900/10 dark:text-rose-300"
                      : "text-slate-700 dark:text-slate-300"
                }`}
              >
                <span className="mr-2 w-4 shrink-0 select-none text-slate-300 dark:text-slate-600">
                  {line.type === "add" ? "+" : line.type === "remove" ? "−" : " "}
                </span>
                <span className="break-all">{line.text || " "}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
