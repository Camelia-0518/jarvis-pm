"use client";

import { useState, useEffect } from "react";
import { competitorApi, type Competitor } from "@/lib/api";
import { toast } from "sonner";
import { confirm } from "@/components/ui/ConfirmDialog";

interface Props {
  projectId: string;
}

export default function CompetitorPanel({ projectId }: Props) {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    strengths: "",
    weaknesses: "",
    features: "" as string,
    pricing: "",
    market_position: "",
    source: "",
  });

  const loadCompetitors = async () => {
    setIsLoading(true);
    try {
      const res = await competitorApi.list(projectId);
      setCompetitors(res || []);
    } catch {
      setCompetitors([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCompetitors();
  }, [projectId]);

  const resetForm = () => {
    setFormData({ name: "", description: "", strengths: "", weaknesses: "", features: "", pricing: "", market_position: "", source: "" });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    try {
      const payload = {
        ...formData,
        features: formData.features ? formData.features.split("\n").filter((f) => f.trim()) : [],
      };
      if (editingId) {
        await competitorApi.update(editingId, payload);
      } else {
        await competitorApi.create(projectId, payload);
      }
      resetForm();
      loadCompetitors();
    } catch {
      toast.error("保存失败，请重试");
    }
  };

  const handleEdit = (c: Competitor) => {
    setFormData({
      name: c.name,
      description: c.description || "",
      strengths: c.strengths || "",
      weaknesses: c.weaknesses || "",
      features: (c.features || []).join("\n"),
      pricing: c.pricing || "",
      market_position: c.market_position || "",
      source: c.source || "",
    });
    setEditingId(c.id);
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    const confirmed = await confirm({
      title: "删除竞品",
      message: "确定删除该竞品信息？",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await competitorApi.delete(id);
      loadCompetitors();
    } catch {
      toast.error("删除失败");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">竞品信息</h3>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700"
        >
          + 新建竞品
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-slate-400">加载中...</div>
      ) : competitors.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-3xl mb-2">⚔️</div>
          <div className="text-slate-500 dark:text-slate-400">暂无竞品信息</div>
          <div className="text-sm text-slate-400 mt-1">添加竞品信息，让 AI 生成时有对标参考</div>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {competitors.map((c) => (
            <div key={c.id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-medium text-slate-900 dark:text-white">{c.name}</h4>
                  {c.market_position && <span className="text-xs text-slate-500">{c.market_position}</span>}
                </div>
                <div className="flex gap-1">
                  <button onClick={() => handleEdit(c)} className="text-sm text-slate-400 hover:text-sky-600">编辑</button>
                  <button onClick={() => handleDelete(c.id)} className="text-sm text-slate-400 hover:text-rose-600">删除</button>
                </div>
              </div>
              {c.description && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{c.description}</p>}
              {c.strengths && (
                <div className="mt-2">
                  <span className="text-xs font-medium text-emerald-600">优势：</span>
                  <span className="text-xs text-slate-500">{c.strengths}</span>
                </div>
              )}
              {c.weaknesses && (
                <div className="mt-1">
                  <span className="text-xs font-medium text-rose-600">劣势：</span>
                  <span className="text-xs text-slate-500">{c.weaknesses}</span>
                </div>
              )}
              {c.features && c.features.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {c.features.map((f, i) => (
                    <span key={i} className="text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full text-slate-600 dark:text-slate-300">{f}</span>
                  ))}
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
              {editingId ? "编辑竞品" : "新建竞品"}
            </h3>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">竞品名称 *</label>
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" placeholder="如：阿里健康" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">描述</label>
                <textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="竞品的基本介绍..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">优势</label>
                <textarea value={formData.strengths} onChange={(e) => setFormData({ ...formData, strengths: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="竞品的核心优势..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">劣势</label>
                <textarea value={formData.weaknesses} onChange={(e) => setFormData({ ...formData, weaknesses: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={2} placeholder="竞品的不足..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">功能列表（每行一个）</label>
                <textarea value={formData.features} onChange={(e) => setFormData({ ...formData, features: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" rows={3} placeholder="功能1&#10;功能2&#10;功能3" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">定价信息</label>
                <input value={formData.pricing} onChange={(e) => setFormData({ ...formData, pricing: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" placeholder="如：免费 / 99元/月" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">市场定位</label>
                <input value={formData.market_position} onChange={(e) => setFormData({ ...formData, market_position: e.target.value })} className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white" placeholder="如：高端市场 / 下沉市场" />
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
