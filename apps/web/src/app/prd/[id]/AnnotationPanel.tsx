"use client";

import { useState } from "react";
import { annotationApi } from "@/lib/api";

interface Annotation {
  id: string;
  content: string;
  annotation_type: 'comment' | 'question' | 'suggestion' | 'issue';
  status: 'open' | 'resolved' | 'dismissed';
  chapter_num: string | null;
  chapter_title: string | null;
  line_index: number | null;
  selected_text: string | null;
  created_at: string;
  revision_task?: {
    id: string;
    title: string;
    status: string;
  } | null;
}

interface Props {
  annotations: Annotation[];
  stats: { open: number; resolved: number; dismissed: number; total: number };
  filter: 'all' | 'open' | 'resolved' | 'dismissed';
  onFilterChange: (filter: 'all' | 'open' | 'resolved' | 'dismissed') => void;
  loading: boolean;
  showForm: boolean;
  onToggleForm: () => void;
  selectedText: string | null;
  annotationType: 'comment' | 'question' | 'suggestion' | 'issue';
  onTypeChange: (type: 'comment' | 'question' | 'suggestion' | 'issue') => void;
  content: string;
  onContentChange: (content: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onResolve: (id: string) => void;
  onDismiss: (id: string) => void;
  onDelete: (id: string) => void;
  onConvertToTask?: (id: string) => void;
  onAutoReview?: () => void;
  autoReviewLoading?: boolean;
  onOpen?: () => void;
  open?: boolean;
  onToggle?: () => void;
  prdId: string;
  onApplyFix?: (fixedContent: string) => void;
}

const TYPE_LABELS: Record<string, string> = {
  comment: '💬',
  question: '❓',
  suggestion: '💡',
  issue: '⚠️',
};

const TYPE_COLORS: Record<string, string> = {
  comment: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  question: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  suggestion: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  issue: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
};

const FILTER_LABELS: Record<string, string> = {
  all: '全部',
  open: '待处理',
  resolved: '已解决',
  dismissed: '已忽略',
};

export default function AnnotationPanel({
  annotations,
  stats,
  filter,
  onFilterChange,
  loading,
  showForm,
  onToggleForm,
  selectedText,
  annotationType,
  onTypeChange,
  content,
  onContentChange,
  onSubmit,
  onCancel,
  onResolve,
  onDismiss,
  onDelete,
  onConvertToTask,
  onAutoReview,
  autoReviewLoading,
  onOpen,
  open: controlledOpen,
  onToggle: controlledOnToggle,
  prdId,
  onApplyFix,
}: Props) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;
  const [fixingId, setFixingId] = useState<string | null>(null);
  const [fixPreview, setFixPreview] = useState<string | null>(null);

  const handleToggle = () => {
    if (isControlled && controlledOnToggle) {
      controlledOnToggle();
    } else {
      const next = !internalOpen;
      setInternalOpen(next);
      if (next && onOpen) onOpen();
    }
  };

  return (
    <div className="mt-6">
      <button
        onClick={handleToggle}
        className="mb-1 flex w-full items-center justify-between px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <span className="flex items-center gap-1.5">
          评审批注
          {stats.total > 0 && (
            <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              {stats.open}
            </span>
          )}
        </span>
        <span>{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div className="space-y-2">
          {/* Stats */}
          <div className="flex gap-1 px-2.5">
            {(['all', 'open', 'resolved', 'dismissed'] as const).map((f) => (
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

          {/* AI Auto Review */}
          {onAutoReview && (
            <button
              onClick={onAutoReview}
              disabled={autoReviewLoading}
              className="mx-2.5 w-[calc(100%-1.25rem)] rounded-md bg-violet-50 px-2 py-1 text-[11px] font-medium text-violet-700 transition-colors hover:bg-violet-100 disabled:opacity-50 dark:bg-violet-900/20 dark:text-violet-400 dark:hover:bg-violet-900/30"
            >
              {autoReviewLoading ? '🤖 评审中...' : '🤖 AI 自动评审'}
            </button>
          )}

          {/* Add button */}
          <button
            onClick={onToggleForm}
            className="mx-2.5 w-[calc(100%-1.25rem)] rounded-md bg-sky-50 px-2 py-1 text-[11px] font-medium text-sky-700 transition-colors hover:bg-sky-100 dark:bg-sky-900/20 dark:text-sky-400 dark:hover:bg-sky-900/30"
          >
            + 添加批注
          </button>

          {/* Annotation form */}
          {showForm && (
            <div className="mx-2.5 rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-800">
              {selectedText && (
                <div className="mb-1.5 rounded bg-slate-50 px-2 py-1 text-[10px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  <span className="font-medium">选中:</span>{' '}
                  {selectedText.length > 40
                    ? selectedText.slice(0, 40) + '...'
                    : selectedText}
                </div>
              )}
              <select
                value={annotationType}
                onChange={(e) => onTypeChange(e.target.value as typeof annotationType)}
                className="mb-1.5 w-full rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
              >
                <option value="comment">💬 评论</option>
                <option value="question">❓ 问题</option>
                <option value="suggestion">💡 建议</option>
                <option value="issue">⚠️ 问题</option>
              </select>
              <textarea
                value={content}
                onChange={(e) => onContentChange(e.target.value)}
                placeholder="输入批注内容..."
                className="mb-1.5 w-full resize-none rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
                rows={2}
              />
              <div className="flex gap-1">
                <button
                  onClick={onSubmit}
                  disabled={!content.trim()}
                  className="flex-1 rounded bg-sky-500 px-2 py-1 text-[11px] font-medium text-white hover:bg-sky-600 disabled:opacity-50"
                >
                  提交
                </button>
                <button
                  onClick={onCancel}
                  className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  取消
                </button>
              </div>
            </div>
          )}

          {/* Annotation list */}
          {loading ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">加载中...</div>
          ) : annotations.length === 0 ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">暂无批注</div>
          ) : (
            annotations
              .filter((a) => filter === 'all' || a.status === filter)
              .map((a) => (
                <div
                  key={a.id}
                  className={`mx-2.5 rounded-lg border p-2 text-xs transition-colors ${
                    a.status === 'open'
                      ? 'border-amber-200 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-900/10'
                      : a.status === 'resolved'
                        ? 'border-emerald-200 bg-emerald-50/30 dark:border-emerald-800 dark:bg-emerald-900/10'
                        : 'border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50'
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className={`rounded px-1 py-0.5 text-[10px] font-medium ${TYPE_COLORS[a.annotation_type]}`}>
                      {TYPE_LABELS[a.annotation_type]}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {new Date(a.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {a.selected_text && (
                    <div className="mb-1 rounded bg-white/80 px-1.5 py-0.5 text-[10px] text-slate-500 italic dark:bg-slate-800/80 dark:text-slate-400">
                      "{a.selected_text.length > 50 ? a.selected_text.slice(0, 50) + '...' : a.selected_text}"
                    </div>
                  )}
                  <p className="mb-1.5 text-slate-700 dark:text-slate-300">{a.content}</p>
                  {/* 关联任务状态 */}
                  {a.revision_task && (
                    <div className={`mb-1.5 flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      a.revision_task.status === 'done'
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400'
                        : a.revision_task.status === 'in_progress'
                        ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400'
                        : 'bg-sky-50 text-sky-700 dark:bg-sky-900/20 dark:text-sky-400'
                    }`}>
                      <span>📋</span>
                      <span className="truncate max-w-[180px]">{a.revision_task.title}</span>
                      <span className="opacity-70">· {a.revision_task.status === 'done' ? '已完成' : a.revision_task.status === 'in_progress' ? '进行中' : '待处理'}</span>
                    </div>
                  )}
                  {a.status === 'open' && (
                    <div>
                      <div className="flex gap-1">
                        {!a.revision_task && onConvertToTask && (
                          <button
                            onClick={() => onConvertToTask(a.id)}
                            className="rounded bg-sky-50 px-1.5 py-0.5 text-[10px] text-sky-700 hover:bg-sky-100 dark:bg-sky-900/20 dark:text-sky-400"
                          >
                            📋 转为任务
                          </button>
                        )}
                        <button
                          onClick={async () => {
                            setFixingId(a.id);
                            setFixPreview(null);
                            try {
                              const res = await annotationApi.fixAnnotation(prdId, a.id);
                              setFixPreview(res.fixed_content || '');
                            } catch {
                              setFixPreview(null);
                            } finally {
                              setFixingId(null);
                            }
                          }}
                          disabled={fixingId === a.id}
                          className="rounded bg-violet-50 px-1.5 py-0.5 text-[10px] text-violet-700 hover:bg-violet-100 disabled:opacity-50 dark:bg-violet-900/20 dark:text-violet-400"
                        >
                          {fixingId === a.id ? '⏳' : '🤖'} 修复
                        </button>
                        <button
                          onClick={() => onResolve(a.id)}
                          className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400"
                        >
                          ✓ 解决
                        </button>
                        <button
                          onClick={() => onDismiss(a.id)}
                          className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-400"
                        >
                          忽略
                        </button>
                        <button
                          onClick={() => onDelete(a.id)}
                          className="ml-auto rounded bg-rose-50 px-1.5 py-0.5 text-[10px] text-rose-700 hover:bg-rose-100 dark:bg-rose-900/20 dark:text-rose-400"
                        >
                          删除
                        </button>
                      </div>
                      {/* Fix preview */}
                      {fixPreview && (
                        <div className="mt-2 rounded-lg border border-violet-200 dark:border-violet-800 overflow-hidden">
                          <div className="bg-violet-50 dark:bg-violet-900/20 px-2 py-1 text-[10px] font-medium text-violet-700 dark:text-violet-400 flex items-center justify-between">
                            <span>AI 修复建议</span>
                            <div className="flex gap-1">
                              <button
                                onClick={() => {
                                  if (onApplyFix) onApplyFix(fixPreview);
                                  setFixPreview(null);
                                  onResolve(a.id);
                                }}
                                className="rounded bg-emerald-500 px-2 py-0.5 text-[10px] text-white hover:bg-emerald-600"
                              >
                                应用修复
                              </button>
                              <button
                                onClick={() => setFixPreview(null)}
                                className="rounded bg-white dark:bg-slate-700 px-2 py-0.5 text-[10px] text-slate-600 dark:text-slate-300"
                              >
                                放弃
                              </button>
                            </div>
                          </div>
                          <div className="max-h-64 overflow-y-auto bg-white dark:bg-slate-800 p-2 text-[11px] text-slate-700 dark:text-slate-300 whitespace-pre-wrap border-t border-violet-100 dark:border-violet-800">
                            {fixPreview.slice(0, 3000)}
                            {fixPreview.length > 3000 && <span className="text-slate-400">... (截断显示)</span>}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  {a.status !== 'open' && (
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-medium ${
                          a.status === 'resolved'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-slate-500 dark:text-slate-400'
                        }`}
                      >
                        {a.status === 'resolved' ? '✓ 已解决' : '已忽略'}
                      </span>
                      <button
                        onClick={() => onDelete(a.id)}
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
