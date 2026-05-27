"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { skillsApi, type SkillDefinition } from "@/lib/api";
import { useSkillStore } from "@/stores/skillStore";
import NavHeader from "@/components/global/NavHeader";

const CATEGORY_LABELS: Record<string, string> = {
  analysis: "分析",
  design: "设计",
  development: "开发",
  review: "评审",
  medical: "医疗",
  planning: "规划",
};

const CATEGORY_ICONS: Record<string, string> = {
  analysis: "🔍",
  design: "🎨",
  development: "💻",
  review: "👀",
  medical: "🏥",
  planning: "📅",
};

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [categories, setCategories] = useState<Array<{ value: string; label: string; icon: string }>>([]);
  const [executions, setExecutions] = useState<Array<{ id: string; skillName: string; skillId: string; status: string; createdAt: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillDefinition | null>(null);
  const [skillInputs, setSkillInputs] = useState<Record<string, unknown>>({});
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState<Record<string, unknown> | null>(null);
  const [executeError, setExecuteError] = useState<string | null>(null);

  const skillStore = useSkillStore();

  useEffect(() => {
    async function loadData() {
      try {
        const [skillsRes, catsRes, execsRes] = await Promise.all([
          skillsApi.getAll(),
          skillsApi.getCategories(),
          skillsApi.getExecutions({ limit: 10 }),
        ]);
        setSkills(skillsRes?.skills || []);
        setCategories(catsRes || []);
        const execs = Array.isArray(execsRes) ? execsRes : [];
        setExecutions(execs.slice(0, 10));
      } catch {
        setSkills([]);
        setCategories([]);
        setExecutions([]);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const filteredSkills = skills.filter((skill) => {
    const matchesCategory = selectedCategory ? skill.category === selectedCategory : true;
    const matchesSearch = searchQuery
      ? skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.tags?.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
      : true;
    return matchesCategory && matchesSearch;
  });

  const handleExecute = async () => {
    if (!selectedSkill) return;
    setExecuting(true);
    setExecuteResult(null);
    setExecuteError(null);
    try {
      const result = await skillStore.executeSkill(selectedSkill.id, skillInputs);
      setExecuteResult(result ? { ...result } : null);
    } catch (err: unknown) {
      setExecuteError(err instanceof Error ? err.message : "执行失败");
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">加载技能列表...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Search & Filter */}
        <div className="mb-8 space-y-4">
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="搜索技能..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 rounded-lg border border-slate-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                selectedCategory === null
                  ? "bg-sky-600 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              }`}
            >
              全部
            </button>
            {categories.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setSelectedCategory(cat.value === selectedCategory ? null : cat.value)}
                className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                  selectedCategory === cat.value
                    ? "bg-sky-600 text-white"
                    : "bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                }`}
              >
                {cat.icon} {cat.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-8 lg:grid-cols-3">
          {/* Skills Grid */}
          <div className="lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                全部技能
              </h2>
              <span className="text-sm text-slate-500">{filteredSkills.length} 个技能</span>
            </div>

            {filteredSkills.length === 0 ? (
              <div className="rounded-xl bg-white p-12 text-center dark:bg-slate-800">
                <div className="text-4xl mb-4">🔍</div>
                <div className="text-slate-600 dark:text-slate-300">未找到匹配的技能</div>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {filteredSkills.map((skill) => (
                  <div
                    key={skill.id}
                    onClick={() => {
                      setSelectedSkill(skill);
                      setSkillInputs({});
                      setExecuteResult(null);
                    }}
                    className={`cursor-pointer rounded-xl bg-white p-5 shadow-sm transition-all hover:shadow-md dark:bg-slate-800 ${
                      selectedSkill?.id === skill.id ? "ring-2 ring-sky-500" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{skill.icon || "⚡"}</span>
                        <div>
                          <h3 className="font-semibold text-slate-900 dark:text-white">{skill.name}</h3>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{skill.agentRole}</p>
                        </div>
                      </div>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                        {CATEGORY_LABELS[skill.category] || skill.category}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                      {skill.description}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-1">
                      {skill.tags?.slice(0, 3).map((tag) => (
                        <span key={tag} className="rounded bg-slate-50 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-700/50 dark:text-slate-400">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Panel: Execution Form or History */}
          <div className="space-y-6">
            {selectedSkill ? (
              <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                    {selectedSkill.name}
                  </h2>
                  <button onClick={() => setSelectedSkill(null)} className="text-slate-400 hover:text-slate-600">
                    ✕
                  </button>
                </div>
                <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">{selectedSkill.description}</p>

                {/* Parameters */}
                {selectedSkill.parameters?.length > 0 && (
                  <div className="space-y-3">
                    {selectedSkill.parameters.map((param) => (
                      <div key={param.name}>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                          {param.label}
                          {param.required && <span className="text-rose-500">*</span>}
                        </label>
                        {param.type === "textarea" ? (
                          <textarea
                            value={String(skillInputs[param.name] || "")}
                            onChange={(e) => setSkillInputs({ ...skillInputs, [param.name]: e.target.value })}
                            placeholder={param.placeholder || ""}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                            rows={3}
                          />
                        ) : param.type === "select" && param.options ? (
                          <select
                            value={String(skillInputs[param.name] || param.defaultValue || "")}
                            onChange={(e) => setSkillInputs({ ...skillInputs, [param.name]: e.target.value })}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                          >
                            {param.options.map((opt) => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type={param.type === "number" ? "number" : "text"}
                            value={String(skillInputs[param.name] || param.defaultValue || "")}
                            onChange={(e) => setSkillInputs({ ...skillInputs, [param.name]: param.type === "number" ? Number(e.target.value) : e.target.value })}
                            placeholder={param.placeholder || ""}
                            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                          />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="mt-4 w-full rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  {executing ? "执行中..." : "执行技能"}
                </button>

                {/* Result */}
                {executeError && (
                  <div className="mt-4 rounded-lg bg-rose-50 p-3 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
                    {executeError}
                  </div>
                )}
                {executeResult && (
                  <div className="mt-4">
                    <SkillResultViewer result={executeResult} />
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                  最近执行
                </h2>
                {executions.length === 0 ? (
                  <div className="text-sm text-slate-400 text-center py-4">暂无执行记录</div>
                ) : (
                  <div className="space-y-2">
                    {executions.map((exec) => (
                      <div key={exec.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-700/50">
                        <div className="flex items-center gap-2">
                          <span className={`h-2 w-2 rounded-full ${exec.status === "completed" ? "bg-emerald-500" : exec.status === "running" ? "bg-sky-500" : "bg-rose-500"}`} />
                          <span className="text-sm text-slate-700 dark:text-slate-300 truncate max-w-[180px]">{exec.skillName || exec.skillId}</span>
                        </div>
                        <span className="text-xs text-slate-400">
                          {exec.createdAt ? new Date(exec.createdAt).toLocaleDateString() : "-"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function SkillResultViewer({ result }: { result: Record<string, unknown> }) {
  const [showRaw, setShowRaw] = useState(false);

  const formattedOutput = result.formattedOutput as string | undefined;
  const output = result.output as Record<string, unknown> | undefined;
  const executionTime = result.executionTime as number | undefined;
  const tokenUsage = result.tokenUsage as Record<string, number> | undefined;
  const success = result.success as boolean;
  const error = result.error as string | undefined;
  const skillId = result.skillId as string | undefined;

  if (showRaw) {
    return (
      <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-700/50">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">原始响应</span>
          <button
            onClick={() => setShowRaw(false)}
            className="text-xs text-sky-600 hover:text-sky-700 dark:text-sky-400"
          >
            查看格式化结果
          </button>
        </div>
        <pre className="text-xs whitespace-pre-wrap overflow-auto max-h-64 text-slate-700 dark:text-slate-300">
          {JSON.stringify(result, null, 2)}
        </pre>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-slate-800 space-y-4">
      {/* Status Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3 dark:border-slate-700">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${success ? "bg-emerald-500" : "bg-rose-500"}`} />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {success ? "执行成功" : "执行失败"}
          </span>
        </div>
        <button
          onClick={() => setShowRaw(true)}
          className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
        >
          查看原始JSON
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400">
          {error}
        </div>
      )}

      {/* Formatted Output (Markdown) */}
      {formattedOutput && (
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{formattedOutput}</ReactMarkdown>
        </div>
      )}

      {/* Structured Output */}
      {output && Object.keys(output).length > 0 && !formattedOutput && (
        <StructuredOutput data={output} />
      )}

      {/* Meta */}
      <div className="flex flex-wrap gap-3 text-xs text-slate-400 dark:text-slate-500 border-t border-slate-100 pt-3 dark:border-slate-700">
        {skillId && <span>技能: {skillId}</span>}
        {executionTime !== undefined && <span>耗时: {executionTime}ms</span>}
        {tokenUsage && Object.entries(tokenUsage).map(([k, v]) => (
          <span key={k}>{k}: {v}</span>
        ))}
      </div>
    </div>
  );
}

function StructuredOutput({ data }: { data: Record<string, unknown> }) {
  // Render sections if present
  const sections = data.sections as Array<Record<string, unknown>> | undefined;
  if (sections && Array.isArray(sections)) {
    return (
      <div className="space-y-3">
        {sections.map((section, idx) => (
          <div key={idx} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-700/30">
            {!!section.title && (
              <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
                {String(section.title)}
              </h4>
            )}
            {!!section.content && (
              <p className="text-sm text-slate-600 dark:text-slate-400">{String(section.content)}</p>
            )}
            {!!section.items && Array.isArray(section.items) && (
              <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-400 space-y-1">
                {section.items.map((item: unknown, i: number) => (
                  <li key={i}>{typeof item === "string" ? (item as string) : JSON.stringify(item)}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    );
  }

  // Render table if rows present
  const rows = data.rows as Array<Record<string, unknown>> | undefined;
  const columns = data.columns as Array<{ key: string; label: string }> | undefined;
  if (rows && Array.isArray(rows) && rows.length > 0) {
    const cols = columns || Object.keys(rows[0]).map((k) => ({ key: k, label: k }));
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              {cols.map((col) => (
                <th key={col.key} className="text-left px-2 py-1.5 font-medium text-slate-600 dark:text-slate-400">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx} className="border-b border-slate-100 dark:border-slate-800">
                {cols.map((col) => (
                  <td key={col.key} className="px-2 py-1.5 text-slate-700 dark:text-slate-300">
                    {typeof row[col.key] === "string" ? (row[col.key] as string) : JSON.stringify(row[col.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Default: key-value pairs
  return (
    <div className="space-y-2">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="flex gap-2">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0">{key}:</span>
          <span className="text-sm text-slate-700 dark:text-slate-300">
            {typeof value === "string" ? value : JSON.stringify(value)}
          </span>
        </div>
      ))}
    </div>
  );
}
