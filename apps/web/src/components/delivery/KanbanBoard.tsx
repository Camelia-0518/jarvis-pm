"use client";

import { type WbsTask } from "@/lib/api";

const PHASE_COLORS: Record<string, string> = {
  "项目启动": "bg-slate-100 border-slate-300 dark:bg-slate-800 dark:border-slate-600",
  "需求分析": "bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800",
  "系统设计": "bg-purple-50 border-purple-200 dark:bg-purple-950 dark:border-purple-800",
  "开发实施": "bg-amber-50 border-amber-200 dark:bg-amber-950 dark:border-amber-800",
  "互联互通测评": "bg-teal-50 border-teal-200 dark:bg-teal-950 dark:border-teal-800",
  "测试验证": "bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800",
  "医保对接": "bg-cyan-50 border-cyan-200 dark:bg-cyan-950 dark:border-cyan-800",
  "部署上线": "bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800",
  "培训与交接": "bg-indigo-50 border-indigo-200 dark:bg-indigo-950 dark:border-indigo-800",
  "运维保障": "bg-emerald-50 border-emerald-200 dark:bg-emerald-950 dark:border-emerald-800",
};

const PRIORITY_BADGES: Record<string, string> = {
  P0: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  P1: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  P2: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

interface Props {
  tasks: WbsTask[];
}

export default function KanbanBoard({ tasks }: Props) {
  const phases = Array.from(new Set(tasks.map((t) => t.phase_name)));

  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex gap-4 min-w-max" style={{ minWidth: phases.length * 260 }}>
        {phases.map((phase) => {
          const phaseTasks = tasks.filter((t) => t.phase_name === phase);
          const color = PHASE_COLORS[phase] || "bg-slate-50 border-slate-200";
          const totalEffort = phaseTasks.reduce((sum, t) => sum + t.effort_days, 0);

          return (
            <div key={phase} className="flex-shrink-0 w-60">
              <div className={`rounded-lg border ${color} p-3`}>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{phase}</h4>
                  <span className="text-xs text-slate-500">{phaseTasks.length}项</span>
                </div>
                <div className="text-xs text-slate-500 mb-3">{totalEffort}人天</div>

                <div className="space-y-2">
                  {phaseTasks.map((task) => (
                    <div
                      key={task.id}
                      className="rounded-md border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-700 p-2 shadow-sm"
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
                        <span className="text-[10px] text-slate-400 ml-auto truncate max-w-[80px]">{task.role}</span>
                      </div>
                      {task.phase && (
                        <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                          {task.phase}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
