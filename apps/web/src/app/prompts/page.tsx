"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePromptStore } from "@/stores/promptStore";
import NavHeader from "@/components/global/NavHeader";
import { toast } from "sonner";
import { confirm } from "@/components/ui/ConfirmDialog";

export default function PromptsPage() {
  const { prompts, versions, isLoading, error, fetchPrompts, fetchVersions, createPrompt, activatePrompt, deletePrompt, clearError } = usePromptStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [newPrompt, setNewPrompt] = useState({
    name: "",
    content: "",
    version: "1.0",
    description: "",
    tags: "",
  });

  useEffect(() => {
    fetchPrompts();
  }, [fetchPrompts]);

  useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createPrompt({
        name: newPrompt.name,
        content: newPrompt.content,
        version: newPrompt.version,
        description: newPrompt.description || undefined,
        tags: newPrompt.tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setShowCreateModal(false);
      setNewPrompt({ name: "", content: "", version: "1.0", description: "", tags: "" });
      toast.success("提示词创建成功");
    } catch {
      toast.error("创建提示词失败");
    }
  };

  const handleActivate = async (id: string) => {
    try {
      await activatePrompt(id);
      toast.success("提示词已激活");
    } catch {
      toast.error("激活失败");
    }
  };

  const handleDelete = async (id: string) => {
    const confirmed = await confirm({
      title: "删除提示词",
      message: "确定要删除此提示词版本吗？",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await deletePrompt(id);
      toast.success("提示词已删除");
    } catch {
      toast.error("删除失败");
    }
  };

  const handleViewVersions = async (name: string) => {
    setSelectedName(name);
    await fetchVersions(name);
  };

  // Group prompts by name
  const promptGroups = prompts.reduce((acc, prompt) => {
    if (!acc[prompt.name]) acc[prompt.name] = [];
    acc[prompt.name].push(prompt);
    return acc;
  }, {} as Record<string, typeof prompts>);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
        >
          + 新建提示词
        </button>
      </NavHeader>

      {/* Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {isLoading ? (
          <div className="text-center py-12 text-slate-400">加载中...</div>
        ) : Object.keys(promptGroups).length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">📝</div>
            <div className="text-slate-600 dark:text-slate-300">暂无提示词</div>
            <div className="text-sm text-slate-400 mt-2">创建你的第一个提示词模板</div>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(promptGroups).map(([name, groupPrompts]) => (
              <div key={name} className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{name}</h2>
                    <p className="text-sm text-slate-500">
                      {groupPrompts.length} 个版本 · 当前激活: {groupPrompts.find((p) => p.is_active)?.version || "无"}
                    </p>
                  </div>
                  <button
                    onClick={() => handleViewVersions(name)}
                    className="text-sm text-sky-600 hover:text-sky-700 dark:text-sky-400"
                  >
                    查看版本
                  </button>
                </div>

                <div className="space-y-2">
                  {groupPrompts.slice(0, 3).map((prompt) => (
                    <div
                      key={prompt.id}
                      className={`flex items-center justify-between p-3 rounded-lg border ${
                        prompt.is_active
                          ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20"
                          : "border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                          prompt.is_active
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
                        }`}>
                          v{prompt.version}
                        </span>
                        <span className="text-sm text-slate-600 dark:text-slate-300">
                          {prompt.description || "暂无描述"}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {!prompt.is_active && (
                          <button
                            onClick={() => handleActivate(prompt.id)}
                            className="text-xs text-sky-600 hover:text-sky-700 dark:text-sky-400"
                          >
                            激活
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(prompt.id)}
                          className="text-xs text-rose-600 hover:text-rose-700 dark:text-rose-400"
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">新建提示词</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <form onSubmit={handleCreate} className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">名称</label>
                <input
                  value={newPrompt.name}
                  onChange={(e) => setNewPrompt({ ...newPrompt, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="例如：prd_generator_system"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">版本</label>
                <input
                  value={newPrompt.version}
                  onChange={(e) => setNewPrompt({ ...newPrompt, version: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="1.0"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">描述</label>
                <input
                  value={newPrompt.description}
                  onChange={(e) => setNewPrompt({ ...newPrompt, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="提示词的简要描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">标签（用逗号分隔）</label>
                <input
                  value={newPrompt.tags}
                  onChange={(e) => setNewPrompt({ ...newPrompt, tags: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="agent, system, prd"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">内容</label>
                <textarea
                  value={newPrompt.content}
                  onChange={(e) => setNewPrompt({ ...newPrompt, content: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white font-mono text-sm"
                  rows={12}
                  placeholder="在此输入提示词内容..."
                  required
                />
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  {isLoading ? "创建中..." : "创建"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Versions Modal */}
      {selectedName && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">版本历史：{selectedName}</h2>
              <button onClick={() => setSelectedName(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-3">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className={`p-4 rounded-lg border ${
                    v.is_active
                      ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20"
                      : "border-slate-200 dark:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                        v.is_active
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-100 text-slate-600"
                      }`}>
                        v{v.version} {v.is_active && "（已激活）"}
                      </span>
                      <span className="text-xs text-slate-400">{v.created_at?.split("T")[0]}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {!v.is_active && (
                        <button
                          onClick={() => handleActivate(v.id)}
                          className="text-xs text-sky-600 hover:text-sky-700"
                        >
                          Activate
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(v.id)}
                        className="text-xs text-rose-600 hover:text-rose-700"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-300 mb-2">{v.description || "No description"}</p>
                  <pre className="text-xs bg-slate-100 dark:bg-slate-900 p-2 rounded overflow-x-auto text-slate-700 dark:text-slate-300">
                    {v.content.slice(0, 200)}{v.content.length > 200 ? "..." : ""}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
