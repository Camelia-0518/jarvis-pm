"use client";

import { useMemo } from "react";
import { type RiskItem } from "@/lib/api";

const LEVEL_COLORS: Record<string, string> = {
  "极高": "bg-red-100 text-red-700 border-red-300 dark:bg-red-950 dark:text-red-400 dark:border-red-800",
  "高": "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-800",
  "中": "bg-yellow-100 text-yellow-700 border-yellow-300 dark:bg-yellow-950 dark:text-yellow-400 dark:border-yellow-800",
  "低": "bg-green-100 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-400 dark:border-green-800",
};

const CELL_BG: Record<string, string> = {
  "低/低": "bg-green-50 dark:bg-green-950/30",
  "低/中": "bg-yellow-50 dark:bg-yellow-950/30",
  "低/高": "bg-orange-50 dark:bg-orange-950/30",
  "中/低": "bg-yellow-50 dark:bg-yellow-950/30",
  "中/中": "bg-orange-50 dark:bg-orange-950/30",
  "中/高": "bg-red-50 dark:bg-red-950/30",
  "高/低": "bg-orange-50 dark:bg-orange-950/30",
  "高/中": "bg-red-50 dark:bg-red-950/30",
  "高/高": "bg-red-100 dark:bg-red-950/50",
};

const LEVEL_ORDER = ["低", "中", "高"] as const;
const ALL_LEVELS = ["极高", "高", "中", "低"] as const;

function normalizeLabel(v: unknown): string {
  if (typeof v === "number") {
    if (v <= 0.3) return "低";
    if (v <= 0.5) return "中";
    return "高";
  }
  if (typeof v === "string") {
    const t = v.trim();
    if (t === "极高" || t === "高" || t === "中" || t === "低") return t;
    const n = parseFloat(t);
    if (!isNaN(n)) {
      if (n <= 0.3) return "低";
      if (n <= 0.5) return "中";
      return "高";
    }
  }
  return "中";
}

interface Props {
  risks: RiskItem[];
  matrix?: {
    grid?: Record<string, { count: number; risks: string[] }>;
    summary?: Record<string, number>;
  } | null;
}

export default function RiskMatrix({ risks, matrix }: Props) {
  // Normalize risks: fill missing ids, normalize prob/impact/level
  const normalized = useMemo(() => {
    const safeRisks = risks || [];
    return safeRisks.map((r, i) => {
      const prob = normalizeLabel(r.probability);
      const impact = normalizeLabel(r.impact);
      const level = r.risk_level || (
        prob === "高" && impact === "高" ? "极高" :
        (prob === "高" || impact === "高") ? "高" :
        (prob === "中" || impact === "中") ? "中" : "低"
      );
      return {
        ...r,
        id: r.id || `risk-${i}`,
        probability: prob,
        impact,
        risk_level: level,
      };
    });
  }, [risks]);

  // Build summary from real data
  const summary = useMemo(() => {
    const s: Record<string, number> = { "极高": 0, "高": 0, "中": 0, "低": 0 };
    normalized.forEach((r) => {
      if (s[r.risk_level] !== undefined) s[r.risk_level]++;
    });
    return s;
  }, [normalized]);

  // Build grid from real data
  const grid = useMemo(() => {
    const g: Record<string, { count: number; risks: string[] }> = {};
    for (const pl of LEVEL_ORDER) {
      for (const il of LEVEL_ORDER) {
        g[`${pl}/${il}`] = { count: 0, risks: [] };
      }
    }
    normalized.forEach((r) => {
      const key = `${r.probability}/${r.impact}`;
      if (g[key]) {
        g[key].count++;
        g[key].risks.push(r.id);
      }
    });
    return g;
  }, [normalized]);

  // Risk lookup by id
  const riskMap = useMemo(() => {
    const m: Record<string, typeof normalized[number]> = {};
    normalized.forEach((r) => { m[r.id] = r; });
    return m;
  }, [normalized]);

  // Use backend matrix if it has richer data, otherwise use computed
  const displaySummary = matrix?.summary && Object.values(matrix.summary).some((v) => v > 0)
    ? matrix.summary
    : summary;
  // Grid always computed from risks — avoids key format mismatch with backend
  const displayGrid = grid;

  if (normalized.length === 0) {
    return <p className="text-sm text-slate-500 py-8 text-center">暂无风险数据</p>;
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex gap-4 flex-wrap">
        {ALL_LEVELS.map((level) => (
          <div key={level} className="flex items-center gap-2">
            <span className={`inline-block w-3 h-3 rounded ${LEVEL_COLORS[level].split(" ")[0]}`} />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              {level}风险：<strong>{displaySummary[level] ?? 0}</strong>
            </span>
          </div>
        ))}
      </div>

      {/* Matrix grid */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-2 text-slate-500 font-medium w-24">概率 →<br />影响 ↓</th>
              {LEVEL_ORDER.map((pl) => (
                <th key={pl} className="p-2 text-slate-500 font-medium w-28">低/中/高</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {LEVEL_ORDER.map((il) => (
              <tr key={il}>
                <td className="p-2 text-slate-500 font-medium border border-slate-200 dark:border-slate-700">{il}</td>
                {LEVEL_ORDER.map((pl) => {
                  const key = `${pl}/${il}`;
                  const cell = displayGrid[key];
                  const count = cell?.count ?? 0;
                  const bg = CELL_BG[key] || "";
                  return (
                    <td key={key} className={`p-2 border border-slate-200 dark:border-slate-700 text-center ${bg}`}>
                      <div className="text-lg font-bold text-slate-700 dark:text-slate-300">
                        {count}
                      </div>
                      {count > 0 && cell && (
                        <div className="mt-1 space-y-0.5">
                          {cell.risks.slice(0, 3).map((rid) => {
                            const r = riskMap[rid];
                            return r ? (
                              <div key={rid} className="text-[10px] text-slate-500 truncate" title={r.risk}>
                                {(r.risk || "").slice(0, 18)}{(r.risk || "").length > 18 ? "..." : ""}
                              </div>
                            ) : null;
                          })}
                          {count > 3 && (
                            <div className="text-[10px] text-slate-400">+{count - 3} 个</div>
                          )}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Risk list */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">风险清单</h4>
        {normalized.slice(0, 10).map((r) => (
          <div
            key={r.id}
            className={`rounded-lg border p-3 ${LEVEL_COLORS[r.risk_level] || LEVEL_COLORS["中"]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-slate-500">{r.id}</span>
                  {r.category && <span className="text-xs font-medium text-slate-500">{r.category}</span>}
                  <span className="text-xs font-bold">{r.risk_level}</span>
                </div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{r.risk}</p>
                {r.prevention && (
                  <p className="text-xs text-slate-500 mt-1">
                    预防：{r.prevention.slice(0, 80)}{r.prevention.length > 80 ? "..." : ""}
                  </p>
                )}
                {r.contingency && (
                  <p className="text-xs text-slate-500 mt-0.5">
                    应急：{r.contingency.slice(0, 80)}{r.contingency.length > 80 ? "..." : ""}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                  <span>P={r.probability}</span>
                  <span>I={r.impact}</span>
                  {r.risk_score && <span>S={r.risk_score}</span>}
                  {r.owner && <span>负责人：{r.owner}</span>}
                </div>
              </div>
            </div>
          </div>
        ))}
        {normalized.length > 10 && (
          <p className="text-xs text-slate-400 text-center">还有 {normalized.length - 10} 条风险</p>
        )}
      </div>
    </div>
  );
}
