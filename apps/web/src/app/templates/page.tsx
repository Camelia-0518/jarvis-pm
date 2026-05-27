"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { projectApi, prdApi, templateApi, type Project, type Template } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";
import { toast } from "sonner";

const COLOR_OPTIONS = [
  { value: "bg-slate-500", label: "灰色", class: "bg-slate-500" },
  { value: "bg-emerald-500", label: "绿色", class: "bg-emerald-500" },
  { value: "bg-sky-500", label: "蓝色", class: "bg-sky-500" },
  { value: "bg-orange-500", label: "橙色", class: "bg-orange-500" },
  { value: "bg-rose-500", label: "红色", class: "bg-rose-500" },
  { value: "bg-violet-500", label: "紫色", class: "bg-violet-500" },
  { value: "bg-amber-500", label: "琥珀", class: "bg-amber-500" },
  { value: "bg-teal-500", label: "青色", class: "bg-teal-500" },
  { value: "bg-indigo-500", label: "靛蓝", class: "bg-indigo-500" },
  { value: "bg-pink-500", label: "粉色", class: "bg-pink-500" },
];

const INDUSTRY_OPTIONS = [
  { value: "other", label: "通用" },
  { value: "medical", label: "医疗" },
  { value: "saas", label: "SaaS" },
  { value: "ecommerce", label: "电商" },
];

export default function TemplatesPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isListLoading, setIsListLoading] = useState(true);

  // Modal states
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);

  // Form states
  const [newProject, setNewProject] = useState({ name: "", description: "" });
  const [templateForm, setTemplateForm] = useState({
    name: "",
    description: "",
    industry: "other",
    icon: "📄",
    color: "bg-slate-500",
    chapters: ["产品概述", "背景与目标", "用户故事", "功能需求"],
  });
  const [chapterInput, setChapterInput] = useState("");

  useEffect(() => {
    loadTemplates();
    projectApi.list().then((res) => setProjects(res.items)).catch(() => setProjects([]));
  }, []);

  const loadTemplates = async () => {
    setIsListLoading(true);
    try {
      const res = await templateApi.list({ limit: 100 });
      setTemplates(res.items);
    } catch {
      setTemplates([]);
    } finally {
      setIsListLoading(false);
    }
  };

  const resetTemplateForm = () => {
    setTemplateForm({
      name: "",
      description: "",
      industry: "other",
      icon: "📄",
      color: "bg-slate-500",
      chapters: ["产品概述", "背景与目标", "用户故事", "功能需求"],
    });
    setChapterInput("");
    setEditingTemplate(null);
  };

  const openCreateModal = () => {
    resetTemplateForm();
    setShowTemplateModal(true);
  };

  const openEditModal = (template: Template) => {
    setEditingTemplate(template);
    setTemplateForm({
      name: template.name,
      description: template.description || "",
      industry: template.industry,
      icon: template.icon,
      color: template.color,
      chapters: [...template.chapters],
    });
    setChapterInput("");
    setShowTemplateModal(true);
  };

  const handleAddChapter = () => {
    const trimmed = chapterInput.trim();
    if (!trimmed) return;
    if (templateForm.chapters.includes(trimmed)) return;
    setTemplateForm({ ...templateForm, chapters: [...templateForm.chapters, trimmed] });
    setChapterInput("");
  };

  const handleRemoveChapter = (index: number) => {
    setTemplateForm({
      ...templateForm,
      chapters: templateForm.chapters.filter((_, i) => i !== index),
    });
  };

  const handleMoveChapter = (index: number, direction: number) => {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= templateForm.chapters.length) return;
    const chapters = [...templateForm.chapters];
    const [moved] = chapters.splice(index, 1);
    chapters.splice(newIndex, 0, moved);
    setTemplateForm({ ...templateForm, chapters });
  };

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!templateForm.name.trim() || templateForm.chapters.length === 0) return;

    setIsLoading(true);
    try {
      if (editingTemplate) {
        await templateApi.update(editingTemplate.id, {
          name: templateForm.name.trim(),
          description: templateForm.description.trim() || undefined,
          industry: templateForm.industry,
          icon: templateForm.icon,
          color: templateForm.color,
          chapters: templateForm.chapters,
        });
      } else {
        await templateApi.create({
          name: templateForm.name.trim(),
          description: templateForm.description.trim() || undefined,
          industry: templateForm.industry,
          icon: templateForm.icon,
          color: templateForm.color,
          chapters: templateForm.chapters,
        });
      }
      setShowTemplateModal(false);
      resetTemplateForm();
      await loadTemplates();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "保存失败";
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const confirmDelete = (template: Template) => {
    setSelectedTemplateId(template.id);
    setShowDeleteConfirm(true);
  };

  const handleDeleteTemplate = async () => {
    if (!selectedTemplateId) return;
    setIsLoading(true);
    try {
      await templateApi.delete(selectedTemplateId);
      setShowDeleteConfirm(false);
      setSelectedTemplateId(null);
      await loadTemplates();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "删除失败";
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseTemplate = async (templateId: string) => {
    if (projects.length === 0) {
      setSelectedTemplateId(templateId);
      setShowProjectModal(true);
      return;
    }
    const project = projects[0];
    try {
      const tmpl = templates.find((t) => t.id === templateId);
      const prd = await prdApi.create({
        project_id: project.id,
        title: `${tmpl?.name || "PRD"}`,
        template: templateId,
      });
      router.push(`/prd/${prd.id}`);
    } catch {
      toast.error("创建失败，请重试");
      router.push(`/workspace?id=${project.id}`);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplateId) return;
    setIsLoading(true);
    try {
      const project = await projectApi.create({
        name: newProject.name,
        description: newProject.description,
        industry: "other",
      });
      const tmpl = templates.find((t) => t.id === selectedTemplateId);
      const prd = await prdApi.create({
        project_id: project.id,
        title: `${tmpl?.name || "PRD"}`,
        template: selectedTemplateId,
      });
      setShowProjectModal(false);
      setSelectedTemplateId(null);
      router.push(`/prd/${prd.id}`);
    } catch {
      toast.error("创建失败，请重试");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <button
          onClick={openCreateModal}
          className="rounded-lg border border-sky-600 px-4 py-2 text-sm font-medium text-sky-600 hover:bg-sky-50 dark:border-sky-500 dark:text-sky-400 dark:hover:bg-sky-950"
        >
          + 新建模板
        </button>
      </NavHeader>

      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">
            浏览模板
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
            选择或创建适合你的 PRD 模板，快速开始产品文档撰写
          </p>
        </div>

        {isListLoading ? (
          <div className="mt-12 text-center text-slate-500">加载中...</div>
        ) : templates.length === 0 ? (
          <div className="mt-12 text-center text-slate-500">
            暂无模板，点击「新建模板」创建第一个模板
          </div>
        ) : (
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {templates.map((template) => (
              <div
                key={template.id}
                className="flex flex-col rounded-xl bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:bg-slate-800"
              >
                <div
                  className={`inline-flex h-12 w-12 items-center justify-center rounded-lg text-2xl text-white ${template.color}`}
                >
                  {template.icon}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-white">
                  {template.name}
                </h3>
                <p className="mt-2 flex-1 text-sm text-slate-600 dark:text-slate-400">
                  {template.description || "暂无描述"}
                </p>
                <div className="mt-4 space-y-1">
                  {template.chapters.slice(0, 4).map((c) => (
                    <div key={c} className="text-xs text-slate-500 dark:text-slate-400">
                      · {c}
                    </div>
                  ))}
                  {template.chapters.length > 4 && (
                    <div className="text-xs text-slate-400">
                      +{template.chapters.length - 4} 章
                    </div>
                  )}
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    {INDUSTRY_OPTIONS.find((i) => i.value === template.industry)?.label || template.industry}
                  </span>
                  {template.is_builtin && (
                    <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-600 dark:bg-sky-900 dark:text-sky-300">
                      内置
                    </span>
                  )}
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => handleUseTemplate(template.id)}
                    className="flex-1 rounded-lg bg-sky-600 py-2 text-sm font-medium text-white hover:bg-sky-700"
                  >
                    使用此模板
                  </button>
                  {!template.is_builtin && (
                    <>
                      <button
                        onClick={() => openEditModal(template)}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                        title="编辑"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => confirmDelete(template)}
                        className="rounded-lg border border-rose-300 px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 dark:border-rose-700 dark:text-rose-400 dark:hover:bg-rose-950"
                        title="删除"
                      >
                        删除
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create/Edit Template Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-white p-6 dark:bg-slate-800">
            <h2 className="mb-4 text-xl font-semibold text-slate-900 dark:text-white">
              {editingTemplate ? "编辑模板" : "新建模板"}
            </h2>
            <form onSubmit={handleSaveTemplate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  模板名称 <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="输入模板名称"
                  required
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  描述
                </label>
                <textarea
                  value={templateForm.description}
                  onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="输入模板描述"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    行业
                  </label>
                  <select
                    value={templateForm.industry}
                    onChange={(e) => setTemplateForm({ ...templateForm, industry: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  >
                    {INDUSTRY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                    图标 (emoji)
                  </label>
                  <input
                    type="text"
                    value={templateForm.icon}
                    onChange={(e) => setTemplateForm({ ...templateForm, icon: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                    placeholder="📄"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  主题色
                </label>
                <div className="flex flex-wrap gap-2">
                  {COLOR_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setTemplateForm({ ...templateForm, color: opt.value })}
                      className={`h-8 w-8 rounded-full ${opt.class} ${templateForm.color === opt.value ? "ring-2 ring-offset-2 ring-slate-400 dark:ring-offset-slate-800" : ""}`}
                      title={opt.label}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  章节列表 <span className="text-rose-500">*</span>
                </label>
                <div className="space-y-2">
                  {templateForm.chapters.map((chapter, index) => (
                    <div
                      key={`${chapter}-${index}`}
                      className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
                    >
                      <span className="flex-1 text-sm text-slate-700 dark:text-slate-300">{chapter}</span>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleMoveChapter(index, -1)}
                          disabled={index === 0}
                          className="rounded px-1.5 py-0.5 text-xs text-slate-500 hover:bg-slate-200 disabled:opacity-30 dark:hover:bg-slate-700"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveChapter(index, 1)}
                          disabled={index === templateForm.chapters.length - 1}
                          className="rounded px-1.5 py-0.5 text-xs text-slate-500 hover:bg-slate-200 disabled:opacity-30 dark:hover:bg-slate-700"
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemoveChapter(index)}
                          className="rounded px-1.5 py-0.5 text-xs text-rose-500 hover:bg-rose-100 dark:hover:bg-rose-950"
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={chapterInput}
                    onChange={(e) => setChapterInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddChapter();
                      }
                    }}
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                    placeholder="输入章节名称，按回车添加"
                  />
                  <button
                    type="button"
                    onClick={handleAddChapter}
                    className="rounded-lg bg-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
                  >
                    添加
                  </button>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowTemplateModal(false); resetTemplateForm(); }}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !templateForm.name.trim() || templateForm.chapters.length === 0}
                  className="flex-1 rounded-lg bg-sky-600 px-4 py-2 text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  {isLoading ? "保存中..." : (editingTemplate ? "保存修改" : "创建模板")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 dark:bg-slate-800">
            <h2 className="mb-2 text-lg font-semibold text-slate-900 dark:text-white">
              确认删除
            </h2>
            <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
              删除后无法恢复，是否继续？
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowDeleteConfirm(false); setSelectedTemplateId(null); }}
                className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                取消
              </button>
              <button
                onClick={handleDeleteTemplate}
                disabled={isLoading}
                className="flex-1 rounded-lg bg-rose-600 px-4 py-2 text-white hover:bg-rose-700 disabled:opacity-50"
              >
                {isLoading ? "删除中..." : "确认删除"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Project Modal */}
      {showProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 dark:bg-slate-800">
            <h2 className="mb-4 text-xl font-semibold text-slate-900 dark:text-white">
              创建项目并使用模板
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              你还没有项目，先创建一个项目，然后自动生成基于 <span className="font-medium text-slate-700">
                {templates.find((t) => t.id === selectedTemplateId)?.name || "选中模板"}
              </span> 的 PRD。
            </p>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  项目名称
                </label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="输入项目名称"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  项目描述
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="输入项目描述"
                  rows={3}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowProjectModal(false); setSelectedTemplateId(null); }}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 rounded-lg bg-sky-600 px-4 py-2 text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  {isLoading ? "创建中..." : "创建并继续"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
