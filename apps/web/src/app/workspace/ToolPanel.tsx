"use client";

import { useState } from "react";
import { toolsApi, ragApi, prdApi, type PRDSummary } from "@/lib/api";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  toolId: string;
  projectId: string | null;
  prds: PRDSummary[];
}

export default function ToolPanel({ toolId, projectId, prds }: Props) {
  const [result, setResult] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [appendSuccess, setAppendSuccess] = useState(false);
  const [appendError, setAppendError] = useState("");

  const [pendingCandidates, setPendingCandidates] = useState<Array<{ name: string; description: string; source_detail?: string; checked?: boolean }>>([]);
  const [showCandidatePanel, setShowCandidatePanel] = useState(false);
  const [pendingCompetitorParams, setPendingCompetitorParams] = useState<Record<string, string>>({});

  const defaultParams: Record<string, Record<string, string>> = {
    research: { target_audience: "主要用户群体" },
    stakeholder: {},
    competitor: { competitors_text: "主要竞品A\n主要竞品B" },
    data: { metrics_text: "日活跃用户\n转化率\n留存率" },
    review: { material_type: "agenda" },
    prototype: { feature_description: "核心功能原型" },
    memory: { query: "", source_type: "prd" },
  };

  const [params, setParams] = useState<Record<string, string>>(defaultParams[toolId] || {});

  const [dataFile, setDataFile] = useState<File | null>(null);
  const [dataPreview, setDataPreview] = useState<Record<string, string>[]>([]);
  const [dataMode, setDataMode] = useState<"text" | "upload">("upload");
  const [fileError, setFileError] = useState<string>("");

  const parseCsvLine = (line: string): string[] => {
    const result: string[] = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const nextChar = line[i + 1];
      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = "";
      } else {
        current += char;
      }
    }
    result.push(current.trim());
    return result;
  };

  const extractPreviewRows = async (file: File, limit: number): Promise<Record<string, string>[]> => {
    const text = await file.text();
    const lines = text.split("\n").filter((l) => l.trim());
    if (lines.length === 0) return [];
    const headers = parseCsvLine(lines[0]).map((h) => h.replace(/^﻿/, ""));
    const rows: Record<string, string>[] = [];
    for (let i = 1; i < Math.min(lines.length, limit + 1); i++) {
      const values = parseCsvLine(lines[i]);
      const row: Record<string, string> = {};
      headers.forEach((h, idx) => {
        row[h] = values[idx] || "";
      });
      rows.push(row);
    }
    return rows;
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    const allowedExtensions = [".csv"];
    const isValidExt = allowedExtensions.some((ext) => selected.name.toLowerCase().endsWith(ext));
    if (!isValidExt) {
      setFileError("暂仅支持 .csv 文件，.xlsx 支持即将上线");
      setDataFile(null);
      setDataPreview([]);
      return;
    }
    if (selected.size > 5 * 1024 * 1024) {
      setFileError("文件大小不能超过 5MB");
      setDataFile(null);
      setDataPreview([]);
      return;
    }
    setFileError("");
    setDataFile(selected);
    const preview = await extractPreviewRows(selected, 5);
    setDataPreview(preview);
  };

  const handleToolAction = async () => {
    if (!projectId) return;
    setIsLoading(true);
    setResult(null);
    try {
      let res: unknown;
      switch (toolId) {
        case "research":
          res = await toolsApi.userResearch({
            project_id: projectId,
            research_type: "interview",
            target_audience: (params.target_audience as string) || "主要用户群体",
          });
          break;
        case "stakeholder":
          res = await toolsApi.stakeholderAnalysis({
            project_id: projectId,
          });
          break;
        case "competitor": {
          const competitorNames = ((params.competitors_text as string) || "")
            .split("\n")
            .map((s: string) => s.trim())
            .filter(Boolean);
          res = await toolsApi.competitorAnalysis({
            project_id: projectId,
            competitors: competitorNames,
          });
          if (res && typeof res === 'object' && 'needs_confirmation' in res && (res as Record<string, unknown>).needs_confirmation === true) {
            const candidates = (res as Record<string, unknown>).candidates as Array<{ name: string; description: string; source_detail?: string }> || [];
            setPendingCandidates(candidates.map(c => ({ ...c, checked: true })));
            setPendingCompetitorParams({ competitors_text: params.competitors_text || "" });
            setShowCandidatePanel(true);
            setIsLoading(false);
            return;
          }
          break;
        }
        case "data":
          if (dataMode === "upload" && dataFile) {
            const formData = new FormData();
            formData.append("file", dataFile);
            formData.append("project_id", projectId);
            res = await toolsApi.dataAnalysisUpload(formData);
          } else {
            res = await toolsApi.dataAnalysis({
              project_id: projectId,
              data_source: "业务数据库",
              metrics: ((params.metrics_text as string) || "")
                .split("\n")
                .map((s: string) => s.trim())
                .filter(Boolean),
            });
          }
          break;
        case "review":
          res = await toolsApi.reviewMaterials({
            project_id: projectId,
            material_type: (params.material_type as string) || "agenda",
          });
          break;
        case "prototype":
          res = await toolsApi.prototype({
            project_id: projectId,
            feature_description: (params.feature_description as string) || "核心功能原型",
          });
          break;
        case "memory":
          res = await ragApi.memorySearch({
            query: (params.query as string) || "",
            top_k: 5,
            source_type: (params.source_type as string) || undefined,
          });
          break;
        default:
          res = { message: "未知工具" };
      }
      setResult(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "请求失败";
      setResult({ error: message });
    } finally {
      setIsLoading(false);
    }
  };

  const toolLabels: Record<string, string> = {
    research: "生成用户研究报告",
    stakeholder: "生成干系人分析",
    competitor: "生成竞品分析",
    data: dataMode === "upload" ? "上传并分析数据" : "生成数据分析",
    review: "生成评审议程",
    prototype: "生成原型设计",
    memory: "语义检索",
  };

  const canRun = !isLoading && !(toolId === "data" && dataMode === "upload" && !dataFile) && !(toolId === "memory" && !(params.query as string)?.trim());

  return (
    <div>
      <p className="text-slate-600 dark:text-slate-400 mb-4">
        使用此工具辅助产品分析和设计工作。
      </p>

      {toolId === "research" && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">目标用户</label>
          <textarea
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
            rows={3}
            value={params.target_audience}
            onChange={(e) => setParams({ ...params, target_audience: e.target.value })}
            placeholder="描述目标用户群体"
          />
        </div>
      )}

      {toolId === "competitor" && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">竞品名称（每行一个）</label>
          <textarea
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
            rows={3}
            value={params.competitors_text}
            onChange={(e) => setParams({ ...params, competitors_text: e.target.value })}
            placeholder="竞品A\n竞品B"
          />
        </div>
      )}

      {toolId === "data" && (
        <div className="mb-4 space-y-3">
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input type="radio" name="data-mode" checked={dataMode === "upload"} onChange={() => setDataMode("upload")} />
              上传 CSV 分析
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input type="radio" name="data-mode" checked={dataMode === "text"} onChange={() => setDataMode("text")} />
              指标框架分析
            </label>
          </div>

          {dataMode === "upload" ? (
            <div className="space-y-3">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-600 dark:text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-sky-50 file:text-sky-600 hover:file:bg-sky-100"
              />
              {fileError && <div className="text-sm text-rose-600 dark:text-rose-400">{fileError}</div>}
              {dataPreview.length > 0 && (
                <div className="overflow-auto border rounded dark:border-slate-600">
                  <table className="text-sm w-full">
                    <thead className="bg-slate-50 dark:bg-slate-800">
                      <tr>
                        {Object.keys(dataPreview[0]).map((k) => (
                          <th key={k} className="px-2 py-1 border-b dark:border-slate-600 text-left font-medium text-slate-700 dark:text-slate-300">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dataPreview.map((row, i) => (
                        <tr key={i}>
                          {Object.values(row).map((v, j) => (
                            <td key={j} className="px-2 py-1 border-b dark:border-slate-600 text-slate-700 dark:text-slate-300">{String(v)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-2 py-1 text-xs text-slate-500 dark:text-slate-400">仅展示前 5 行预览</div>
                </div>
              )}
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">分析指标（每行一个）</label>
              <textarea
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
                rows={3}
                value={params.metrics_text}
                onChange={(e) => setParams({ ...params, metrics_text: e.target.value })}
                placeholder="日活跃用户\n转化率\n留存率"
              />
            </div>
          )}
        </div>
      )}

      {toolId === "review" && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">材料类型</label>
          <select
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
            value={params.material_type}
            onChange={(e) => setParams({ ...params, material_type: e.target.value })}
          >
            <option value="agenda">评审议程</option>
            <option value="qa">预设 Q&A</option>
            <option value="risks">风险预案</option>
          </select>
        </div>
      )}

      {toolId === "prototype" && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">功能描述</label>
          <textarea
            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
            rows={3}
            value={params.feature_description}
            onChange={(e) => setParams({ ...params, feature_description: e.target.value })}
            placeholder="描述需要设计原型的核心功能"
          />
        </div>
      )}

      {toolId === "memory" && (
        <div className="mb-4 space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">检索内容</label>
            <textarea
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
              rows={3}
              value={params.query}
              onChange={(e) => setParams({ ...params, query: e.target.value })}
              placeholder="输入自然语言查询，例如：医疗行业的用户登录流程"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">来源过滤</label>
            <select
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
              value={params.source_type}
              onChange={(e) => setParams({ ...params, source_type: e.target.value })}
            >
              <option value="">全部来源</option>
              <option value="prd">PRD 文档</option>
              <option value="project">项目信息</option>
              <option value="knowledge">知识库</option>
            </select>
          </div>
        </div>
      )}

      <button
        onClick={handleToolAction}
        disabled={!canRun}
        className="w-full py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50"
      >
        {isLoading ? "执行中..." : toolLabels[toolId] || "开始分析"}
      </button>

      {isLoading && (
        <div className="mt-4 p-4 rounded-lg bg-sky-50 dark:bg-sky-900/20 border border-sky-200 dark:border-sky-800">
          <div className="flex items-center gap-3">
            <div className="animate-spin h-5 w-5 border-2 border-sky-600 border-t-transparent rounded-full" />
            <div>
              <p className="text-sm font-medium text-sky-800 dark:text-sky-200">AI 正在生成内容...</p>
              <p className="text-xs text-sky-600 dark:text-sky-400 mt-0.5">预计需要 30-60 秒，请耐心等待，不要刷新页面</p>
            </div>
          </div>
        </div>
      )}

      {/* Candidate Confirmation Panel */}
      {showCandidatePanel && toolId === "competitor" && (
        <div className="mt-4 p-4 rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800">
          <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-100 mb-2">⏳ 候选竞品确认</h3>
          <p className="text-xs text-amber-700 dark:text-amber-300 mb-3">
            网络搜索未返回结果，以下竞品由 AI 推断生成。请勾选确认准确的竞品：
          </p>
          <div className="space-y-2 mb-4">
            {pendingCandidates.map((c, idx) => (
              <label key={idx} className="flex items-start gap-2 p-2 rounded bg-white dark:bg-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700">
                <input
                  type="checkbox"
                  checked={c.checked}
                  onChange={(e) => {
                    const next = [...pendingCandidates];
                    next[idx].checked = e.target.checked;
                    setPendingCandidates(next);
                  }}
                  className="mt-0.5"
                />
                <div className="text-sm">
                  <div className="font-medium text-slate-800 dark:text-slate-200">{c.name}</div>
                  <div className="text-slate-500 dark:text-slate-400 text-xs">{c.description}</div>
                </div>
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={async () => {
                const confirmed = pendingCandidates.filter(c => c.checked);
                if (confirmed.length === 0) {
                  toast.error("请至少确认一个竞品");
                  return;
                }
                setIsLoading(true);
                try {
                  if (!projectId) return;
                  const res = await toolsApi.confirmCompetitorAnalysis({
                    project_id: projectId,
                    competitors: ((pendingCompetitorParams.competitors_text as string) || "")
                      .split("\n")
                      .map((s: string) => s.trim())
                      .filter(Boolean),
                    confirmed_candidates: confirmed.map(c => ({ name: c.name, description: c.description })),
                  });
                  setResult(res);
                  setShowCandidatePanel(false);
                  setPendingCandidates([]);
                } catch (err: unknown) {
                  setResult({ error: err instanceof Error ? err.message : "确认失败" });
                } finally {
                  setIsLoading(false);
                }
              }}
              disabled={isLoading}
              className="px-3 py-1.5 rounded bg-sky-600 text-white text-sm font-medium hover:bg-sky-700 disabled:opacity-50"
            >
              {isLoading ? "生成中..." : "确认并生成报告"}
            </button>
            <button
              onClick={() => { setShowCandidatePanel(false); setPendingCandidates([]); }}
              className="px-3 py-1.5 rounded border border-slate-300 text-slate-700 text-sm hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {result !== null && result !== undefined && (
        <div className="mt-4 p-4 rounded-lg bg-slate-50 dark:bg-slate-700 overflow-auto max-h-[60vh]">
          {toolId === "memory" && typeof result === 'object' && result !== null && 'results' in result ? (
            <div className="space-y-3">
              {(result as Record<string, unknown>).results && Array.isArray((result as Record<string, unknown>).results) && ((result as Record<string, unknown>).results as Array<Record<string, unknown>>).length > 0 ? (
                ((result as Record<string, unknown>).results as Array<Record<string, unknown>>).map((item: Record<string, unknown>, idx: number) => (
                  <div key={idx} className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-600 dark:bg-slate-800">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="rounded bg-sky-50 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:bg-sky-900/20 dark:text-sky-400">
                        {(item.source_type as string)?.toUpperCase?.() || 'UNKNOWN'}
                      </span>
                      <span className="text-[10px] text-slate-400">相似度: {((item.score as number) * 100).toFixed(1)}%</span>
                    </div>
                    <p className="text-sm text-slate-700 dark:text-slate-300 line-clamp-4">{item.content as string}</p>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-500 dark:text-slate-400">未找到相关记忆</div>
              )}
            </div>
          ) : typeof result === 'object' && result !== null && 'markdown' in result && typeof (result as Record<string, unknown>).markdown === 'string' ? (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{(result as Record<string, unknown>).markdown as string}</ReactMarkdown>
            </div>
          ) : (
            <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
          )}
        </div>
      )}

      {result !== null && result !== undefined && toolId !== "memory" && prds.length > 0 && (
        <div className="mt-4 flex items-center gap-3">
          <select
            className="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-white text-sm"
            value=""
            onChange={async (e) => {
              const prdId = e.target.value;
              if (!prdId) return;
              const markdown = typeof result === 'object' && result !== null && 'markdown' in result && typeof (result as Record<string, unknown>).markdown === 'string' ? (result as Record<string, unknown>).markdown as string : "";
              if (!markdown) return;
              try {
                setAppendError("");
                const prd = await prdApi.get(prdId);
                const newMarkdown = (prd.markdown || "") + "\n\n---\n\n" + markdown;
                await prdApi.update(prdId, { markdown: newMarkdown });
                setAppendSuccess(true);
                setTimeout(() => setAppendSuccess(false), 3000);
              } catch (err: unknown) {
                setAppendError("追加失败: " + (err instanceof Error ? err.message : "未知错误"));
              }
            }}
          >
            <option value="">追加到 PRD...</option>
            {prds.map((p) => (
              <option key={p.id} value={p.id}>{p.title}</option>
            ))}
          </select>
          {appendSuccess && <span className="text-sm text-emerald-600 dark:text-emerald-400">已追加</span>}
          {appendError && <span className="text-sm text-rose-600 dark:text-rose-400">{appendError}</span>}
        </div>
      )}
      {result !== null && result !== undefined && toolId !== "memory" && prds.length === 0 && (
        <div className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          该项目暂无 PRD，无法追加结果
        </div>
      )}
    </div>
  );
}
