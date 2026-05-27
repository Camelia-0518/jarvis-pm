"use client";

import { type RiskItem } from "@/lib/api";

const LEVEL_COLORS: Record<string, string> = {
  "极高": "bg-red-100 text-red-700 border-red-300 dark:bg-red-950 dark:text-red-400 dark:border-red-800",
  "高": "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-800",
  "中": "bg-yellow-100 text-yellow-700 border-yellow-300 dark:bg-yellow-950 dark:text-yellow-400 dark:border-yellow-800",
  "低": "bg-green-100 text-green-700 border-green-300 dark:bg-green-950 dark:text-green-400 dark:border-green-800",
};

const CELL_BG: Record<string, string> = {
  "低(0-0.3)/低(0-0.3)": "bg-green-50 dark:bg-green-950/30",
  "低(0-0.3)/中(0.3-0.5)": "bg-yellow-50 dark:bg-yellow-950/30",
  "低(0-0.3)/高(0.5-1.0)": "bg-orange-50 dark:bg-orange-950/30",
  "中(0.3-0.5)/低(0-0.3)": "bg-yellow-50 dark:bg-yellow-950/30",
  "中(0.3-0.5)/中(0.3-0.5)": "bg-orange-50 dark:bg-orange-950/30",
  "中(0.3-0.5)/高(0.5-1.0)": "bg-red-50 dark:bg-red-950/30",
  "高(0.5-1.0)/低(0-0.3)": "bg-orange-50 dark:bg-orange-950/30",
  "高(0.5-1.0)/中(0.3-0.5)": "bg-red-50 dark:bg-red-950/30",
  "高(0.5-1.0)/高(0.5-1.0)": "bg-red-100 dark:bg-red-950/50",
};

interface Props {
  risks: RiskItem[];
  matrix: {
    grid: Record<string, { count: number; risks: string[] }>;
    summary: Record<string, number>;
  };
}

export default function RiskMatrix({ risks, matrix }: Props) {
  const probLabels = ["低(0-0.3)", "中(0.3-0.5)", "高(0.5-1.0)"];
  const impactLabels = ["低(0-0.3)", "中(0.3-0.5)", "高(0.5-1.0)"];

  const riskMap: Record<string, RiskItem> = {};
  risks.forEach((r) => {
    riskMap[r.id] = r;
  });

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="flex gap-4 flex-wrap">
        {(["极高", "高", "中", "低"] as const).map((level) => (
          <div key={level} className="flex items-center gap-2">
            <span className={`inline-block w-3 h-3 rounded ${LEVEL_COLORS[level].split(" ")[0]}`} />
            <span className="text-sm text-slate-600 dark:text-slate-400">
              {level}风险：<strong>{matrix.summary[level] ?? 0}</strong>
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
              {probLabels.map((pl) => (
                <th key={pl} className="p-2 text-slate-500 font-medium w-28">{pl}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {impactLabels.map((il) => (
              <tr key={il}>
                <td className="p-2 text-slate-500 font-medium border border-slate-200 dark:border-slate-700">{il}</td>
                {probLabels.map((pl) => {
                  const key = `${pl}/${il}`;
                  const cell = matrix.grid[key];
                  const bg = CELL_BG[key] || "";
                  return (
                    <td key={key} className={`p-2 border border-slate-200 dark:border-slate-700 text-center ${bg}`}>
                      <div className="text-lg font-bold text-slate-700 dark:text-slate-300">
                        {cell?.count ?? 0}
                      </div>
                      {cell && cell.count > 0 && (
                        <div className="mt-1 space-y-0.5">
                          {cell.risks.slice(0, 3).map((rid) => {
                            const r = riskMap[rid];
                            return r ? (
                              <div key={rid} className="text-[10px] text-slate-500 truncate" title={r.risk}>
                                {r.risk.slice(0, 18)}{r.risk.length > 18 ? "..." : ""}
                              </div>
                            ) : null;
                          })}
                          {cell.count > 3 && (
                            <div className="text-[10px] text-slate-400">+{cell.count - 3} 个</div>
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
        {risks.slice(0, 10).map((r) => (
          <div
            key={r.id}
            className={`rounded-lg border p-3 ${LEVEL_COLORS[r.risk_level] || ""}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-slate-500">{r.id}</span>
                  <span className="text-xs font-medium text-slate-500">{r.category}</span>
                  <span className="text-xs font-bold">{r.risk_level}</span>
                </div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{r.risk}</p>
                <p className="text-xs text-slate-500 mt-1">
                  预防：{r.prevention?.slice(0, 80)}{(r.prevention?.length ?? 0) > 80 ? "..." : ""}
                </p>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                  <span>P={r.probability}</span>
                  <span>I={r.impact}</span>
                  <span>S={r.risk_score}</span>
                  <span>负责人：{r.owner}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
