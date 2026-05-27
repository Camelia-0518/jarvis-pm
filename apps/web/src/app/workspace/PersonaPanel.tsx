"use client";

import { useState, useEffect } from "react";
import { personaApi, type Persona } from "@/lib/api";
import { toast } from "sonner";
import { confirm } from "@/components/ui/ConfirmDialog";

interface Props {
  projectId: string;
}

export default function PersonaPanel({ projectId }: Props) {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    role: "",
    description: "",
    pain_points: "",
    goals: "",
    scenarios: "",
    demographics: "",
  });

  const loadPersonas = async () => {
    setIsLoading(true);
    try {
      const res = await personaApi.list(projectId);
      setPersonas(res || []);
    } catch {
      setPersonas([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPersonas();
  }, [projectId]);

  const resetForm = () => {
    setFormData({ name: "", role: "", description: "", pain_points: "", goals: "", scenarios: "", demographics: "" });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.role.trim()) return;
    try {
      if (editingId) {
        await personaApi.update(editingId, formData);
      } else {
        await personaApi.create(projectId, formData);
      }
      resetForm();
      loadPersonas();
    } catch {
      toast.error("保存失败，请重试");
    }
  };

  const handleEdit = (p: Persona) => {
    setFormData({
      name: p.name,
      role: p.role,
      description: p.description || "",
      pain_points: p.pain_points || "",
      goals: p.goals || "",
      scenarios: p.scenarios || "",
      demographics: p.demographics || "",
    });
    setEditingId(p.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    const confirmed = await confirm({
      title: "删除用户画像",
      message: "确定删除该用户画像？",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await personaApi.delete(id);
      loadPersonas();
    } catch {
      toast.error("删除失败");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">用户画像</h3>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
        >
          + 新建画像
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-slate-400">加载中...</div>
      ) : personas.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-3xl mb-2">👤</div>
          <div className="text-slate-500 dark:text-slate-400">暂无用户画像</div>
          <div className="text-sm text-slate-400 mt-1">添加目标用户角色，让 AI 生成更贴合实际</div>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {personas.map((p) => (
            <div key={p.id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-medium text-slate-900 dark:text-white">{p.name}</h4>
                  <span className="text-xs text-sky-600 bg-sky-50 dark:bg-sky-900/20 px-2 py-0.5 rounded-full">{p.role}</span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => handleEdit(p)} className="text-sm text-slate-400 hover:text-sky-600">编辑</button>
                  <button onClick={() => handleDelete(p.id)} className="text-sm text-slate-400 hover:text-rose-600">删除</button>
                </div>
              </div>
              {p.description && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{p.description}</p>}
              {p.pain_points && (
                <div className="mt-2">
                  <span className="text-xs font-medium text-rose-600">痛点：</span>
                  <span className="text-xs text-slate-500">{p.pain_points}</span>
                </div>
              )}
              {p.goals && (
                <div className="mt-1">
                  <span className="text-xs font-medium text-emerald-600">目标：</span>
                  <span className="text-xs text-slate-500">{p.goals}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">
              {editingId ? "编辑用户画像" : "新建用户画像"}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">角色名称 *</label>
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" placeholder="如：门诊医生" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">角色类型 *</label>
                <input value={formData.role} onChange={(e) => setFormData({ ...formData, role: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" placeholder="如：医生 / 护士 / 患者" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">角色描述</label>
                <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="该角色的基本背景..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">痛点</label>
                <textarea value={formData.pain_points} onChange={(e) => setFormData({ ...formData, pain_points: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="该角色面临的主要问题..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">目标</label>
                <textarea value={formData.goals} onChange={(e) => setFormData({ ...formData, goals: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="该角色希望通过产品实现什么..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">使用场景</label>
                <textarea value={formData.scenarios} onChange={(e) => setFormData({ ...formData, scenarios: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="何时、何地、什么情况下使用..." />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={resetForm} className="flex-1 px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700">取消</button>
                <button type="submit" className="flex-1 px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700">保存</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
