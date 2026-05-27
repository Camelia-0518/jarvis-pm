"use client";

import { useState } from "react";
import { type Stakeholder, type RaciMatrix, type CommunicationPlan } from "@/lib/api";

interface Props {
  stakeholders: Stakeholder[];
  raci: RaciMatrix | null;
  communicationPlan: CommunicationPlan | null;
}

export default function StakeholderPanel({ stakeholders, raci, communicationPlan }: Props) {
  const [view, setView] = useState<"stakeholders" | "raci" | "meetings" | "reports">("stakeholders");

  const influenceColor = (level: string) => {
    const map: Record<string, string> = {
      "高": "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
      "中": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
      "低": "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    };
    return map[level] || "bg-slate-100 text-slate-600";
  };

  return (
    <div className="space-y-6">
      {/* Sub-nav */}
      <div className="flex gap-4 border-b border-slate-200 dark:border-slate-700 pb-2">
        {([
          { key: "stakeholders", label: "干系人登记" },
          { key: "raci", label: "RACI矩阵" },
          { key: "meetings", label: "会议节奏" },
          { key: "reports", label: "报告体系" },
        ] as const).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setView(tab.key)}
            className={`text-sm font-medium pb-2 -mb-0.5 border-b-2 transition-colors ${
              view === tab.key
                ? "border-sky-600 text-sky-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Stakeholders list */}
      {view === "stakeholders" && (
        <div className="space-y-3">
          {stakeholders.map((s) => (
            <div key={s.id} className="rounded-lg border bg-white dark:bg-slate-950 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{s.role}</span>
                    <span className="text-xs text-slate-400">{s.dept}</span>
                  </div>
                  <p className="text-xs text-slate-500">关注：{s.concern}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${influenceColor(s.influence)}`}>
                    影响力{s.influence}
                  </span>
                  <span className="text-xs text-slate-400">{s.comm_freq}</span>
                </div>
              </div>
              <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
                <span>参与度：{s.interest}</span>
                <span>方式：{s.comm_channel}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* RACI Matrix */}
      {view === "raci" && raci && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="p-2 text-left text-slate-500 font-medium border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 w-40">
                  活动
                </th>
                {raci.roles.slice(0, 8).map((r) => (
                  <th key={r.id} className="p-2 text-center text-slate-500 font-medium border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 max-w-[80px]">
                    <div className="text-[10px] leading-tight">{r.name.length > 6 ? r.name.slice(0, 6) + "..." : r.name}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {raci.activities.map((act) => (
                <tr key={act.id} className="hover:bg-slate-50 dark:hover:bg-slate-900">
                  <td className="p-2 border border-slate-200 dark:border-slate-700">
                    <div className="text-xs text-slate-700 dark:text-slate-300">{act.name}</div>
                    <div className="text-[10px] text-slate-400">{act.phase}</div>
                  </td>
                  {raci.roles.slice(0, 8).map((r) => {
                    const val = raci.assignments?.[act.id]?.[r.id] || "";
                    const valColor: Record<string, string> = {
                      R: "bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-300",
                      A: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
                      C: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
                      I: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
                    };
                    return (
                      <td key={r.id} className="p-1 text-center border border-slate-200 dark:border-slate-700">
                        {val && (
                          <span className={`inline-block w-5 h-5 rounded text-[11px] font-bold leading-5 ${valColor[val] || ""}`}>
                            {val}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 flex gap-4 text-xs text-slate-500">
            <span><strong className="text-sky-600">R</strong>=负责执行</span>
            <span><strong className="text-orange-600">A</strong>=审批决策</span>
            <span><strong className="text-purple-600">C</strong>=咨询意见</span>
            <span><strong className="text-slate-600">I</strong>=知会即可</span>
          </div>
        </div>
      )}

      {/* Meetings */}
      {view === "meetings" && communicationPlan && (
        <div className="space-y-4">
          {communicationPlan.meetings.map((m) => (
            <div key={m.id} className="rounded-lg border bg-white dark:bg-slate-950 p-4">
              <div className="flex items-start justify-between mb-2">
                <h4 className="text-sm font-medium text-slate-800 dark:text-slate-200">{m.name}</h4>
                <span className="text-xs text-slate-400">{m.duration}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 mb-2">
                <div>频率：{m.frequency}</div>
                <div>方式：{m.format}</div>
                <div className="col-span-2">参与：{m.participants.slice(0, 5).join("、")}</div>
                <div className="col-span-2">产出：{m.output}</div>
              </div>
              <div className="flex flex-wrap gap-1">
                {m.agenda.map((a, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                    {a}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reports */}
      {view === "reports" && communicationPlan && (
        <div className="space-y-3">
          {communicationPlan.reports.map((r, i) => (
            <div key={i} className="rounded-lg border bg-white dark:bg-slate-950 p-4">
              <h4 className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-1">{r.name}</h4>
              <div className="text-xs text-slate-500 space-y-1">
                <div>受众：{r.audience}</div>
                <div>内容：{r.content}</div>
                <div>模板：{r.template}</div>
              </div>
            </div>
          ))}

          {communicationPlan.escalation_path.length > 0 && (
            <div className="rounded-lg border bg-amber-50 dark:bg-amber-950/30 p-4 mt-4">
              <h4 className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-2">问题升级路径</h4>
              {communicationPlan.escalation_path.map((path, i) => (
                <p key={i} className="text-xs text-amber-700 dark:text-amber-300">{path}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}