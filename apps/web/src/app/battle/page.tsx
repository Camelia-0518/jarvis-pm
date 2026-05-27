"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { battleApi, projectApi, type Battle, type BattleDay, type Project } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";

const TOOLS = [
  { id: "research", name: "用户调研", icon: "🔍", color: "bg-sky-500", href: "/workspace", toolParam: "research" },
  { id: "prd", name: "PRD撰写", icon: "📝", color: "bg-purple-500", href: "/workspace", toolParam: "prd" },
  { id: "review", name: "评审准备", icon: "📋", color: "bg-emerald-500", href: "/workspace", toolParam: "review" },
];

const DEFAULT_DAYS: BattleDay[] = [
  { day: "Day 1", task: "用户调研", status: "pending", tool: "research", notes: "" },
  { day: "Day 2", task: "竞品分析", status: "pending", tool: "research", notes: "" },
  { day: "Day 3", task: "PRD框架搭建", status: "pending", tool: "prd", notes: "" },
  { day: "Day 4", task: "功能规格撰写", status: "pending", tool: "prd", notes: "" },
  { day: "Day 5", task: "评审材料准备", status: "pending", tool: "review", notes: "" },
];

export default function BattlePage() {
  const router = useRouter();
  const [battles, setBattles] = useState<Battle[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeBattle, setActiveBattle] = useState<Battle | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newBattle, setNewBattle] = useState({
    name: "",
    description: "",
    project_id: "",
  });

  useEffect(() => {
    loadBattles();
    loadProjects();
  }, []);

  const loadBattles = async () => {
    try {
      const res = await battleApi.list({ limit: 20 });
      const list = Array.isArray(res) ? res : res.data || [];
      setBattles(list);
      // Auto-select first active battle
      const active = list.find((b: Battle) => b.status === "active");
      if (active) setActiveBattle(active);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "加载战役失败");
    }
  };

  const loadProjects = async () => {
    try {
      const { items } = await projectApi.list();
      setProjects(items || []);
    } catch {
      // ignore
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBattle.name.trim()) return;
    setIsLoading(true);
    try {
      const created = await battleApi.create({
        name: newBattle.name,
        description: newBattle.description,
        project_id: newBattle.project_id || undefined,
        days: DEFAULT_DAYS,
      });
      const battle = Array.isArray(created) ? created : created;
      setBattles((prev) => [battle, ...prev]);
      setActiveBattle(battle);
      setShowCreateModal(false);
      setNewBattle({ name: "", description: "", project_id: "" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdvance = async () => {
    if (!activeBattle) return;
    setIsLoading(true);
    try {
      const updated = await battleApi.advance(activeBattle.id);
      const battle = Array.isArray(updated) ? updated : updated;
      setActiveBattle(battle);
      setBattles((prev) =>
        prev.map((b) => (b.id === battle.id ? { ...b, ...battle } : b))
      );
      // Show a summary of what was generated
      const currentDay = battle.days?.[battle.current_day - 2];
      if (currentDay?.notes) {
        setError(null); // clear any previous error
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "推进失败");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateDayStatus = async (index: number, status: BattleDay["status"]) => {
    if (!activeBattle) return;
    const days = [...activeBattle.days];
    days[index] = { ...days[index], status };
    try {
      const updated = await battleApi.update(activeBattle.id, { days });
      const battle = Array.isArray(updated) ? updated : updated;
      setActiveBattle(battle);
      setBattles((prev) =>
        prev.map((b) => (b.id === battle.id ? { ...b, ...battle } : b))
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "更新失败");
    }
  };

  const completedCount = activeBattle
    ? activeBattle.days.filter((d) => d.status === "completed").length
    : 0;
  const progress = activeBattle
    ? Math.round((completedCount / activeBattle.days.length) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader />

      <main className="mx-auto max-w-7xl px-4 py-8">
        {error && (
          <div className="mb-4 rounded-lg bg-rose-50 p-4 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400">
            {error}
            <button onClick={() => setError(null)} className="ml-4 text-sm underline">
              关闭
            </button>
          </div>
        )}

        {/* Title */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
              PRD 战役模式
            </h1>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              5天冲刺，从需求到评审，一站式完成专业PRD
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
          >
            + 新建战役
          </button>
        </div>

        {/* Battle Selector */}
        {battles.length > 0 && (
          <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
            {battles.map((battle) => (
              <button
                key={battle.id}
                onClick={() => setActiveBattle(battle)}
                className={`flex-shrink-0 rounded-lg border px-4 py-2 text-left text-sm ${
                  activeBattle?.id === battle.id
                    ? "border-sky-500 bg-sky-50 text-sky-700 dark:border-sky-700 dark:bg-sky-900/20"
                    : "border-slate-200 bg-white text-slate-700 hover:border-sky-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
                }`}
              >
                <div className="font-medium">{battle.name}</div>
                <div className="text-xs text-slate-500">
                  {battle.status === "active"
                    ? `Day ${battle.current_day} / ${battle.total_days}`
                    : battle.status === "completed"
                    ? "已完成"
                    : "已取消"}
                </div>
              </button>
            ))}
          </div>
        )}

        {activeBattle ? (
          <>
            {/* Active Battle Info */}
            <div className="mb-6 rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
                    {activeBattle.name}
                  </h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {activeBattle.description || "5天 PRD 冲刺战役"}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-sky-600">{progress}%</div>
                  <div className="text-xs text-slate-500">总体进度</div>
                </div>
              </div>
              <div className="mt-4 h-2 w-full rounded-full bg-slate-200">
                <div
                  className="h-2 rounded-full bg-sky-500 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Tools */}
            <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
              {TOOLS.map((tool) => (
                <Link
                  key={tool.id}
                  href={(() => {
                    const params = new URLSearchParams();
                    if (activeBattle.project_id) params.set("id", activeBattle.project_id);
                    if (tool.toolParam) params.set("tool", tool.toolParam);
                    const query = params.toString();
                    return tool.href + (query ? `?${query}` : "");
                  })()}
                  className="rounded-xl border-2 border-slate-200 bg-white p-4 text-left transition-all hover:border-sky-300 dark:border-slate-700 dark:bg-slate-800"
                >
                  <div className={`inline-flex rounded-lg p-2 text-2xl text-white ${tool.color}`}>
                    {tool.icon}
                  </div>
                  <div className="mt-3 font-semibold text-slate-800 dark:text-slate-200">
                    {tool.name}
                  </div>
                </Link>
              ))}
            </div>

            {/* Progress */}
            <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold">战役进度</h2>
                {activeBattle.status === "active" && (
                  <button
                    onClick={handleAdvance}
                    disabled={isLoading || progress >= 100}
                    className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
                  >
                    {isLoading ? "AI 生成中，请稍候..." : progress >= 100 ? "已完成" : "推进到下一天"}
                  </button>
                )}
              </div>

              <div className="space-y-3">
                {activeBattle.days.map((item, idx) => {
                  const isCurrent = idx + 1 === activeBattle.current_day && activeBattle.status === "active";
                  return (
                    <div
                      key={idx}
                      className={`flex items-center gap-4 rounded-lg p-3 ${
                        isCurrent
                          ? "border border-sky-200 bg-sky-50 dark:border-sky-800 dark:bg-sky-900/20"
                          : "bg-slate-50 dark:bg-slate-700/50"
                      }`}
                    >
                      <button
                        onClick={() =>
                          handleUpdateDayStatus(
                            idx,
                            item.status === "completed" ? "pending" : "completed"
                          )
                        }
                        className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium ${
                          item.status === "completed"
                            ? "bg-emerald-500 text-white"
                            : isCurrent
                            ? "bg-sky-500 text-white"
                            : "bg-slate-300 text-slate-600"
                        }`}
                      >
                        {item.status === "completed" ? "✓" : idx + 1}
                      </button>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {item.task}
                          </span>
                          <span className="text-xs text-slate-500">{item.day}</span>
                        </div>
                        {item.notes && (
                          <div className="mt-2 text-sm text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800/60 rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap">
                            {item.notes}
                          </div>
                        )}
                      </div>
                      {isCurrent && (
                        <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700 dark:bg-sky-900/30 dark:text-sky-400">
                          当前
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="rounded-xl bg-white p-12 text-center shadow-sm dark:bg-slate-800">
            <div className="mb-4 text-5xl">⚔️</div>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
              还没有战役
            </h2>
            <p className="mt-2 text-slate-500 dark:text-slate-400">
              点击"新建战役"开始你的第一个 5 天 PRD 冲刺
            </p>
          </div>
        )}
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 dark:bg-slate-800">
            <h2 className="mb-4 text-xl font-semibold text-slate-900 dark:text-white">
              新建战役
            </h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  战役名称
                </label>
                <input
                  type="text"
                  value={newBattle.name}
                  onChange={(e) => setNewBattle({ ...newBattle, name: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="例如：切片借阅平台 PRD 战役"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  描述
                </label>
                <textarea
                  value={newBattle.description}
                  onChange={(e) =>
                    setNewBattle({ ...newBattle, description: e.target.value })
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="简单描述战役目标"
                  rows={3}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  关联项目（可选）
                </label>
                <select
                  value={newBattle.project_id}
                  onChange={(e) =>
                    setNewBattle({ ...newBattle, project_id: e.target.value })
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                >
                  <option value="">不关联项目</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 rounded-lg bg-sky-600 px-4 py-2 text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  {isLoading ? "创建中..." : "创建"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
