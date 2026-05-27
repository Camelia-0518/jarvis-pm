"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import NavHeader from "@/components/global/NavHeader";
import { useParams, useSearchParams } from "next/navigation";
import { prdApi } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface DiffLine {
  type: "same" | "add" | "remove";
  text: string;
}

function diffLines(oldText: string, newText: string): DiffLine[] {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const result: DiffLine[] = [];
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

export default function DiffPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const prdId = params.id as string;
  const versionId = searchParams.get("versionId");
  const versionNum = searchParams.get("versionNum");

  const [currentMarkdown, setCurrentMarkdown] = useState("");
  const [versionMarkdown, setVersionMarkdown] = useState("");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [viewMode, setViewMode] = useState<"diff" | "side">("diff");

  useEffect(() => {
    async function load() {
      if (!prdId || !versionId) {
        setError("缺少必要参数");
        setLoading(false);
        return;
      }
      try {
        const [prd, version] = await Promise.all([
          prdApi.get(prdId),
          prdApi.getVersion(prdId, versionId),
        ]);
        setTitle(prd.title || "未命名 PRD");
        setCurrentMarkdown(prd.markdown || "");
        setVersionMarkdown(version.markdown || "");
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "加载失败");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [prdId, versionId]);

  const diff = useMemo(
    () => diffLines(versionMarkdown, currentMarkdown),
    [versionMarkdown, currentMarkdown]
  );

  const stats = useMemo(() => {
    const added = diff.filter((d) => d.type === "add").length;
    const removed = diff.filter((d) => d.type === "remove").length;
    const same = diff.filter((d) => d.type === "same").length;
    return { added, removed, same };
  }, [diff]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-sm text-slate-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 dark:bg-slate-900">
        <div className="text-sm text-rose-500">{error}</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">版本 {versionNum}</span>
            <span className="text-slate-400">→</span>
            <span className="font-medium text-slate-700 dark:text-slate-300">当前</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-emerald-600 dark:text-emerald-400">+{stats.added}</span>
            <span className="text-rose-600 dark:text-rose-400">−{stats.removed}</span>
            <span className="text-slate-400">≈{stats.same}</span>
          </div>
          <div className="flex rounded-md border border-slate-200 bg-white dark:border-slate-600 dark:bg-slate-800">
            {[
              { key: "diff" as const, label: "Diff" },
              { key: "side" as const, label: "并排" },
            ].map((m) => (
              <button
                key={m.key}
                onClick={() => setViewMode(m.key)}
                className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                  viewMode === m.key
                    ? "bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </NavHeader>

      {/* Legend */}
      <div className="flex gap-4 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-700 dark:bg-slate-950">
        <div className="mx-auto flex w-full max-w-7xl gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 rounded bg-emerald-50 dark:bg-emerald-900/20" />
            <span className="text-emerald-700 dark:text-emerald-400">新增</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-3 w-3 rounded bg-rose-50 dark:bg-rose-900/20" />
            <span className="text-rose-700 dark:text-rose-400">删除</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-4 py-4">
        <div className="mx-auto max-w-7xl">
          {viewMode === "diff" ? (
            <div className="space-y-0.5 rounded-lg border border-slate-200 bg-white p-4 font-mono text-xs dark:border-slate-700 dark:bg-slate-950">
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
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950">
                <div className="mb-2 text-xs font-medium text-slate-500">
                  版本 {versionNum}
                </div>
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {versionMarkdown || "*无内容*"}
                  </ReactMarkdown>
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950">
                <div className="mb-2 text-xs font-medium text-slate-500">当前版本</div>
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {currentMarkdown || "*无内容*"}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
