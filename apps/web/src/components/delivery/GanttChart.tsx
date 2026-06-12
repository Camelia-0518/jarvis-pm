"use client";

import { useState, useRef, useCallback, useEffect, type MouseEvent as RMouseEvent } from "react";

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

export interface GanttItem {
  id: string;
  name: string;
  phase: string;
  start_offset_days: number;
  duration_weeks: number;
  dependencies: string[];
  priority: string;
  role: string;
  phase_label: string;
}

interface Props {
  items: GanttItem[];
  startDate: string;
  totalDays: number;
  onItemUpdate?: (itemId: string, patch: Record<string, unknown>) => void;
}

export default function GanttChart({ items, startDate, totalDays, onItemUpdate }: Props) {
  const [dragging, setDragging] = useState<{ id: string; side: "left" | "right" | "move" } | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  const totalWeeks = Math.ceil(totalDays / 7);
  const maxWeeks = Math.max(totalWeeks, 8);
  const cellWidth = 32;
  const chartWidth = maxWeeks * cellWidth;

  const handleMouseDown = useCallback((e: RMouseEvent, itemId: string, side: "left" | "right" | "move") => {
    e.preventDefault();
    e.stopPropagation();
    setDragging({ id: itemId, side });
  }, []);

  const handleMouseMove = useCallback(
    (e: globalThis.MouseEvent) => {
      if (!dragging || !onItemUpdate || !chartRef.current) return;
      const rect = chartRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left - 320; // subtract label width
      const week = Math.round(x / cellWidth);
      if (week < 0) return;

      const item = items.find((it) => it.id === dragging.id);
      if (!item) return;

      if (dragging.side === "left") {
        const newStart = Math.max(0, week * 7);
        const diff = (item.start_offset_days + item.duration_weeks * 7) - newStart;
        const newDuration = Math.max(1, Math.round(diff / 7));
        onItemUpdate(item.id, { start_offset_days: newStart, duration_weeks: newDuration });
      } else if (dragging.side === "right") {
        const newEnd = Math.max(1, week);
        const newDuration = Math.max(1, newEnd - Math.floor(item.start_offset_days / 7));
        onItemUpdate(item.id, { duration_weeks: newDuration });
      } else if (dragging.side === "move") {
        const newStart = Math.max(0, week * 7);
        onItemUpdate(item.id, { start_offset_days: newStart });
      }
    },
    [dragging, items, onItemUpdate]
  );

  const handleMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  // Attach global listeners when dragging
  useEffect(() => {
    if (!dragging) return;
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging, handleMouseMove, handleMouseUp]);

  if (!items.length) {
    return <p className="text-sm text-slate-500 p-4">暂无甘特图数据</p>;
  }

  const weeks = Array.from({ length: maxWeeks }, (_, i) => i + 1);

  const addWeeks = (dateStr: string, weeks: number): string => {
    const d = new Date(dateStr);
    d.setDate(d.getDate() + weeks * 7);
    return d.toISOString().slice(0, 10);
  };

  return (
    <div className="overflow-x-auto pb-4" ref={chartRef}>
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
          const isDragging = dragging?.id === item.id;

          return (
            <div
              key={item.id}
              className={`flex items-center py-1 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 ${isDragging ? "bg-sky-50 dark:bg-sky-950" : ""}`}
            >
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
                  className={`absolute top-1 h-6 rounded-sm flex items-center px-1.5 group ${onItemUpdate ? "cursor-grab" : ""}`}
                  style={{
                    left: startWeek * cellWidth + 2,
                    width: Math.max(duration * cellWidth - 4, 24),
                    backgroundColor: color + "33",
                    borderLeft: `3px solid ${color}`,
                  }}
                  onMouseDown={onItemUpdate ? (e) => handleMouseDown(e, item.id, "move") : undefined}
                >
                  {/* Left resize handle */}
                  {onItemUpdate && (
                    <div
                      className="absolute left-0 top-0 w-2 h-full cursor-col-resize opacity-0 group-hover:opacity-100 hover:bg-black/10 rounded-l-sm"
                      onMouseDown={(e) => { e.stopPropagation(); handleMouseDown(e, item.id, "left"); }}
                    />
                  )}
                  {duration >= 3 && (
                    <span className="text-[10px] text-slate-600 dark:text-slate-300 font-medium truncate">
                      {item.name.length > 15 ? item.name.slice(0, 15) + "..." : item.name}
                    </span>
                  )}
                  {/* Right resize handle */}
                  {onItemUpdate && (
                    <div
                      className="absolute right-0 top-0 w-2 h-full cursor-col-resize opacity-0 group-hover:opacity-100 hover:bg-black/10 rounded-r-sm"
                      onMouseDown={(e) => { e.stopPropagation(); handleMouseDown(e, item.id, "right"); }}
                    />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {!onItemUpdate && (
        <p className="text-xs text-slate-400 mt-2 text-center">拖拽调整功能需开启编辑模式</p>
      )}
    </div>
  );
}
