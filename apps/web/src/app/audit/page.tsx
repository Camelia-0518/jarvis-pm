"use client";

import { useState, useEffect, useMemo } from "react";
import NavHeader from "@/components/global/NavHeader";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import Link from "next/link";

interface AuditEntry {
  id: string;
  user_id: string;
  workspace_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  summary: string | null;
  created_at: string;
}

const ACTION_LABELS: Record<string, string> = {
  create: "创建", update: "更新", delete: "删除",
  retry: "重试", login: "登录", complete: "完成",
};

const RESOURCE_LABELS: Record<string, string> = {
  project: "项目", prd: "PRD", annotation: "批注",
  job: "任务", task: "修订任务", template: "模板",
  prompt: "提示词", workspace: "工作区",
};

const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400",
  delete: "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400",
  update: "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400",
  retry: "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400",
  complete: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400",
};

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId);

  // Filters
  const [filterAction, setFilterAction] = useState("");
  const [filterResource, setFilterResource] = useState("");
  const [filterUser, setFilterUser] = useState("");
  const [filterDays, setFilterDays] = useState("7");

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (activeWorkspaceId) params.set("workspace_id", activeWorkspaceId);
        params.set("limit", "200");
        const res = await fetch(`/api/v1/system/audit?${params.toString()}`);
        const data = await res.json();
        setEntries(data.data || []);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, [activeWorkspaceId]);

  const filtered = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - parseInt(filterDays || "0", 10) || 0);

    return entries.filter((e) => {
      if (filterAction && e.action !== filterAction) return false;
      if (filterResource && e.resource_type !== filterResource) return false;
      if (filterUser && !e.user_id.toLowerCase().includes(filterUser.toLowerCase())) return false;
      if (filterDays && e.created_at && new Date(e.created_at) < cutoff) return false;
      return true;
    });
  }, [entries, filterAction, filterResource, filterUser, filterDays]);

  // Cross-link helper
  const resourceLink = (e: AuditEntry): { href: string; label: string } | null => {
    if (!e.resource_id) return null;
    if (e.resource_type === "project") return { href: `/workspace?id=${e.resource_id}`, label: "查看项目" };
    if (e.resource_type === "prd") return { href: `/prd/${e.resource_id}`, label: "查看 PRD" };
    if (e.resource_type === "job") return { href: "/jobs", label: "查看任务" };
    return null;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <NavHeader />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">审计中心</h1>

        {/* Filter bar */}
        <div className="mb-4 flex flex-wrap gap-2">
          <select value={filterAction} onChange={(e) => setFilterAction(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
            <option value="">全部操作</option>
            {Object.entries(ACTION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select value={filterResource} onChange={(e) => setFilterResource(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
            <option value="">全部资源</option>
            {Object.entries(RESOURCE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input type="text" placeholder="用户 ID..." value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white w-32" />
          <select value={filterDays} onChange={(e) => setFilterDays(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white">
            <option value="">全部时间</option>
            <option value="1">最近 1 天</option>
            <option value="3">最近 3 天</option>
            <option value="7">最近 7 天</option>
            <option value="30">最近 30 天</option>
          </select>
          <span className="self-center text-xs text-gray-400 ml-auto">
            {filtered.length} / {entries.length} 条
          </span>
        </div>

        {loading ? (
          <p className="text-gray-500">加载中...</p>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl bg-white p-12 text-center dark:bg-gray-900">
            <p className="text-gray-500">暂无匹配的审计记录</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-left dark:border-gray-800 dark:bg-gray-800/50">
                <tr>
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">时间</th>
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">用户</th>
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">操作</th>
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">资源</th>
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">摘要</th>
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filtered.map((e) => {
                  const link = resourceLink(e);
                  const isOpen = expanded === e.id;
                  return (
                    <tr key={e.id} className="group hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="whitespace-nowrap px-4 py-2.5 text-gray-500">
                        {e.created_at ? new Date(e.created_at).toLocaleString("zh-CN") : "-"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs text-gray-500 font-mono max-w-[80px] truncate"
                        title={e.user_id}>{e.user_id.slice(0, 8)}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLORS[e.action] || "bg-gray-100 text-gray-700"}`}>
                          {ACTION_LABELS[e.action] || e.action}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-600 dark:text-gray-400">
                        {RESOURCE_LABELS[e.resource_type] || e.resource_type}
                      </td>
                      <td className="max-w-[200px] truncate px-4 py-2.5 text-gray-600 dark:text-gray-400">
                        {e.summary || "-"}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button onClick={() => setExpanded(isOpen ? null : e.id)}
                          className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400">
                          {isOpen ? "收起" : "详情"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Expanded detail panel */}
        {expanded && (() => {
          const e = entries.find((x) => x.id === expanded);
          if (!e) return null;
          const link = resourceLink(e);
          return (
            <div className="mt-4 rounded-xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-800 dark:bg-blue-900/20">
              <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">审计详情</h3>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-gray-500">ID：</span><span className="font-mono text-xs">{e.id}</span></div>
                <div><span className="text-gray-500">用户：</span><span className="font-mono text-xs">{e.user_id}</span></div>
                <div><span className="text-gray-500">操作：</span>{ACTION_LABELS[e.action] || e.action}</div>
                <div><span className="text-gray-500">资源类型：</span>{RESOURCE_LABELS[e.resource_type] || e.resource_type}</div>
                <div><span className="text-gray-500">资源 ID：</span><span className="font-mono text-xs">{e.resource_id || "-"}</span></div>
                <div><span className="text-gray-500">时间：</span>{e.created_at ? new Date(e.created_at).toLocaleString("zh-CN") : "-"}</div>
                <div className="col-span-2"><span className="text-gray-500">摘要：</span>{e.summary || "-"}</div>
              </dl>
              {link && (
                <div className="mt-3">
                  <Link href={link.href} className="text-sm text-blue-600 hover:underline dark:text-blue-400">
                    {link.label} →
                  </Link>
                </div>
              )}
            </div>
          );
        })()}
      </main>
    </div>
  );
}
