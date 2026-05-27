"use client";

import { useEffect } from "react";

export default function PRDErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("PRDErrorBoundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">📝</div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">
          PRD 加载失败
        </h2>
        <p className="text-slate-600 dark:text-slate-400 mb-6">
          {error.message || "无法加载 PRD 文档，请稍后重试"}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors"
          >
            重新加载
          </button>
          <a
            href="/dashboard"
            className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
          >
            返回仪表盘
          </a>
        </div>
      </div>
    </div>
  );
}
