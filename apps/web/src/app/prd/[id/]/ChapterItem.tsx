"use client";

interface Props {
  title: string;
  status: "done" | "active" | "pending" | "failed";
  onJump?: () => void;
  onGenerate?: () => void;
  onRegenerate?: () => void;
  onRetry?: () => void;
}

const statusClasses = {
  done: "text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 cursor-pointer",
  active: "font-medium text-sky-600 dark:text-sky-400 animate-pulse hover:bg-sky-50 dark:hover:bg-sky-900/20 cursor-pointer",
  pending: "text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer",
  failed: "text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 cursor-pointer",
};

const statusIcon = {
  done: "✓",
  active: "●",
  pending: "○",
  failed: "✗",
};

export default function ChapterItem({ title, status, onJump, onGenerate, onRegenerate, onRetry }: Props) {
  return (
    <div className="flex items-center gap-1 rounded-md px-2.5 py-1.5 text-sm transition-colors duration-150 group">
      <button
        onClick={() => onJump?.()}
        disabled={!onJump}
        className={`flex flex-1 items-center gap-2 min-w-0 text-left ${statusClasses[status]} ${!onJump ? "cursor-default" : ""}`}
        title={
          status === "done"
            ? "点击跳转到该章节"
            : status === "active"
              ? "正在生成中，点击跳转"
              : status === "failed"
                ? "生成失败，点击重试或跳转"
                : "点击跳转到该章节"
        }
      >
        <span className="text-xs">{statusIcon[status]}</span>
        <span className="truncate">{title}</span>
      </button>
      {status === "pending" && onGenerate && (
        <button
          onClick={(e) => { e.stopPropagation(); onGenerate(); }}
          className="ml-1 shrink-0 rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:hover:bg-sky-800/50"
          title="生成该章节"
        >
          生成
        </button>
      )}
      {status === "failed" && onRetry && (
        <button
          onClick={(e) => { e.stopPropagation(); onRetry(); }}
          className="ml-1 shrink-0 rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-medium text-rose-700 opacity-100 transition-opacity hover:bg-rose-200 dark:bg-rose-900/30 dark:text-rose-400 dark:hover:bg-rose-800/50"
          title="重新生成该章节"
        >
          重试
        </button>
      )}
      {status === "done" && onRegenerate && (
        <button
          onClick={(e) => { e.stopPropagation(); onRegenerate(); }}
          className="ml-1 shrink-0 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:hover:bg-emerald-800/50"
          title="重新生成该章节"
        >
          重新生成
        </button>
      )}
    </div>
  );
}
