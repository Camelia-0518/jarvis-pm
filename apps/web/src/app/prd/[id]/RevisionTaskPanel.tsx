"use client";

import { useState } from "react";

interface RevisionTask {
  id: string;
  title: string;
  description: string | null;
  status: string;
  assigned_to: string | null;
  completed_at: string | null;
  completion_note: string | null;
  re_review_status: string | null;
  created_at: string;
}

interface Props {
  tasks: RevisionTask[];
  stats: { todo: number; in_progress: number; done: number; cancelled: number; total: number };
  filter: 'all' | 'todo' | 'in_progress' | 'done' | 'cancelled';
  onFilterChange: (filter: 'all' | 'todo' | 'in_progress' | 'done' | 'cancelled') => void;
  loading: boolean;
  onComplete: (taskId: string, note: string, triggerReReview: boolean) => void;
  onUpdateStatus: (taskId: string, status: string) => void;
  onDelete: (taskId: string) => void;
  onOpen?: () => void;
  open?: boolean;
  onToggle?: () => void;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  todo: { label: '待处理', color: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400' },
  in_progress: { label: '进行中', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
  done: { label: '已完成', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' },
  cancelled: { label: '已取消', color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400' },
};

const FILTER_LABELS: Record<string, string> = {
  all: '全部',
  todo: '待处理',
  in_progress: '进行中',
  done: '已完成',
  cancelled: '已取消',
};

export default function RevisionTaskPanel({
  tasks,
  stats,
  filter,
  onFilterChange,
  loading,
  onComplete,
  onUpdateStatus,
  onDelete,
  onOpen,
  open: controlledOpen,
  onToggle: controlledOnToggle,
}: Props) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [completingTaskId, setCompletingTaskId] = useState<string | null>(null);
  const [completionNote, setCompletionNote] = useState('');
  const [triggerReReview, setTriggerReReview] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;

  const handleToggle = () => {
    if (isControlled && controlledOnToggle) {
      controlledOnToggle();
    } else {
      const next = !internalOpen;
      setInternalOpen(next);
      if (next && onOpen) onOpen();
    }
  };

  const handleStartComplete = (taskId: string) => {
    setCompletingTaskId(taskId);
    setCompletionNote('');
    setTriggerReReview(false);
  };

  const handleSubmitComplete = () => {
    if (!completingTaskId || !completionNote.trim()) return;
    onComplete(completingTaskId, completionNote.trim(), triggerReReview);
    setCompletingTaskId(null);
    setCompletionNote('');
    setTriggerReReview(false);
  };

  return (
    <div className="mt-4">
      <button
        onClick={handleToggle}
        className="mb-1 flex w-full items-center justify-between px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <span className="flex items-center gap-1.5">
          📋 修改任务
          {stats.total > 0 && (
            <span className="rounded-full bg-sky-100 px-1.5 py-0.5 text-[10px] font-bold text-sky-700 dark:bg-sky-900/30 dark:text-sky-400">
              {stats.todo + stats.in_progress}
            </span>
          )}
        </span>
        <span>{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div className="space-y-2">
          {/* Stats */}
          <div className="flex gap-1 px-2.5">
            {(['all', 'todo', 'in_progress', 'done'] as const).map((f) => (
              <button
                key={f}
                onClick={() => onFilterChange(f)}
                className={`rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors ${
                  filter === f
                    ? 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200'
                    : 'text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300'
                }`}
              >
                {FILTER_LABELS[f]} {f === 'all' ? stats.total : stats[f]}
              </button>
            ))}
          </div>

          {/* Task list */}
          {loading ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">加载中...</div>
          ) : tasks.length === 0 ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">暂无修改任务</div>
          ) : (
            tasks
              .filter((t) => filter === 'all' || t.status === filter)
              .map((t) => (
                <div
                  key={t.id}
                  className={`mx-2.5 rounded-lg border p-2 text-xs transition-colors ${
                    t.status === 'todo'
                      ? 'border-sky-200 bg-sky-50/50 dark:border-sky-800 dark:bg-sky-900/10'
                      : t.status === 'in_progress'
                        ? 'border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-900/10'
                        : t.status === 'done'
                          ? 'border-emerald-200 bg-emerald-50/30 dark:border-emerald-800 dark:bg-emerald-900/10'
                          : 'border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50'
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className={`rounded px-1 py-0.5 text-[10px] font-medium ${STATUS_LABELS[t.status]?.color || 'bg-slate-100 text-slate-600'}`}>
                      {STATUS_LABELS[t.status]?.label || t.status}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {new Date(t.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <p className="mb-1 font-medium text-slate-800 dark:text-slate-200">{t.title}</p>
                  {t.description && (
                    <p className="mb-1 text-slate-600 dark:text-slate-400">{t.description}</p>
                  )}

                  {/* 完成信息 */}
                  {t.status === 'done' && t.completion_note && (
                    <div className="mb-1.5 rounded bg-white/80 px-1.5 py-1 text-[10px] text-slate-500 dark:bg-slate-800/80 dark:text-slate-400">
                      <span className="font-medium">修改说明:</span> {t.completion_note}
                    </div>
                  )}
                  {t.re_review_status && (
                    <div className={`mb-1.5 text-[10px] font-medium ${
                      t.re_review_status === 'pass'
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : t.re_review_status === 'pending'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-rose-600 dark:text-rose-400'
                    }`}>
                      再评审: {t.re_review_status === 'pass' ? '通过' : t.re_review_status === 'pending' ? '排队中' : t.re_review_status === 'partial' ? '部分通过' : '未通过'}
                    </div>
                  )}

                  {/* 完成表单 */}
                  {completingTaskId === t.id && (
                    <div className="mb-1.5 space-y-1.5 rounded border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-800">
                      <textarea
                        value={completionNote}
                        onChange={(e) => setCompletionNote(e.target.value)}
                        placeholder="填写修改说明..."
                        className="w-full resize-none rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        rows={2}
                      />
                      <label className="flex items-center gap-1 text-[10px] text-slate-600 dark:text-slate-400">
                        <input
                          type="checkbox"
                          checked={triggerReReview}
                          onChange={(e) => setTriggerReReview(e.target.checked)}
                          className="rounded border-slate-300"
                        />
                        触发再评审
                      </label>
                      <div className="flex gap-1">
                        <button
                          onClick={handleSubmitComplete}
                          disabled={!completionNote.trim()}
                          className="flex-1 rounded bg-emerald-500 px-2 py-1 text-[10px] font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
                        >
                          确认完成
                        </button>
                        <button
                          onClick={() => setCompletingTaskId(null)}
                          className="rounded border border-slate-200 px-2 py-1 text-[10px] text-slate-600 dark:border-slate-600 dark:text-slate-300"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 操作按钮 */}
                  {t.status !== 'done' && t.status !== 'cancelled' && completingTaskId !== t.id && (
                    <div className="flex gap-1">
                      {t.status === 'todo' && (
                        <button
                          onClick={() => onUpdateStatus(t.id, 'in_progress')}
                          className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-700 hover:bg-amber-100 dark:bg-amber-900/20 dark:text-amber-400"
                        >
                          开始修改
                        </button>
                      )}
                      <button
                        onClick={() => handleStartComplete(t.id)}
                        className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400"
                      >
                        完成
                      </button>
                      <button
                        onClick={() => onUpdateStatus(t.id, 'cancelled')}
                        className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-400"
                      >
                        取消
                      </button>
                      <button
                        onClick={() => onDelete(t.id)}
                        className="ml-auto rounded bg-rose-50 px-1.5 py-0.5 text-[10px] text-rose-700 hover:bg-rose-100 dark:bg-rose-900/20 dark:text-rose-400"
                      >
                        删除
                      </button>
                    </div>
                  )}

                  {(t.status === 'done' || t.status === 'cancelled') && (
                    <div className="flex items-center justify-between">
                      <span className={`text-[10px] font-medium ${
                        t.status === 'done'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-slate-500 dark:text-slate-400'
                      }`}>
                        {t.status === 'done' ? '✓ 已完成' : '已取消'}
                      </span>
                      <button
                        onClick={() => onDelete(t.id)}
                        className="rounded bg-rose-50 px-1.5 py-0.5 text-[10px] text-rose-700 hover:bg-rose-100 dark:bg-rose-900/20 dark:text-rose-400"
                      >
                        删除
                      </button>
                    </div>
                  )}
                </div>
              ))
          )}
        </div>
      )}
    </div>
  );
}
