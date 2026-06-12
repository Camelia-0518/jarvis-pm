"use client";

import { useState, useEffect, useCallback } from "react";
import NavHeader from "@/components/global/NavHeader";
import { templateApi, promptApi, skillsApi, methodologyApi, retrospectiveApi, type Template, type PromptTemplate } from "@/lib/api";
import { toast } from "sonner";

type TabId = "templates" | "prompts" | "skills" | "methodologies" | "retrospectives";

interface SkillInfo {
  id: string; name: string; description: string; category: string; role: string;
}

export default function AssetsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("templates");

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <NavHeader />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">资产中心</h1>

        {/* Tabs */}
        <div className="mb-6 flex gap-1 rounded-xl bg-gray-100 p-1 dark:bg-gray-800 w-fit">
          {([
            { id: "templates" as TabId, label: "模板", desc: "PRD 模板" },
            { id: "prompts" as TabId, label: "提示词", desc: "AI Prompt" },
            { id: "skills" as TabId, label: "技能", desc: "Skills" },
            { id: "methodologies" as TabId, label: "方法论", desc: "方法论" },
            { id: "retrospectives" as TabId, label: "复盘", desc: "经验" },
          ]).map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                activeTab === t.id
                  ? "bg-white text-gray-900 shadow dark:bg-gray-700 dark:text-white"
                  : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              {t.label}
              <span className="ml-1 text-xs text-gray-400">{t.desc}</span>
            </button>
          ))}
        </div>

        {activeTab === "templates" && <TemplatesTab />}
        {activeTab === "prompts" && <PromptsTab />}
        {activeTab === "skills" && <SkillsTab />}
        {activeTab === "methodologies" && <MethodologyTab />}
        {activeTab === "retrospectives" && <RetrospectiveTab />}
      </main>
    </div>
  );
}

function TemplatesTab() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await templateApi.list({});
        setTemplates(Array.isArray(res) ? res : (res as { items: Template[] }).items || []);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  if (loading) return <p className="text-sm text-gray-500">加载中...</p>;
  if (!templates.length) return <p className="text-sm text-gray-500">暂无模板</p>;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {templates.map((t) => (
        <div key={t.id} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{t.icon || "📋"}</span>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{t.name}</h3>
              <p className="text-xs text-gray-500">{t.industry || "通用"} · {t.is_builtin ? "内置" : "自定义"}</p>
            </div>
          </div>
          {t.description && <p className="text-sm text-gray-600 dark:text-gray-400">{t.description}</p>}
          {t.chapters && (
            <div className="mt-3 flex flex-wrap gap-1">
              {t.chapters.slice(0, 5).map((c: string, i: number) => (
                <span key={i} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">{c}</span>
              ))}
              {t.chapters.length > 5 && <span className="text-xs text-gray-400">+{t.chapters.length - 5}</span>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function PromptsTab() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await promptApi.list();
        setPrompts(Array.isArray(res) ? res : (res as { items: PromptTemplate[] }).items || []);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  if (loading) return <p className="text-sm text-gray-500">加载中...</p>;
  if (!prompts.length) return <p className="text-sm text-gray-500">暂无提示词</p>;

  return (
    <div className="space-y-3">
      {prompts.map((p) => (
        <div key={p.id} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{p.name}</h3>
              <p className="text-xs text-gray-500">v{p.version} · {p.tags?.join(", ") || "无标签"}</p>
            </div>
            {p.is_active && (
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900 dark:text-green-300">启用</span>
            )}
          </div>
          {p.description && <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{p.description}</p>}
        </div>
      ))}
    </div>
  );
}

function SkillsTab() {
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await skillsApi.getAll();
        setSkills(Array.isArray(res) ? res : []);
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  if (loading) return <p className="text-sm text-gray-500">加载中...</p>;
  if (!skills.length) return <p className="text-sm text-gray-500">暂无技能</p>;

  // Group by category
  const grouped: Record<string, SkillInfo[]> = {};
  for (const s of skills) {
    const cat = s.category || "其他";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(s);
  }

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat}>
          <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase">{cat}</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((s) => (
              <div key={s.id} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
                <h4 className="font-medium text-gray-900 dark:text-white">{s.name}</h4>
                <p className="mt-1 text-xs text-gray-500">{s.description}</p>
                <span className="mt-2 inline-block rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-600 dark:bg-blue-900 dark:text-blue-300">{s.role}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Methodologies Tab ──

function MethodologyTab() {
  const [items, setItems] = useState<Array<{ id: string; name: string; description: string; industry: string; stages: unknown[] }>>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    (async () => {
      try { const res = await methodologyApi.list(); setItems(res.items || []); } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);
  if (loading) return <p className="text-sm text-gray-500">加载中...</p>;
  if (!items.length) return <p className="text-sm text-gray-500">暂无方法论模板</p>;
  return (
    <div className="space-y-3">
      {items.map((m) => (
        <div key={m.id} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h3 className="font-semibold text-gray-900 dark:text-white">{m.name}</h3>
          <p className="text-xs text-gray-500">{m.industry || "通用"} · {m.stages?.length || 0} 阶段</p>
          {m.description && <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{m.description}</p>}
        </div>
      ))}
    </div>
  );
}

// ── Retrospectives Tab ──

function RetrospectiveTab() {
  const [items, setItems] = useState<Array<{ id: string; title: string; project_id: string; lessons: Array<{ category: string; lesson: string; action_item: string }>; created_at?: string }>>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    (async () => {
      try { const res = await retrospectiveApi.list(); setItems(res.items || []); } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);
  if (loading) return <p className="text-sm text-gray-500">加载中...</p>;
  if (!items.length) return <p className="text-sm text-gray-500">暂无复盘记录</p>;
  return (
    <div className="space-y-3">
      {items.map((r) => (
        <div key={r.id} className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h3 className="font-semibold text-gray-900 dark:text-white">{r.title}</h3>
          <p className="text-xs text-gray-500">{r.created_at ? new Date(r.created_at).toLocaleString("zh-CN") : "-"}</p>
          <div className="mt-2 space-y-1">
            {r.lessons?.map((l, i) => (
              <div key={i} className="flex gap-2 text-sm">
                <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs ${l.category === "well" ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300" : l.category === "wrong" ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300" : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"}`}>
                  {l.category === "well" ? "👍" : l.category === "wrong" ? "⚠️" : "💡"}
                </span>
                <span className="text-gray-600 dark:text-gray-400">{l.lesson}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
