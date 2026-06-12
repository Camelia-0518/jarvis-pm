"use client";

import { useState, useEffect } from "react";
import { personaApi, competitorApi, prdApi, type Persona, type Competitor } from "@/lib/api";

interface Props {
  projectId: string;
  projectName: string;
  projectDescription?: string | null;
  isOpen: boolean;
  onClose: () => void;
  onCreated: (prdId: string) => void;
}

type Step = 1 | 2 | 3 | 4 | 5;

export default function PRDWizard({ projectId, projectName, projectDescription, isOpen, onClose, onCreated }: Props) {
  const [step, setStep] = useState<Step>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Step 1: 需求澄清
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState(projectDescription || "");
  const [template, setTemplate] = useState("default");

  // Step 2: 用户画像
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [selectedPersonas, setSelectedPersonas] = useState<Set<string>>(new Set());
  const [loadingPersonas, setLoadingPersonas] = useState(false);

  // Step 3: 竞品对标
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [selectedCompetitors, setSelectedCompetitors] = useState<Set<string>>(new Set());
  const [loadingCompetitors, setLoadingCompetitors] = useState(false);

  // Step 4: 补充需求
  const [additionalReq, setAdditionalReq] = useState("");

  useEffect(() => {
    if (!isOpen) {
      reset();
      return;
    }
    setTitle("");
    setDescription(projectDescription || "");
    setTemplate("default");
    setStep(1);
    setError("");
  }, [isOpen, projectDescription]);

  useEffect(() => {
    if (step === 2 && projectId) {
      setLoadingPersonas(true);
      personaApi.list(projectId)
        .then((res) => { setPersonas(res || []); })
        .catch(() => setPersonas([]))
        .finally(() => setLoadingPersonas(false));
    }
    if (step === 3 && projectId) {
      setLoadingCompetitors(true);
      competitorApi.list(projectId)
        .then((res) => { setCompetitors(res || []); })
        .catch(() => setCompetitors([]))
        .finally(() => setLoadingCompetitors(false));
    }
  }, [step, projectId]);

  const reset = () => {
    setStep(1);
    setTitle("");
    setDescription("");
    setTemplate("default");
    setPersonas([]);
    setSelectedPersonas(new Set());
    setCompetitors([]);
    setSelectedCompetitors(new Set());
    setAdditionalReq("");
    setError("");
    setIsSubmitting(false);
  };

  const canNext = () => {
    switch (step) {
      case 1: return title.trim().length > 0;
      case 2: return true; // personas 可选
      case 3: return true; // competitors 可选
      case 4: return true;
      default: return false;
    }
  };

  const handleNext = () => {
    if (step < 5) setStep((s) => (s + 1) as Step);
  };

  const handleBack = () => {
    if (step > 1) setStep((s) => (s - 1) as Step);
  };

  const handleCreate = async () => {
    if (!projectId) {
      setError("项目 ID 缺失");
      return;
    }
    setIsSubmitting(true);
    setError("");
    try {
      const prd = await prdApi.create({
        project_id: projectId,
        title: title.trim(),
        template,
      });
      // 如果有补充需求，更新 PRD 内容
      if (additionalReq.trim()) {
        try {
          await prdApi.update(prd.id, {
            markdown: `# ${title.trim()}\n\n## 补充需求\n\n${additionalReq.trim()}\n`,
          });
        } catch {
          // ignore update error
        }
      }
      onCreated(prd.id);
      reset();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "创建失败";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const steps = [
    { num: 1, label: "需求澄清" },
    { num: 2, label: "用户画像" },
    { num: 3, label: "竞品对标" },
    { num: 4, label: "补充需求" },
    { num: 5, label: "确认创建" },
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">新建 PRD</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            {steps.map((s, idx) => (
              <div key={s.num} className="flex items-center gap-2">
                <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium ${
                  s.num === step
                    ? "bg-sky-600 text-white"
                    : s.num < step
                      ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                      : "bg-slate-100 text-slate-400 dark:bg-slate-700"
                }`}>
                  {s.num < step ? "✓" : s.num}
                </div>
                <span className={`text-xs ${s.num === step ? "text-sky-600 font-medium" : "text-slate-400"}`}>
                  {s.label}
                </span>
                {idx < steps.length - 1 && (
                  <div className={`w-6 h-px ${s.num < step ? "bg-sky-300" : "bg-slate-200 dark:bg-slate-700"}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Step 1: 需求澄清 */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">项目名称</label>
                <div className="px-3 py-2 rounded-lg bg-slate-50 text-slate-600 dark:bg-slate-700 dark:text-slate-300 text-sm">{projectName}</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  PRD 标题 <span className="text-rose-500">*</span>
                </label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="如：切片借阅平台 PRD"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">项目描述（可修改）</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  rows={3}
                  placeholder="简要描述项目目标和范围..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">模板</label>
                <select
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                >
                  <option value="default">默认模板（8章）</option>
                  <option value="medical">医疗行业模板</option>
                  <option value="saas">SaaS 产品模板</option>
                  <option value="ecommerce">电商产品模板</option>
                </select>
              </div>
            </div>
          )}

          {/* Step 2: 用户画像 */}
          {step === 2 && (
            <div className="space-y-3">
              <p className="text-sm text-slate-500 dark:text-slate-400">选择本次 PRD 需要重点考虑的用户角色（可多选）：</p>
              {loadingPersonas ? (
                <div className="text-center py-8 text-slate-400">加载中...</div>
              ) : personas.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-3xl mb-2">👤</div>
                  <div className="text-slate-500 dark:text-slate-400">暂无用户画像</div>
                  <div className="text-sm text-slate-400 mt-1">先去&ldquo;用户画像&rdquo;标签页添加角色</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {personas.map((p) => (
                    <label key={p.id} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedPersonas.has(p.id)
                        ? "border-sky-300 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                        : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700"
                    }`}>
                      <input
                        type="checkbox"
                        checked={selectedPersonas.has(p.id)}
                        onChange={(e) => {
                          const next = new Set(selectedPersonas);
                          if (e.target.checked) next.add(p.id);
                          else next.delete(p.id);
                          setSelectedPersonas(next);
                        }}
                        className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600"
                      />
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white">{p.name}</div>
                        <div className="text-xs text-sky-600 bg-sky-50 dark:bg-sky-900/20 px-1.5 py-0.5 rounded inline-block mt-0.5">{p.role}</div>
                        {p.pain_points && <div className="text-xs text-slate-500 mt-1">痛点：{p.pain_points}</div>}
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 3: 竞品对标 */}
          {step === 3 && (
            <div className="space-y-3">
              <p className="text-sm text-slate-500 dark:text-slate-400">选择本次 PRD 需要参考的竞品（可多选）：</p>
              {loadingCompetitors ? (
                <div className="text-center py-8 text-slate-400">加载中...</div>
              ) : competitors.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-3xl mb-2">⚔️</div>
                  <div className="text-slate-500 dark:text-slate-400">暂无竞品信息</div>
                  <div className="text-sm text-slate-400 mt-1">先去&ldquo;竞品信息&rdquo;标签页添加竞品</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {competitors.map((c) => (
                    <label key={c.id} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedCompetitors.has(c.id)
                        ? "border-sky-300 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                        : "border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-700"
                    }`}>
                      <input
                        type="checkbox"
                        checked={selectedCompetitors.has(c.id)}
                        onChange={(e) => {
                          const next = new Set(selectedCompetitors);
                          if (e.target.checked) next.add(c.id);
                          else next.delete(c.id);
                          setSelectedCompetitors(next);
                        }}
                        className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600"
                      />
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white">{c.name}</div>
                        {c.market_position && <div className="text-xs text-slate-500">{c.market_position}</div>}
                        {c.strengths && <div className="text-xs text-emerald-600 mt-1">优势：{c.strengths}</div>}
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 4: 补充需求 */}
          {step === 4 && (
            <div className="space-y-4">
              <p className="text-sm text-slate-500 dark:text-slate-400">补充 PRD 中需要特别说明的需求或约束：</p>
              <textarea
                value={additionalReq}
                onChange={(e) => setAdditionalReq(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                rows={8}
                placeholder="如：&#10;- 必须支持多院区部署&#10;- 患者端必须使用微信小程序&#10;- 对接医院现有 HIS 系统&#10;- 等保三级合规要求"
              />
            </div>
          )}

          {/* Step 5: 确认创建 */}
          {step === 5 && (
            <div className="space-y-4">
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700">
                <h4 className="font-medium text-slate-900 dark:text-white mb-2">PRD 信息</h4>
                <div className="text-sm space-y-1 text-slate-600 dark:text-slate-300">
                  <div><span className="text-slate-400">标题：</span>{title}</div>
                  <div><span className="text-slate-400">模板：</span>{template}</div>
                  <div><span className="text-slate-400">项目：</span>{projectName}</div>
                </div>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700">
                <h4 className="font-medium text-slate-900 dark:text-white mb-2">已选用户画像（{selectedPersonas.size}）</h4>
                {selectedPersonas.size === 0 ? (
                  <div className="text-sm text-slate-400">未选择（AI 将使用通用用户分析）</div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {personas.filter((p) => selectedPersonas.has(p.id)).map((p) => (
                      <span key={p.id} className="text-xs bg-sky-100 text-sky-700 px-2 py-0.5 rounded-full dark:bg-sky-900/30 dark:text-sky-400">{p.name}</span>
                    ))}
                  </div>
                )}
              </div>
              <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700">
                <h4 className="font-medium text-slate-900 dark:text-white mb-2">已选竞品（{selectedCompetitors.size}）</h4>
                {selectedCompetitors.size === 0 ? (
                  <div className="text-sm text-slate-400">未选择（AI 将使用通用竞品分析）</div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {competitors.filter((c) => selectedCompetitors.has(c.id)).map((c) => (
                      <span key={c.id} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full dark:bg-amber-900/30 dark:text-amber-400">{c.name}</span>
                    ))}
                  </div>
                )}
              </div>
              {additionalReq.trim() && (
                <div className="rounded-lg bg-slate-50 p-4 dark:bg-slate-700">
                  <h4 className="font-medium text-slate-900 dark:text-white mb-2">补充需求</h4>
                  <div className="text-sm text-slate-600 dark:text-slate-300 whitespace-pre-wrap">{additionalReq}</div>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="mt-4 text-sm text-rose-600 dark:text-rose-400">{error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-between">
          <button
            onClick={step === 1 ? onClose : handleBack}
            className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            {step === 1 ? "取消" : "上一步"}
          </button>
          {step < 5 ? (
            <button
              onClick={handleNext}
              disabled={!canNext()}
              className="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一步
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50"
            >
              {isSubmitting ? "创建中..." : "确认创建"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
