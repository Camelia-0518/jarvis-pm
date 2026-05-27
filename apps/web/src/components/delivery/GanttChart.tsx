"use client";

import { type GanttItem } from "@/lib/api";

const PHASE_COLORS: Record<string, string> = {
  "项目启动": "#94a3b8",
  "需求分析": "#60a5fa",
  "系统设计": "#a78bfa",
  "开发实施": "#fbbf24",
  "互联互通测评": "#2dd4bf",
  "测试验证": "#4ade80",
  "医保对接": "#22d3ee",
  "部署上线": "#f87171",
  "培训与交接": "#818cf8",
  "运维保障": "#34d399",
};

interface Props {
  items: GanttItem[];
  startDate: string;
  totalDays: number;
}

export default function GanttChart({ items, startDate, totalDays }: Props) {
  if (!items.length) {
    return <p className="text-sm text-slate-500 p-4">暂无甘特图数据</p>;
  }

  const totalWeeks = Math.ceil(totalDays / 7);
  const maxWeeks = Math.max(totalWeeks, 8);
  const weeks = Array.from({ length: maxWeeks }, (_, i) => i + 1);

  const cellWidth = 32;
  const chartWidth = maxWeeks * cellWidth;

  const addWeeks = (dateStr: string, weeks: number): string => {
    const d = new Date(dateStr);
    d.setDate(d.getDate() + weeks * 7);
    return d.toISOString().slice(0, 10);
  };

  return (
    <div className="overflow-x-auto pb-4">
      <div className="min-w-max" style={{ minWidth: chartWidth + 320 }}>
        {/* Header */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 pb-1 mb-1">
          <div className="w-80 flex-shrink-0 pr-3">
            <span className="text-xs font-semibold text-slate-500">任务</span>
          </div>
          <div className="flex" style={{ width: chartWidth }}>
            {weeks.map((w) => (
              <div key={w} className="text-[10px] text-slate-400 text-center" style={{ width: cellWidth }}>
                W{w}
              </div>
            ))}
          </div>
        </div>

        {/* Rows */}
        {items.map((item) => {
          const startWeek = Math.floor(item.start_offset_days / 7);
          const duration = item.duration_weeks;
          const color = PHASE_COLORS[item.phase] || "#94a3b8";
          const startLabel = addWeeks(startDate, startWeek);

          return (
            <div key={item.id} className="flex items-center py-1 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50">
              <div className="w-80 flex-shrink-0 pr-3">
                <div className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate" title={item.name}>
                  {item.name}
                </div>
                <div className="text-[10px] text-slate-400">
                  {item.phase} · {item.role} · {startLabel}
                </div>
              </div>
              <div className="relative" style={{ width: chartWidth, height: 28 }}>
                {/* Grid lines */}
                {weeks.map((w) => (
                  <div
                    key={w}
                    className="absolute top-0 h-full border-l border-slate-100 dark:border-slate-800"
                    style={{ left: (w - 1) * cellWidth }}
                  />
                ))}
                {/* Bar */}
                <div
                  className="absolute top-1 h-6 rounded-sm flex items-center px-1.5"
                  style={{
                    left: startWeek * cellWidth + 2,
                    width: Math.max(duration * cellWidth - 4, 24),
                    backgroundColor: color + "33",
                    borderLeft: `3px solid ${color}`,
                  }}
                >
                  {duration >= 3 && (
                    <span className="text-[10px] text-slate-600 dark:text-slate-300 font-medium truncate">
                      {item.name.length > 15 ? item.name.slice(0, 15) + "..." : item.name}
                    </span>
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
