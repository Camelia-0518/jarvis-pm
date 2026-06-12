"use client";

import { useState, type DragEvent } from "react";

export interface KanbanTask {
  id: string;
  phase_id: string;
  phase_name: string;
  name: string;
  effort_days: number;
  dependencies: string[];
  role: string;
  priority: string;
  phase: string;
  status?: string;
}

const STATUS_COLS = [
  { key: "todo", label: "待办", color: "border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-900" },
  { key: "in_progress", label: "进行中", color: "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950" },
  { key: "done", label: "已完成", color: "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-950" },
];

const PRIORITY_BADGES: Record<string, string> = {
  P0: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  P1: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  P2: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

interface Props {
  tasks: KanbanTask[];
  onTaskUpdate?: (taskId: string, patch: Record<string, unknown>) => void;
}

export default function KanbanBoard({ tasks, onTaskUpdate }: Props) {
  const [dragTaskId, setDragTaskId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  const getStatus = (t: KanbanTask) => t.status || "todo";

  const handleDragStart = (taskId: string) => {
    setDragTaskId(taskId);
  };

  const handleDragOver = (e: DragEvent, colKey: string) => {
    e.preventDefault();
    setDropTarget(colKey);
  };

  const handleDrop = (colKey: string) => {
    if (dragTaskId && onTaskUpdate) {
      onTaskUpdate(dragTaskId, { status: colKey });
    }
    setDragTaskId(null);
    setDropTarget(null);
  };

  const handleDragEnd = () => {
    setDragTaskId(null);
    setDropTarget(null);
  };

  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex gap-4 min-w-max" style={{ minWidth: 780 }}>
        {STATUS_COLS.map((col) => {
          const colTasks = tasks.filter((t) => getStatus(t) === col.key);
          const totalEffort = colTasks.reduce((s, t) => s + t.effort_days, 0);
          const isOver = dropTarget === col.key;

          return (
            <div
              key={col.key}
              className="flex-shrink-0 w-64"
              onDragOver={(e) => handleDragOver(e, col.key)}
              onDrop={() => handleDrop(col.key)}
            >
              <div className={`rounded-lg border-2 ${isOver ? "border-sky-400 bg-sky-50 dark:bg-sky-950" : col.color} p-3 transition-colors`}>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{col.label}</h4>
                  <span className="text-xs text-slate-500">{colTasks.length}项</span>
                </div>
                <div className="text-xs text-slate-500 mb-3">{totalEffort}人天</div>

                <div className="space-y-2 min-h-[60px]">
                  {colTasks.map((task) => (
                    <div
                      key={task.id}
                      draggable
                      onDragStart={() => handleDragStart(task.id)}
                      onDragEnd={handleDragEnd}
                      className={`rounded-md border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-700 p-2 shadow-sm cursor-grab active:cursor-grabbing ${dragTaskId === task.id ? "opacity-50" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300 leading-tight">
                          {task.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${PRIORITY_BADGES[task.priority] || PRIORITY_BADGES.P1}`}>
                          {task.priority}
                        </span>
                        <span className="text-[10px] text-slate-400">{task.effort_days}d</span>
                        <span className="text-[10px] text-slate-400 ml-auto truncate max-w-[70px]">{task.role}</span>
                      </div>
                      <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        {task.phase_name}
                      </span>
                    </div>
                  ))}
                  {colTasks.length === 0 && (
                    <div className="text-xs text-slate-400 text-center py-4">
                      {isOver ? "释放以移入" : "拖拽任务到此处"}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
