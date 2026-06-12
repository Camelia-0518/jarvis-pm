"use client";

import { useState, useEffect } from "react";
import { requirementApi, type Requirement, type PriorityMatrix } from "@/lib/api";
import { toast } from "sonner";
import { confirm } from "@/components/ui/ConfirmDialog";

interface Props {
  projectId: string;
}

const KANO_LABELS: Record<string, string> = {
  must_be: "必备",
  one_dimensional: "期望",
  attractive: "魅力",
  indifferent: "无差异",
  reverse: "反向",
  "": "未分类",
};

const KANO_COLORS: Record<string, string> = {
  must_be: "bg-rose-100 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400",
  one_dimensional: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400",
  attractive: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400",
  indifferent: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400",
  reverse: "bg-violet-100 text-violet-700 dark:bg-violet-900/20 dark:text-violet-400",
  "": "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
};

const PRIORITY_COLORS: Record<string, string> = {
  p0: "bg-rose-100 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400",
  p1: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400",
  p2: "bg-sky-100 text-sky-700 dark:bg-sky-900/20 dark:text-sky-400",
};

const STATUS_LABELS: Record<string, string> = {
  backlog: "待办",
  todo: "计划中",
  in_progress: "进行中",
  done: "已完成",
};

const STATUS_COLORS: Record<string, string> = {
  backlog: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400",
  todo: "bg-sky-100 text-sky-700 dark:bg-sky-900/20 dark:text-sky-400",
  in_progress: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400",
  done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400",
};

export default function RequirementPanel({ projectId }: Props) {
  const [view, setView] = useState<"list" | "matrix">("list");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [matrix, setMatrix] = useState<PriorityMatrix | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState("created_at");
  const [order, setOrder] = useState("desc");
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    status: "backlog",
    priority: "p1",
    rice_reach: 0,
    rice_impact: 0.5,
    rice_confidence: 50,
    rice_effort: 1,
    kano_category: "",
  });

  const loadRequirements = async () => {
    setIsLoading(true);
    try {
      const res = await requirementApi.list(projectId, { sort_by: sortBy, order });
      setRequirements(res || []);
    } catch {
      setRequirements([]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMatrix = async () => {
    setIsLoading(true);
    try {
      const res = await requirementApi.getPriorityMatrix(projectId);
      setMatrix(res);
    } catch {
      setMatrix(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (view === "list") {
      loadRequirements();
    } else {
      loadMatrix();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, view, sortBy, order]);

  const resetForm = () => {
    setFormData({
      title: "",
      description: "",
      status: "backlog",
      priority: "p1",
      rice_reach: 0,
      rice_impact: 0.5,
      rice_confidence: 50,
      rice_effort: 1,
      kano_category: "",
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;
    try {
      if (editingId) {
        await requirementApi.update(editingId, formData);
      } else {
        await requirementApi.create(projectId, formData);
      }
      resetForm();
      if (view === "list") loadRequirements();
      else loadMatrix();
    } catch {
      toast.error("保存失败，请重试");
    }
  };

  const handleEdit = (r: Requirement) => {
    setFormData({
      title: r.title,
      description: r.description || "",
      status: r.status,
      priority: r.priority,
      rice_reach: r.rice_reach,
      rice_impact: r.rice_impact,
      rice_confidence: r.rice_confidence,
      rice_effort: r.rice_effort,
      kano_category: r.kano_category,
    });
    setEditingId(r.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    const confirmed = await confirm({
      title: "删除需求",
      message: "确定删除该需求？",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await requirementApi.delete(id);
      if (view === "list") loadRequirements();
      else loadMatrix();
    } catch {
      toast.error("删除失败");
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">需求池</h3>
          <div className="flex rounded-lg bg-slate-100 dark:bg-slate-700 p-0.5">
            <button
              onClick={() => setView("list")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                view === "list"
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-600 dark:text-white"
                  : "text-slate-500 dark:text-slate-400"
              }`}
            >
              列表
            </button>
            <button
              onClick={() => setView("matrix")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                view === "matrix"
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-600 dark:text-white"
                  : "text-slate-500 dark:text-slate-400"
              }`}
            >
              优先级矩阵
            </button>
          </div>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
        >
          + 新建需求
        </button>
      </div>

      {/* List View */}
      {view === "list" && (
        <>
          {/* Sort controls */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">排序：</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-xs rounded-md border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white px-2 py-1"
            >
              <option value="created_at">创建时间</option>
              <option value="rice_score">RICE 分数</option>
              <option value="priority">优先级</option>
            </select>
            <button
              onClick={() => setOrder(order === "desc" ? "asc" : "desc")}
              className="text-xs rounded-md border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white px-2 py-1"
            >
              {order === "desc" ? "降序" : "升序"}
            </button>
          </div>

          {isLoading ? (
            <div className="text-center py-8 text-slate-400">加载中...</div>
          ) : requirements.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-3xl mb-2">📋</div>
              <div className="text-slate-500 dark:text-slate-400">暂无需求</div>
              <div className="text-sm text-slate-400 mt-1">添加需求并使用 RICE 模型进行优先级排序</div>
            </div>
          ) : (
            <div className="overflow-auto border rounded-lg dark:border-slate-700">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-700 dark:text-slate-300">需求</th>
                    <th className="px-3 py-2 text-center font-medium text-slate-700 dark:text-slate-300">状态</th>
                    <th className="px-3 py-2 text-center font-medium text-slate-700 dark:text-slate-300">优先级</th>
                    <th className="px-3 py-2 text-center font-medium text-slate-700 dark:text-slate-300">RICE</th>
                    <th className="px-3 py-2 text-center font-medium text-slate-700 dark:text-slate-300">Kano</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-700 dark:text-slate-300">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {requirements.map((r) => (
                    <tr key={r.id} className="border-t dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-3 py-2">
                        <div className="font-medium text-slate-900 dark:text-white">{r.title}</div>
                        {r.description && (
                          <div className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1">{r.description}</div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[r.status] || STATUS_COLORS.backlog}`}>
                          {STATUS_LABELS[r.status] || r.status}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[r.priority] || PRIORITY_COLORS.p2}`}>
                          {r.priority.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <div className="font-semibold text-slate-900 dark:text-white">{r.rice_score.toFixed(1)}</div>
                        <div className="text-[10px] text-slate-400">
                          R{r.rice_reach}·I{r.rice_impact}·C{r.rice_confidence}%·E{r.rice_effort}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${KANO_COLORS[r.kano_category] || KANO_COLORS[""]}`}>
                          {KANO_LABELS[r.kano_category] || "未分类"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => handleEdit(r)} className="text-xs text-slate-400 hover:text-sky-600 px-1">编辑</button>
                          <button onClick={() => handleDelete(r.id)} className="text-xs text-slate-400 hover:text-rose-600 px-1">删除</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Matrix View */}
      {view === "matrix" && (
        <>
          {isLoading ? (
            <div className="text-center py-8 text-slate-400">加载中...</div>
          ) : !matrix || matrix.total === 0 ? (
            <div className="text-center py-8">
              <div className="text-3xl mb-2">📊</div>
              <div className="text-slate-500 dark:text-slate-400">暂无数据</div>
              <div className="text-sm text-slate-400 mt-1">先添加需求才能查看优先级矩阵</div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-lg bg-white border border-slate-200 p-3 dark:bg-slate-800 dark:border-slate-700">
                  <div className="text-xs text-slate-500 dark:text-slate-400">总需求数</div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white">{matrix.total}</div>
                </div>
                <div className="rounded-lg bg-white border border-slate-200 p-3 dark:bg-slate-800 dark:border-slate-700">
                  <div className="text-xs text-slate-500 dark:text-slate-400">最高 RICE</div>
                  <div className="text-xl font-bold text-sky-600 dark:text-sky-400">
                    {matrix.rice_top[0]?.rice_score.toFixed(1) || "0"}
                  </div>
                </div>
                <div className="rounded-lg bg-white border border-slate-200 p-3 dark:bg-slate-800 dark:border-slate-700">
                  <div className="text-xs text-slate-500 dark:text-slate-400">必备型需求</div>
                  <div className="text-xl font-bold text-rose-600 dark:text-rose-400">
                    {matrix.kano_distribution.must_be || 0}
                  </div>
                </div>
                <div className="rounded-lg bg-white border border-slate-200 p-3 dark:bg-slate-800 dark:border-slate-700">
                  <div className="text-xs text-slate-500 dark:text-slate-400">魅力型需求</div>
                  <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
                    {matrix.kano_distribution.attractive || 0}
                  </div>
                </div>
              </div>

              {/* RICE Top */}
              <div>
                <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">
                  RICE 分数 Top {Math.min(matrix.rice_top.length, 10)}
                </h4>
                <div className="space-y-2">
                  {matrix.rice_top.slice(0, 10).map((r, idx) => (
                    <div
                      key={r.id}
                      className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                    >
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-sky-100 text-sky-700 dark:bg-sky-900/20 dark:text-sky-400 flex items-center justify-center text-xs font-bold">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-slate-900 dark:text-white text-sm truncate">{r.title}</div>
                        <div className="text-[10px] text-slate-400">
                          R{r.rice_reach} · I{r.rice_impact} · C{r.rice_confidence}% · E{r.rice_effort} = {r.rice_score.toFixed(1)}
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${KANO_COLORS[r.kano_category] || KANO_COLORS[""]}`}>
                          {KANO_LABELS[r.kano_category] || "未分类"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Kano Distribution */}
              <div>
                <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Kano 分布</h4>
                <div className="space-y-2">
                  {Object.entries(matrix.kano_distribution)
                    .filter(([, count]) => count > 0)
                    .sort(([, a], [, b]) => b - a)
                    .map(([cat, count]) => {
                      const pct = matrix.total > 0 ? (count / matrix.total) * 100 : 0;
                      return (
                        <div key={cat} className="flex items-center gap-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full w-16 text-center ${KANO_COLORS[cat] || KANO_COLORS[""]}`}>
                            {KANO_LABELS[cat] || "未分类"}
                          </span>
                          <div className="flex-1 h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                cat === "must_be"
                                  ? "bg-rose-500"
                                  : cat === "one_dimensional"
                                    ? "bg-amber-500"
                                    : cat === "attractive"
                                      ? "bg-emerald-500"
                                      : cat === "reverse"
                                        ? "bg-violet-500"
                                        : "bg-slate-400"
                              }`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500 dark:text-slate-400 w-12 text-right">
                            {count} ({pct.toFixed(0)}%)
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Kano Groups */}
              {Object.entries(matrix.kano_groups)
                .filter(([, items]) => items.length > 0)
                .map(([cat, items]) => (
                  <div key={cat}>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                      {KANO_LABELS[cat] || "未分类"} ({items.length})
                    </h4>
                    <div className="grid gap-2 md:grid-cols-2">
                      {items.map((r) => (
                        <div
                          key={r.id}
                          className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                        >
                          <div className="flex items-center justify-between">
                            <div className="font-medium text-slate-900 dark:text-white text-sm">{r.title}</div>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLORS[r.priority] || PRIORITY_COLORS.p2}`}>
                              {r.priority.toUpperCase()}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-400 mt-1">
                            RICE: {r.rice_score.toFixed(1)} · {STATUS_LABELS[r.status] || r.status}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">
              {editingId ? "编辑需求" : "新建需求"}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">需求标题 *</label>
                <input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="如：患者端切片借阅申请"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  rows={2}
                  placeholder="需求背景和目标..."
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">状态</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  >
                    <option value="backlog">待办</option>
                    <option value="todo">计划中</option>
                    <option value="in_progress">进行中</option>
                    <option value="done">已完成</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">优先级</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  >
                    <option value="p0">P0 - 最高</option>
                    <option value="p1">P1 - 高</option>
                    <option value="p2">P2 - 中</option>
                  </select>
                </div>
              </div>

              {/* RICE */}
              <div className="rounded-lg bg-slate-50 dark:bg-slate-700/50 p-3 space-y-3">
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">RICE 评分</div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Reach (影响范围 0-1000)</label>
                    <input
                      type="number"
                      min={0}
                      max={1000}
                      value={formData.rice_reach}
                      onChange={(e) => setFormData({ ...formData, rice_reach: Number(e.target.value) })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Impact (影响程度)</label>
                    <select
                      value={formData.rice_impact}
                      onChange={(e) => setFormData({ ...formData, rice_impact: Number(e.target.value) })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
                    >
                      <option value={0.25}>0.25 - 极低</option>
                      <option value={0.5}>0.5 - 低</option>
                      <option value={1}>1 - 中</option>
                      <option value={2}>2 - 高</option>
                      <option value={3}>3 - 极高</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Confidence (信心度 0-100%)</label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={formData.rice_confidence}
                      onChange={(e) => setFormData({ ...formData, rice_confidence: Number(e.target.value) })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Effort (工作量，人月)</label>
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={formData.rice_effort}
                      onChange={(e) => setFormData({ ...formData, rice_effort: Number(e.target.value) })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
                      placeholder="如：1.5"
                    />
                  </div>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  预估 RICE 分数：{formData.rice_effort > 0
                    ? ((formData.rice_reach * formData.rice_impact * (formData.rice_confidence / 100)) / formData.rice_effort).toFixed(1)
                    : "0"}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Kano 分类</label>
                <select
                  value={formData.kano_category}
                  onChange={(e) => setFormData({ ...formData, kano_category: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                >
                  <option value="">未分类</option>
                  <option value="must_be">必备型（Must-be）</option>
                  <option value="one_dimensional">期望型（One-dimensional）</option>
                  <option value="attractive">魅力型（Attractive）</option>
                  <option value="indifferent">无差异型（Indifferent）</option>
                  <option value="reverse">反向型（Reverse）</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={resetForm}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700"
                >
                  保存
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
