"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { flushSync } from "react-dom";
import Link from "next/link";
import NavHeader from "@/components/global/NavHeader";
import { usePRDStore } from '@/stores/prdStore';
import { prdApi, toolsApi, aiApi, annotationApi, reviewApi, codeApi, revisionTaskApi, type ChecklistItem, type ChecklistState, type PrototypeSkeleton } from "@/lib/api";
import { SkeletonText } from "@/components/ui/Skeleton";
import { devLog, devWarn } from "@/utils/logger";
import { confirm } from "@/components/ui/ConfirmDialog";
import ExportPanel from "./ExportPanel";
import VersionPanel from "./VersionPanel";
import PrototypePanel from "./PrototypePanel";
import ReviewPanel from "./ReviewPanel";
import AnnotationPanel from "./AnnotationPanel";
import RevisionTaskPanel from "./RevisionTaskPanel";
import MarkdownEditor from "./MarkdownEditor";
import QuickAction from "./QuickAction";
import ChapterItem from "./ChapterItem";
import WorkspaceTabs from "./WorkspaceTabs";
import NextStepCard from "./NextStepCard";

export default function PRDEditor({ params }: { params: { id: string } }) {
  const { content, setContent, isLoading, setIsLoading, isSaving, setIsSaving, autoSaveStatus, setAutoSaveStatus, documentTitle, setDocumentTitle, status, setStatus, projectId, setProjectId, chapters, setChapters, checklistState, setChecklistState, checklistResult, setChecklistResult, aiReviewLoading, setAiReviewLoading, runAIReview } = usePRDStore();
  const [aiMessage, setAiMessage] = useState("");

  // Panels
  const [showExportPanel, setShowExportPanel] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [versions, setVersions] = useState<Array<{ id: string; version_number: number; title: string; created_at: string }>>([]);
  const [isPublishing, setIsPublishing] = useState(false);

  // Annotations
  const [showAnnotationPanel, setShowAnnotationPanel] = useState(false);
  const [annotations, setAnnotations] = useState<Array<{
    id: string;
    content: string;
    annotation_type: 'comment' | 'question' | 'suggestion' | 'issue';
    status: 'open' | 'resolved' | 'dismissed';
    chapter_num: string | null;
    chapter_title: string | null;
    line_index: number | null;
    selected_text: string | null;
    created_at: string;
  }>>([]);
  const [annotationFilter, setAnnotationFilter] = useState<'all' | 'open' | 'resolved' | 'dismissed'>('all');
  const [annotationStats, setAnnotationStats] = useState({ open: 0, resolved: 0, dismissed: 0, total: 0 });
  const [newAnnotationContent, setNewAnnotationContent] = useState('');
  const [newAnnotationType, setNewAnnotationType] = useState<'comment' | 'question' | 'suggestion' | 'issue'>('comment');
  const [showAnnotationForm, setShowAnnotationForm] = useState(false);
  const [selectedTextForAnnotation, setSelectedTextForAnnotation] = useState<string | null>(null);
  const [annotationLineIndex, setAnnotationLineIndex] = useState<number | null>(null);
  const [isLoadingAnnotations, setIsLoadingAnnotations] = useState(false);
  const [autoReviewLoading, setAutoReviewLoading] = useState(false);

  // Revision Tasks
  const [showTaskPanel, setShowTaskPanel] = useState(false);
  const [tasks, setTasks] = useState<Array<{
    id: string;
    title: string;
    description: string | null;
    status: string;
    assigned_to: string | null;
    completed_at: string | null;
    completion_note: string | null;
    re_review_status: string | null;
    created_at: string;
  }>>([]);
  const [taskFilter, setTaskFilter] = useState<'all' | 'todo' | 'in_progress' | 'done' | 'cancelled'>('all');
  const [taskStats, setTaskStats] = useState({ todo: 0, in_progress: 0, done: 0, cancelled: 0, total: 0 });
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  // Review checklist
  const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([]);
  const [checklistLoading, setChecklistLoading] = useState(false);
  const [checklistSaving, setChecklistSaving] = useState(false);

  // Prototype preview
  const [showPrototypePanel, setShowPrototypePanel] = useState(false);
  const [prototypeHtml, setPrototypeHtml] = useState<string>("");
  const [prototypeLoading, setPrototypeLoading] = useState(false);
  const [prototypeDevice, setPrototypeDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");

  // Prototype generation pipeline (transparent)
  const [protoPhase, setProtoPhase] = useState<"idle" | "extracting" | "generating" | "done" | "error">("idle");
  const [protoSkeleton, setProtoSkeleton] = useState<PrototypeSkeleton | null>(null);
  const [protoProgressMsg, setProtoProgressMsg] = useState("");
  const [protoProgress, setProtoProgress] = useState("0/0");
  const [protoReport, setProtoReport] = useState<any>(null);

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [chapterStatus, setChapterStatus] = useState<Record<string, "pending" | "active" | "done" | "failed">>({});

  const contentRef = useRef(content);
  const reviewRef = useRef<HTMLDivElement>(null);
  useEffect(() => { contentRef.current = content; }, [content]);

  // Streaming: queue-based consumption for smooth visual effect
  // Even if fetch buffers all data, we display chunks gradually
  const streamingQueueRef = useRef<string[]>([]);
  const displayedTextRef = useRef("");
  const activeChapterRef = useRef<{ title: string; num: string }>({ title: "", num: "" });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const protoIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamingIntervalsRef = useRef<Set<ReturnType<typeof setInterval>>>(new Set());
  const protoPollCountRef = useRef(0);
  const MAX_POLL_ATTEMPTS = 30;
  const hasReceivedChunkRef = useRef(false);

  // Optimized chapter replacement with position cache
  const chapterCacheRef = useRef<Record<string, { start: number; end: number }>>({});

  const buildChapterCache = (doc: string) => {
    const lines = doc.split("\n");
    const cache: Record<string, { start: number; end: number }> = {};
    let currentChapter = "";
    let currentStart = -1;
    for (let i = 0; i < lines.length; i++) {
      const match = lines[i].match(/^##\s*\d*\.?\s*(.+)$/);
      if (match) {
        if (currentChapter && currentStart >= 0) {
          cache[currentChapter] = { start: currentStart, end: i };
        }
        currentChapter = match[1].trim();
        currentStart = i;
      }
    }
    if (currentChapter && currentStart >= 0) {
      cache[currentChapter] = { start: currentStart, end: lines.length };
    }
    chapterCacheRef.current = cache;
    return cache;
  };

  // Skeleton content shown immediately after clicking "generate" to eliminate black-screen wait
  const CHAPTER_SKELETONS: Record<string, string> = {
    "1": "### 执行摘要\n\nAI 正在分析项目背景与核心目标，请稍候...\n\n### 当前痛点\n\nAI 正在梳理业务痛点与现状问题，请稍候...\n\n### 产品愿景\n\nAI 正在构建产品愿景与价值主张，请稍候...\n\n### 项目目标\n\nAI 正在定义项目目标与范围边界，请稍候...\n\n### 成功指标\n\nAI 正在设定可量化的成功指标，请稍候...\n",
    "2": "### 用户角色定义\n\nAI 正在分析目标用户画像，请稍候...\n\n### 核心用户场景\n\nAI 正在梳理关键使用场景，请稍候...\n\n### 用户故事列表\n\nAI 正在编写用户故事与验收标准，请稍候...\n\n### 验收标准\n\nAI 正在细化各故事的验收条件，请稍候...\n",
    "3": "### 核心业务流程\n\nAI 正在梳理主业务流程与参与者，请稍候...\n\n### 时序图说明\n\nAI 正在分析系统交互时序，请稍候...\n\n### 异常流程\n\nAI 正在梳理异常分支与处理策略，请稍候...\n\n### 业务规则\n\nAI 正在定义关键业务规则与约束，请稍候...\n",
    "4": "### 功能模块概述\n\nAI 正在划分功能模块与优先级，请稍候...\n\n### 核心功能详情\n\nAI 正在编写功能规格与交互逻辑，请稍候...\n\n### 页面结构\n\nAI 正在设计页面布局与信息架构，请稍候...\n\n### 输入输出定义\n\nAI 正在定义接口输入输出与数据格式，请稍候...\n",
    "5": "### 数据实体定义\n\nAI 正在设计核心数据实体与关系，请稍候...\n\n### 字段定义\n\nAI 正在定义关键字段与数据类型，请稍候...\n\n### 数据流转\n\nAI 正在梳理数据流转路径与存储策略，请稍候...\n\n### 安全分级\n\nAI 正在制定数据安全分级与保护措施，请稍候...\n",
    "6": "### 适用法规\n\nAI 正在识别适用的法律法规与行业标准，请稍候...\n\n### 安全要求\n\nAI 正在梳理安全合规要求与技术措施，请稍候...\n\n### 隐私保护\n\nAI 正在制定隐私保护与数据最小化策略，请稍候...\n\n### 审计要求\n\nAI 正在定义审计检查清单与合规流程，请稍候...\n",
    "7": "### 核心指标定义\n\nAI 正在定义核心业务与分析指标，请稍候...\n\n### 埋点事件设计\n\nAI 正在设计埋点事件与属性规范，请稍候...\n\n### 上报时机\n\nAI 正在制定数据上报时机与触发条件，请稍候...\n\n### 分析看板\n\nAI 正在规划数据看板与报表需求，请稍候...\n",
    "8": "### 阶段划分\n\nAI 正在划分项目阶段与关键里程碑，请稍候...\n\n### 交付物清单\n\nAI 正在梳理各阶段交付物与验收标准，请稍候...\n\n### 风险预估\n\nAI 正在识别项目风险与缓解方案，请稍候...\n\n### 发布策略\n\nAI 正在制定发布计划与回滚方案，请稍候...\n",
    "9": "### 阶段划分\n\nAI 正在划分项目阶段与关键里程碑，请稍候...\n\n### 交付物清单\n\nAI 正在梳理各阶段交付物与验收标准，请稍候...\n\n### 风险预估\n\nAI 正在识别项目风险与缓解方案，请稍候...\n\n### 发布策略\n\nAI 正在制定发布计划与回滚方案，请稍候...\n",
  };

  const replaceChapterContent = (doc: string, chapterTitle: string, newContent: string, chapterNum?: string): string => {
    const lines = doc.split("\n");

    // Try 1: match by chapter title (existing behavior)
    let chapterIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (/^##\s/.test(lines[i]) && lines[i].includes(chapterTitle)) {
        chapterIdx = i;
        break;
      }
    }

    // Try 2: fallback to chapter number prefix (e.g. "## 1. xxx", "## 1.1 xxx", "## 1、xxx")
    if (chapterIdx === -1 && chapterNum) {
      const escapedNum = chapterNum.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const numRegex = new RegExp(`^##\\s*${escapedNum}([.\\s)\\]|$)`);
      for (let i = 0; i < lines.length; i++) {
        if (numRegex.test(lines[i])) {
          chapterIdx = i;
          break;
        }
      }
    }

    // Try 3: append a new chapter at end of document if still not found
    if (chapterIdx === -1) {
      devLog(`[replaceChapterContent] NOT FOUND: title="${chapterTitle}" num="${chapterNum}" — APPENDING at end`);
      const heading = `## ${chapterNum ? chapterNum + ". " : ""}${chapterTitle}`;
      const trimmed = doc.replace(/\s+$/, "");
      return `${trimmed}\n\n${heading}\n\n${newContent}\n`;
    }

    // Find the end of this chapter (next ## heading or EOF)
    let endIdx = lines.length;
    for (let i = chapterIdx + 1; i < lines.length; i++) {
      if (/^##\s/.test(lines[i])) {
        endIdx = i;
        break;
      }
    }

    const rawAiLines = newContent.split("\n");
    let skipIdx = 0;
    while (skipIdx < rawAiLines.length) {
      const line = rawAiLines[skipIdx].trim();
      if (line === "") { skipIdx++; continue; }
      // Match heading that contains chapter title or "X. title" pattern
      const isChapterHeading = /^##\s/.test(line) && (
        line.includes(chapterTitle) ||
        (chapterNum ? new RegExp(`^##\\s*${chapterNum.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")}([.\\s)\\]|$)`).test(line) : false)
      );
      if (isChapterHeading) { skipIdx++; continue; }
      break;
    }
    const aiLines = rawAiLines.slice(skipIdx);

    // Look for placeholder inside the chapter
    let placeholderIdx = -1;
    for (let i = chapterIdx + 1; i < endIdx; i++) {
      if (lines[i].includes("（待填写）")) { placeholderIdx = i; break; }
    }

    if (placeholderIdx !== -1) {
      lines.splice(placeholderIdx, 1, ...aiLines);
    } else {
      lines.splice(chapterIdx + 1, endIdx - chapterIdx - 1, "", ...aiLines, "");
    }

    return lines.join("\n");
  };

  const startStreamingTimer = (chapterTitle: string, chapterNum: string) => {
    activeChapterRef.current = { title: chapterTitle, num: chapterNum };
    displayedTextRef.current = "";
    streamingQueueRef.current = [];
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      const queue = streamingQueueRef.current;
      if (queue.length === 0) return;
      // Consume up to 5 chunks per tick for smooth visual flow
      const batch = queue.splice(0, Math.min(queue.length, 5));
      displayedTextRef.current += batch.join("");
      const { title, num } = activeChapterRef.current;
      setContent((prev) => replaceChapterContent(prev, title, displayedTextRef.current, num));
    }, 50);
  };

  const stopStreamingTimer = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
    streamingQueueRef.current = [];
    displayedTextRef.current = "";
    activeChapterRef.current = { title: "", num: "" };
  };

  // Cleanup on unmount
  useEffect(() => () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (protoIntervalRef.current) clearInterval(protoIntervalRef.current);
    streamingIntervalsRef.current.forEach((id) => clearInterval(id));
    streamingIntervalsRef.current.clear();
  }, []);

  const findChapterLineIndex = (doc: string, chapterTitle: string): number => {
    const lines = doc.split("\n");
    for (let i = 0; i < lines.length; i++) {
      if (/^##\s/.test(lines[i]) && lines[i].includes(chapterTitle)) return i;
    }
    return -1;
  };

  const chapterHasRealContent = (doc: string, chapterTitle: string): boolean => {
    const lines = doc.split("\n");
    let chapterIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (/^##\s/.test(lines[i]) && lines[i].includes(chapterTitle)) { chapterIdx = i; break; }
    }
    if (chapterIdx === -1) return false;
    for (let i = chapterIdx + 1; i < lines.length; i++) {
      if (/^##\s/.test(lines[i])) break;
      const trimmed = lines[i].trim();
      if (trimmed && trimmed !== "（待填写）") return true;
    }
    return false;
  };

  const scrollToLine = (lineIndex: number) => {
    const textarea = document.querySelector("textarea") as HTMLTextAreaElement | null;
    if (!textarea) return;
    const lines = content.split("\n");
    let charIndex = 0;
    for (let i = 0; i < lineIndex; i++) {
      charIndex += lines[i].length + 1; // +1 for \n
    }
    textarea.selectionStart = charIndex;
    textarea.selectionEnd = charIndex;
    textarea.focus();
    // Approximate scroll: line height ~ 24px
    textarea.scrollTop = lineIndex * 24 - textarea.clientHeight / 3;
  };

  // Load real PRD data
  useEffect(() => {
    async function loadPRD() {
      try {
        if (!params.id || typeof params.id !== 'string') {
          throw new Error('无效的 PRD ID');
        }
        const prd = await prdApi.get(params.id);
        if (!prd || !prd.id) {
          throw new Error('PRD 不存在或已被删除');
        }
        setDocumentTitle(prd.title || "未命名 PRD");
        setContent(prd.markdown || "");
        setStatus(prd.status || "draft");
        setProjectId(prd.project_id || null);

        // Load dynamic chapter list from PRD template
        const prdChapters = prd.content?.chapters;
        let dynamicChapters: { num: string; title: string }[] = [];
        if (prdChapters && typeof prdChapters === "object") {
          dynamicChapters = Object.entries(prdChapters)
            .sort(([a], [b]) => parseInt(a) - parseInt(b))
            .map(([num, ch]) => ({
              num,
              title: (ch as { title?: string }).title || `Chapter ${num}`,
            }));
        }
        // Fallback: parse chapters from markdown headings
        if (dynamicChapters.length === 0 && prd.markdown) {
          const lines = prd.markdown.split("\n");
          const headingRe = /^##\s+(\d+)[\.\s]*(.+)$/;
          for (const line of lines) {
            const match = line.match(headingRe);
            if (match) {
              dynamicChapters.push({ num: match[1], title: match[2].trim() });
            }
          }
        }
        if (dynamicChapters.length > 0) {
          setChapters(dynamicChapters);
          // Initialize chapter status from existing markdown content
          const initialStatus: Record<string, "pending" | "active" | "done" | "failed"> = {};
          for (const ch of dynamicChapters) {
            initialStatus[ch.num] = chapterHasRealContent(prd.markdown || "", ch.title) ? "done" : "pending";
          }
          setChapterStatus(initialStatus);
        }

        setAiMessage("PRD 加载完成，可直接编辑、导出或继续生成章节");
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "未知错误";
        setAiMessage("加载 PRD 失败: " + message);
        setContent("");
      } finally {
        setIsLoading(false);
        // Check for local draft after loading
        const draftKey = `prd-draft-${params.id}`;
        const draft = localStorage.getItem(draftKey);
        if (draft) {
          try {
            const parsed = JSON.parse(draft);
            if (parsed.content && parsed.timestamp) {
              const age = Date.now() - parsed.timestamp;
              if (age < 7 * 24 * 60 * 60 * 1000) { // 7 days
                setContent(parsed.content);
                setAutoSaveStatus("saved");
                setAiMessage("已恢复本地自动保存的草稿");
              } else {
                localStorage.removeItem(draftKey);
              }
            }
          } catch {
            devWarn("本地草稿数据损坏，已跳过恢复");
          }
        }
      }
    }
    loadPRD();
  }, [params.id, setAutoSaveStatus, setChapters, setContent, setDocumentTitle, setIsLoading, setProjectId, setStatus]);

  // Load annotations on mount
  useEffect(() => {
    if (params.id) loadAnnotations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  // Load review checklist when projectId is available
  useEffect(() => {
    if (!projectId) return;
    async function loadChecklist() {
      setChecklistLoading(true);
      try {
        const res = await reviewApi.getChecklist(projectId!);
        setChecklistItems(res.items || []);
        // Load saved state from localStorage
        const saved = localStorage.getItem(`review-checklist-${projectId}-${params.id}`);
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
              setChecklistState(parsed);
            }
          } catch {
            devWarn("检查清单数据损坏，保留现有状态");
          }
        }
      } catch (err: unknown) {
        console.error("Failed to load checklist:", err);
      } finally {
        setChecklistLoading(false);
      }
    }
    loadChecklist();
  }, [projectId, params.id, setChecklistState]);

  const handleAIReview = async () => {
    await runAIReview(checklistItems, projectId, params.id);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await prdApi.update(params.id, { markdown: content });
      setAiMessage("已保存");
      localStorage.removeItem(`prd-draft-${params.id}`);
      setAutoSaveStatus("idle");
    } catch (err: unknown) {
      setAiMessage("保存失败: " + (err instanceof Error ? err.message : "未知错误"));
    } finally {
      setIsSaving(false);
    }
  };

  // Auto-save draft to localStorage every 30 seconds
  useEffect(() => {
    if (!content || isLoading) return;
    const draftKey = `prd-draft-${params.id}`;
    const timer = setInterval(() => {
      localStorage.setItem(
        draftKey,
        JSON.stringify({ content, timestamp: Date.now() })
      );
      setAutoSaveStatus("saved");
      setTimeout(() => setAutoSaveStatus("idle"), 2000);
    }, 30000);
    return () => clearInterval(timer);
  }, [content, isLoading, params.id, setAutoSaveStatus]);

  // Mark dirty on content change (debounced)
  useEffect(() => {
    if (!content || isLoading) return;
    const timer = setTimeout(() => {
      setAutoSaveStatus("dirty");
    }, 500);
    return () => clearTimeout(timer);
  }, [content, isLoading, setAutoSaveStatus]);

  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      await prdApi.update(params.id, { status: "published" });
      setStatus("published");
      setAiMessage("PRD 已发布");
    } catch (err: unknown) {
      setAiMessage("发布失败: " + (err instanceof Error ? err.message : "未知错误"));
    } finally {
      setIsPublishing(false);
    }
  };

  const handleExport = async (format: string) => {
    try {
      const res = await prdApi.export(params.id, format as "markdown" | "json" | "pdf" | "docx");

      let blob: Blob;
      if (res.encoding === "base64") {
        const byteString = atob(res.content);
        const bytes = new Uint8Array(byteString.length);
        for (let i = 0; i < byteString.length; i++) {
          bytes[i] = byteString.charCodeAt(i);
        }
        const mimeTypes: Record<string, string> = {
          pdf: "application/pdf",
          docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        };
        blob = new Blob([bytes], { type: mimeTypes[format] || "application/octet-stream" });
      } else {
        blob = new Blob([res.content], { type: "text/plain;charset=utf-8" });
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = res.filename;
      a.click();
      URL.revokeObjectURL(url);
      setAiMessage(`已导出为 ${format}`);
    } catch (err: unknown) {
      setAiMessage("导出失败: " + (err instanceof Error ? err.message : "未知错误"));
    }
  };

  const loadVersions = async () => {
    try {
      const res = await prdApi.versions(params.id, { limit: 10 });
      setVersions(res.items || []);
    } catch {
      setVersions([]);
    }
  };

  const handleRestoreVersion = async (versionId: string, versionNumber: number) => {
    const confirmed = await confirm({
      title: "恢复版本",
      message: `确定要恢复到版本 ${versionNumber} 吗？当前内容将被备份。`,
      type: "warning",
    });
    if (!confirmed) {
      return;
    }
    try {
      const res = await prdApi.restoreVersion(params.id, versionId);
      setAiMessage(res.message);
      // Reload PRD content
      const prd = await prdApi.get(params.id);
      setContent(prd.markdown || "");
      setDocumentTitle(prd.title);
      loadVersions();
    } catch (err: unknown) {
      setAiMessage("恢复失败: " + (err instanceof Error ? err.message : "未知错误"));
    }
  };

  // Annotation functions
  const loadAnnotations = async () => {
    setIsLoadingAnnotations(true);
    try {
      const [listRes, statsRes] = await Promise.all([
        annotationApi.list(params.id, { limit: 100 }),
        annotationApi.stats(params.id),
      ]);
      setAnnotations(listRes.items || []);
      setAnnotationStats(statsRes);
    } catch (err: unknown) {
      setAiMessage('批注加载失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setIsLoadingAnnotations(false);
    }
  };

  const handleAddAnnotation = async () => {
    if (!newAnnotationContent.trim()) return;
    try {
      await annotationApi.create(params.id, {
        content: newAnnotationContent.trim(),
        annotation_type: newAnnotationType,
        selected_text: selectedTextForAnnotation || undefined,
        line_index: annotationLineIndex ?? undefined,
      });
      setNewAnnotationContent('');
      setShowAnnotationForm(false);
      setSelectedTextForAnnotation(null);
      setAnnotationLineIndex(null);
      await loadAnnotations();
      setAiMessage('批注已添加');
    } catch (err: unknown) {
      setAiMessage('添加批注失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleResolveAnnotation = async (annotationId: string) => {
    try {
      await annotationApi.update(params.id, annotationId, { status: 'resolved' });
      await loadAnnotations();
      setAiMessage('批注已标记为已解决');
    } catch (err: unknown) {
      setAiMessage('操作失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleDismissAnnotation = async (annotationId: string) => {
    try {
      await annotationApi.update(params.id, annotationId, { status: 'dismissed' });
      await loadAnnotations();
      setAiMessage('批注已忽略');
    } catch (err: unknown) {
      setAiMessage('操作失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleDeleteAnnotation = async (annotationId: string) => {
    const confirmed = await confirm({
      title: "删除批注",
      message: "确定要删除这条批注吗？",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await annotationApi.delete(params.id, annotationId);
      await loadAnnotations();
      setAiMessage('批注已删除');
    } catch (err: unknown) {
      setAiMessage('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleConvertToTask = async (annotationId: string) => {
    try {
      await annotationApi.convertToTask(params.id, annotationId);
      await Promise.all([loadAnnotations(), loadTasks()]);
      setAiMessage('已转为修改任务');
    } catch (err: unknown) {
      setAiMessage('转任务失败 ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleAutoReview = async () => {
    setAutoReviewLoading(true);
    try {
      const res = await annotationApi.autoReview(params.id);
      await loadAnnotations();
      setAiMessage(res.message || `AI 评审完成，发现 ${res.issues_found} 个问题`);
    } catch (err: unknown) {
      setAiMessage('AI 评审失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setAutoReviewLoading(false);
    }
  };

  // Revision Task functions
  const loadTasks = async () => {
    setIsLoadingTasks(true);
    try {
      const [listRes, statsRes] = await Promise.all([
        revisionTaskApi.list(params.id),
        revisionTaskApi.stats(params.id),
      ]);
      setTasks(listRes || []);
      setTaskStats(statsRes);
    } catch (err: unknown) {
      setAiMessage('任务加载失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setIsLoadingTasks(false);
    }
  };

  const handleCompleteTask = async (taskId: string, note: string, triggerReReview: boolean) => {
    try {
      await revisionTaskApi.complete(params.id, taskId, { completion_note: note, trigger_re_review: triggerReReview });
      await Promise.all([loadTasks(), loadAnnotations()]);
      setAiMessage(triggerReReview ? '任务已完成，再评审已排队' : '任务已完成');
    } catch (err: unknown) {
      setAiMessage('完成任务失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleUpdateTaskStatus = async (taskId: string, status: string) => {
    try {
      await revisionTaskApi.update(params.id, taskId, { status });
      await loadTasks();
    } catch (err: unknown) {
      setAiMessage('更新状态失败 ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    const confirmed = await confirm({
      title: "删除任务",
      message: "确定要删除这个修改任务吗？",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await revisionTaskApi.delete(params.id, taskId);
      await Promise.all([loadTasks(), loadAnnotations()]);
      setAiMessage('任务已删除');
    } catch (err: unknown) {
      setAiMessage('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  // Review callbacks
  const handleChecklistToggle = (itemId: string, checked: boolean) => {
    const itemState = checklistState[itemId] || { checked: false, note: "" };
    const next = { ...checklistState, [itemId]: { ...itemState, checked } };
    setChecklistState(next);
    if (projectId) {
      localStorage.setItem(`review-checklist-${projectId}-${params.id}`, JSON.stringify(next));
    }
  };

  const handleChecklistNoteChange = (itemId: string, note: string) => {
    const itemState = checklistState[itemId] || { checked: false, note: "" };
    const next = { ...checklistState, [itemId]: { ...itemState, note } };
    setChecklistState(next);
    if (projectId) {
      localStorage.setItem(`review-checklist-${projectId}-${params.id}`, JSON.stringify(next));
    }
  };

  const handleSubmitChecklist = async () => {
    if (!projectId) return;
    setChecklistSaving(true);
    try {
      const items = checklistItems.map((item) => ({
        item_id: item.id,
        checked: checklistState[item.id]?.checked || false,
        note: checklistState[item.id]?.note || null,
      }));
      const res = await reviewApi.submitChecklist(projectId, items);
      const requiredItems = checklistItems.filter((i) => i.required);
      const requiredChecked = requiredItems.filter((i) => checklistState[i.id]?.checked).length;
      if (res.all_required_passed) {
        setChecklistResult(`✅ 所有必选项已通过 (${requiredChecked}/${requiredItems.length})`);
      } else {
        setChecklistResult(`⚠️ 必选项未全部通过 (${requiredChecked}/${requiredItems.length})`);
        // Prompt to create revision tasks for failed items
        const failed = checklistItems.filter((i) => i.required && !checklistState[i.id]?.checked);
        if (failed.length > 0 && confirm) {
          const ok = await confirm({ message: `有 ${failed.length} 个必选项未通过。是否基于未通过项创建修订任务？`, type: "warning" });
          if (ok) setShowTaskPanel(true);
        }
      }
      setTimeout(() => setChecklistResult(null), 5000);
    } catch (err: unknown) {
      setChecklistResult("提交失败: " + (err instanceof Error ? err.message : "未知错误"));
    } finally {
      setChecklistSaving(false);
    }
  };

  // Annotation callbacks
  const handleAnnotationCancel = () => {
    setShowAnnotationForm(false);
    setSelectedTextForAnnotation(null);
    setAnnotationLineIndex(null);
    setNewAnnotationContent("");
  };

  const openAnnotationForm = () => {
    const textarea = document.querySelector('textarea') as HTMLTextAreaElement | null;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      if (start !== end) {
        const selected = content.slice(start, end).trim();
        if (selected) {
          setSelectedTextForAnnotation(selected);
          // Calculate line index
          const beforeSelection = content.slice(0, start);
          setAnnotationLineIndex(beforeSelection.split('\n').length - 1);
        }
      }
    }
    setShowAnnotationForm(true);
    setShowAnnotationPanel(true);
  };

  const handleRegenerate = async () => {
    const confirmed = await confirm({
      title: "重新生成 PRD",
      message: "重新生成将按模板章节结构，每章替换全部内容。此操作不可撤销。确定继续？",
      type: "warning",
    });
    if (!confirmed) {
      return;
    }
    if (isStreaming) return;

    // Reset all chapter statuses to pending before regeneration
    const resetStatus: Record<string, "pending" | "active" | "done" | "failed"> = {};
    for (const ch of chapters) {
      resetStatus[ch.num] = "pending";
    }
    setChapterStatus(resetStatus);

    const CONCURRENCY = 1; // sequential generation for maximum cross-chapter consistency
    const failedList: string[] = [];
    let completed = 0;
    let currentDoc = content;

    // Debug: log chapters from store vs document headings
    devLog("[handleRegenerate] chapters from store:", JSON.stringify(chapters.map(c => ({ num: c.num, title: c.title }))));
    const docHeadings = content.split("\n").filter(l => /^##\s/.test(l));
    devLog("[handleRegenerate] doc headings:", JSON.stringify(docHeadings));

    // Helper: generate a single chapter with real-time streaming display
    const generateOne = (ch: (typeof chapters)[0]): Promise<string | null> => {
      let displayed = "";
      let lastDisplayed = "";
      let done = false;
      const interval = setInterval(() => {
        if (done) return;
        if (displayed !== lastDisplayed) {
          lastDisplayed = displayed;
          setContent((prev) => replaceChapterContent(prev, ch.title, displayed, ch.num));
        }
      }, 100);
      streamingIntervalsRef.current.add(interval);

      // Safety timeout: abort after 3 minutes
      const timeout = setTimeout(() => {
        if (!done) {
          done = true;
          clearInterval(interval);
          streamingIntervalsRef.current.delete(interval);
        }
      }, 180000);

      return new Promise((resolve) => {
        const cleanup = () => {
          clearInterval(interval);
          clearTimeout(timeout);
          streamingIntervalsRef.current.delete(interval);
        };
        prdApi.generateStream(
          params.id,
          {
            chapter: ch.num,
            prompt: `生成 PRD 章节：${ch.title}。当前文档标题：${documentTitle}`,
            bypass_cache: true,
          },
          (chunk) => {
            if (!done) displayed += chunk;
          },
          (markdown) => {
            done = true;
            cleanup();
            resolve(markdown);
          },
          () => {
            done = true;
            cleanup();
            resolve(null);
          }
        );
      });
    };

    // Process in batches of CONCURRENCY
    for (let i = 0; i < chapters.length; i += CONCURRENCY) {
      const batch = chapters.slice(i, i + CONCURRENCY);

      // Mark batch as active
      batch.forEach((ch) => {
        setChapterStatus((prev) => ({ ...prev, [ch.num]: "active" }));
      });
      setAiMessage(
        `正在重新生成 (${i + 1}-${Math.min(i + CONCURRENCY, chapters.length)}/${chapters.length})...`
      );

      // Parallel generation
      const results = await Promise.all(batch.map(generateOne));

      // Sequential write to avoid race conditions
      batch.forEach((ch, idx) => {
        const markdown = results[idx];
        if (markdown) {
          const beforeLen = currentDoc.length;
          currentDoc = replaceChapterContent(currentDoc, ch.title, markdown, ch.num);
          devLog(`[handleRegenerate] Ch ${ch.num} "${ch.title}": markdown=${markdown.length} chars, doc ${beforeLen}→${currentDoc.length}, replaced=${currentDoc.length !== beforeLen}`);
          setContent(currentDoc);
          setChapterStatus((prev) => ({ ...prev, [ch.num]: "done" }));
        } else {
          setChapterStatus((prev) => ({ ...prev, [ch.num]: "failed" }));
          failedList.push(ch.num);
        }
        completed++;
      });

      // Save current state to backend
      try {
        await prdApi.update(params.id, { markdown: currentDoc });
      } catch (saveErr) {
        const backupKey = `prd-backup-${params.id}`;
        localStorage.setItem(backupKey, currentDoc);
        console.error("Save after batch regen failed:", saveErr);
        setAiMessage("⚠️ 保存失败，内容已备份到本地存储，请勿刷新页面并稍后重试");
      }
    }

    devLog("[handleRegenerate] DONE. currentDoc length:", currentDoc.length);
    devLog("[handleRegenerate] first 500 chars:", currentDoc.slice(0, 500));
    if (failedList.length > 0) {
      setAiMessage(
        `重新生成完成，第 ${failedList.join(", ")} 章生成失败，可点击左侧"重试"按钮单独生成`
      );
    } else {
      setAiMessage("PRD 已按模板结构重新生成");
    }
  };

  const replaceChapterPlaceholder = (doc: string, chapterTitle: string, newContent: string): string => {
    const lines = doc.split("\n");

    // Find the chapter heading line (## prefix + chapter title)
    let chapterIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (/^##\s/.test(lines[i]) && lines[i].includes(chapterTitle)) {
        chapterIdx = i;
        break;
      }
    }
    if (chapterIdx === -1) return doc; // chapter not found, no change

    // Find the end of this chapter (next ## heading or EOF)
    let endIdx = lines.length;
    for (let i = chapterIdx + 1; i < lines.length; i++) {
      if (/^##\s/.test(lines[i])) {
        endIdx = i;
        break;
      }
    }

    // Look for the "（待填写）" placeholder inside the chapter
    let placeholderIdx = -1;
    for (let i = chapterIdx + 1; i < endIdx; i++) {
      if (lines[i].includes("（待填写）")) {
        placeholderIdx = i;
        break;
      }
    }

    const aiLines = newContent.split("\n");

    if (placeholderIdx !== -1) {
      // Replace only the placeholder line with AI content
      lines.splice(placeholderIdx, 1, ...aiLines);
    } else {
      // No placeholder — chapter already has content. Replace the entire chapter body
      lines.splice(chapterIdx + 1, endIdx - chapterIdx - 1, "", ...aiLines, "");
    }

    return lines.join("\n");
  };

  const insertAfterChapter = (doc: string, keywords: string[], insertText: string): string => {
    const lines = doc.split("\n");
    let idx = -1;
    for (let i = 0; i < lines.length; i++) {
      for (const kw of keywords) {
        if (lines[i].includes(kw)) {
          idx = i;
          break;
        }
      }
      if (idx !== -1) break;
    }
    if (idx === -1) {
      return doc + "\n\n" + insertText;
    }
    let endIdx = lines.length;
    for (let i = idx + 1; i < lines.length; i++) {
      if (/^##\s/.test(lines[i])) {
        endIdx = i;
        break;
      }
    }
    lines.splice(endIdx, 0, "", insertText);
    return lines.join("\n");
  };

  const handleQuickAction = async (action: string) => {
    if (!projectId) {
      setAiMessage("缺少项目关联，无法执行此操作");
      return;
    }
    if (isStreaming) return;

    setIsStreaming(true);
    setAiMessage("正在执行...");

    const materialType = action === "compliance" ? "risks" : action;

    const previewQueue: string[] = [];
    let previewText = "";

    // Timer for smooth visual streaming of quick action output
    const previewInterval = setInterval(() => {
      if (previewQueue.length === 0) return;
      const batch = previewQueue.splice(0, Math.min(previewQueue.length, 8));
      previewText += batch.join("");
      const separator = "\n\n--- AI 生成中---\n\n";
      // Use functional update to avoid stale snapshot
      setContent((prev) => {
        let clean = prev;
        const sepIdx = clean.indexOf(separator);
        if (sepIdx !== -1) clean = clean.slice(0, sepIdx);
        return clean + separator + previewText;
      });
    }, 50);

    const abort = toolsApi.reviewMaterialsStream(
      { project_id: projectId, material_type: materialType },
      (chunk) => {
        previewQueue.push(chunk);
      },
      async (markdown) => {
        clearInterval(previewInterval);

        const append = `## AI Quick Output:${action}\n\n${markdown}`;

        const actionChapterMap: Record<string, string[]> = {
          agenda: ["背景与目的", "执行摘要"],
          qa: ["用户故事", "核心用户场景"],
          risks: ["风险预估", "风险预控"],
          compliance: ["合规要求", "安全要求"],
        };

        // Insert into correct chapter based on latest document state
        let newContent = "";
        flushSync(() => {
          setContent((prev) => {
            // Strip any streaming preview first
            let clean = prev;
            const separator = "\n\n--- AI 生成中---\n\n";
            const sepIdx = clean.indexOf(separator);
            if (sepIdx !== -1) clean = clean.slice(0, sepIdx);
            newContent = insertAfterChapter(clean, actionChapterMap[action] || [], append);
            return newContent;
          });
        });
        setIsStreaming(false);
        setAiMessage("AI 操作完成，结果已插入到对应章节");
        try {
          await prdApi.update(params.id, { markdown: newContent });
        } catch (saveErr) {
          const backupKey = `prd-backup-${params.id}`;
          localStorage.setItem(backupKey, newContent);
          console.error("Save after AI operation failed:", saveErr);
          setAiMessage("⚠️ 保存失败，内容已备份到本地存储，请勿刷新页面并稍后重试");
        }
      },
      (error) => {
        clearInterval(previewInterval);
        // Remove streaming preview from current content
        flushSync(() => {
          setContent((prev) => {
            const separator = "\n\n--- AI 生成中---\n\n";
            const sepIdx = prev.indexOf(separator);
            if (sepIdx !== -1) return prev.slice(0, sepIdx);
            return prev;
          });
        });
        setIsStreaming(false);
        setAiMessage("操作失败: " + error);
      }
    );

    return () => {
      clearInterval(previewInterval);
      abort();
    };
  };

  const generateChapterPromise = (chapterNum: string, chapterTitle: string): Promise<boolean> => {
    return new Promise((resolve) => {
      if (isStreaming) {
        resolve(false);
        return;
      }

      setIsStreaming(true);
      streamingQueueRef.current = [];
      hasReceivedChunkRef.current = false;
      setChapterStatus((prev) => ({ ...prev, [chapterNum]: "active" }));
      setAiMessage(`Generating chapter ${chapterNum}: ${chapterTitle}...`);

      // Show skeleton immediately so user sees chapter structure before first token
      const skeleton = CHAPTER_SKELETONS[chapterNum] || "### 正在生成...\n\nAI 正在构建章节内容，请稍候...\n";
      flushSync(() => {
        setContent((prev) => replaceChapterContent(prev, chapterTitle, skeleton, chapterNum));
      });

      startStreamingTimer(chapterTitle, chapterNum);

      // If reasoning model takes >3s before first content chunk, show thinking hint
      const thinkingTimeout = setTimeout(() => {
        if (!hasReceivedChunkRef.current) {
          setAiMessage(`Generating chapter ${chapterNum}: ${chapterTitle}（AI 正在深度思考，请稍候...）`);
        }
      }, 3000);

      prdApi.generateStream(
        params.id,
        {
          chapter: chapterNum,
          prompt: `生成 PRD 章节：${chapterTitle}。当前文档标题：${documentTitle}`,
          bypass_cache: true,
        },
        (chunk) => {
          if (!hasReceivedChunkRef.current) {
            hasReceivedChunkRef.current = true;
            clearTimeout(thinkingTimeout);
            setAiMessage(`Generating chapter ${chapterNum}: ${chapterTitle}...`);
          }
          streamingQueueRef.current.push(chunk);
        },
        async (markdown) => {
          stopStreamingTimer();
          let newContent = "";
          flushSync(() => {
            setContent((prev) => {
              newContent = replaceChapterContent(prev, chapterTitle, markdown, chapterNum);
              return newContent;
            });
            setIsStreaming(false);
            setChapterStatus((prev) => ({ ...prev, [chapterNum]: "done" }));
          });
          setAiMessage(`第${chapterNum} 章生成完成`);

          try {
            await prdApi.update(params.id, { markdown: newContent });
          } catch (saveErr) {
            const backupKey = `prd-backup-${params.id}`;
            localStorage.setItem(backupKey, newContent);
            console.error("Save after chapter generation failed:", saveErr);
            setAiMessage("⚠️ 保存失败，内容已备份到本地存储，请勿刷新页面并稍后重试");
          }
          resolve(true);
        },
        (error) => {
          stopStreamingTimer();
          flushSync(() => {
            setIsStreaming(false);
            setChapterStatus((prev) => ({ ...prev, [chapterNum]: "failed" }));
          });
          setAiMessage(`第${chapterNum} 章生成失败: ${error}，可点击左侧"重试"按钮再次生成`);
          resolve(false);
        }
      );
    });
  };

  const handleGenerateChapter = async (chapterNum: string, chapterTitle: string) => {
    await generateChapterPromise(chapterNum, chapterTitle);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 md:hidden dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
          title="导出文档"
        >
          📤
        </button>
        <button
          onClick={() => setShowTaskPanel(!showTaskPanel)}
          className="rounded-lg border px-2.5 py-1.5 text-sm font-medium transition-colors duration-150 md:hidden border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          📋
        </button>
        <button
          onClick={() => setShowExportPanel(!showExportPanel)}
          className={`rounded-lg border px-2.5 md:px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
            showExportPanel
              ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
              : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-400 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          }`}
        >
          <span className="hidden md:inline">导出</span>
          <span className="md:hidden">?</span>
        </button>
        <button
          onClick={handlePublish}
          disabled={isPublishing || status === "published"}
          className="rounded-lg bg-sky-500 px-2.5 md:px-3 py-1.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-sky-600 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPublishing ? "..." : status === "published" ? "已发布" : "发布"}
        </button>
      </NavHeader>

      {/* Title bar */}
      <div className="border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-700 dark:bg-slate-950">
        <div className="mx-auto flex max-w-7xl items-center gap-4">
          <Link
            href="/workspace"
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            ← 返回工作台
          </Link>
          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700" />
          <h1 className="max-w-[120px] truncate text-sm font-semibold text-slate-900 sm:max-w-xs dark:text-white">
            {documentTitle}
          </h1>
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
              status === "published"
                ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                : "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
            }`}
          >
            {status === "published" ? "已发布" : "草稿"}
          </span>
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
            <span className="hidden sm:inline">可见范围：{projectId ? "工作区成员" : "仅自己"}</span>
          </div>
        </div>

        {/* Next step recommendation */}
        {!isLoading && (
          <div className="mx-auto max-w-7xl px-1 pb-2">
            <NextStepCard
              hasUnfinishedChecklist={(checklistItems || []).some((i) => i.required && !(checklistState || {})[i.id]?.checked)}
              openAnnotations={annotationStats?.open || 0}
              activeTaskCount={(taskStats?.todo || 0) + (taskStats?.in_progress || 0)}
              hasFailedReReview={(tasks || []).some((t) => t.re_review_status === "fail" || t.re_review_status === "partial" || t.re_review_status === "pending")}
              prdStatus={status || ""}
              projectId={projectId}
              onScrollToReview={() => { reviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }}
              onOpenAnnotations={() => setShowAnnotationPanel(true)}
              onOpenTasks={() => setShowTaskPanel(true)}
            />
          </div>
        )}
      </div>

      {/* Editor */}
      <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-7xl relative">
        {/* Mobile sidebar backdrop */}
        {showSidebar && (
          <div
            className="absolute inset-0 z-10 bg-black/20 md:hidden"
            onClick={() => setShowSidebar(false)}
          />
        )}

        {/* Left Sidebar is hidden on mobile unless toggled */}
        <aside
          className={`absolute z-20 h-full w-64 overflow-y-auto border-r border-slate-200 bg-white p-3 shadow-lg transition-transform duration-200 md:static md:w-72 md:transform-none md:shadow-none dark:border-slate-700 dark:bg-slate-950 ${
            showSidebar ? "translate-x-0" : "-translate-x-full md:translate-x-0"
          }`}
        >
          {/* Mobile close button */}
          <div className="mb-2 flex items-center justify-between md:hidden">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">导出文档</span>
            <button
              onClick={() => setShowSidebar(false)}
              className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              ✕
            </button>
          </div>
          {/* Export Panel */}
          {showExportPanel && (
            <ExportPanel onExport={handleExport} onClose={() => setShowExportPanel(false)} />
          )}

          {/* AI Assistant */}
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-lg dark:bg-amber-900/30">📄</div>
            <h2 className="font-semibold text-slate-900 dark:text-white">AI 助手</h2>
          </div>

          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-sm text-slate-700 dark:text-slate-300">{aiMessage}</p>
          </div>

          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-2">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 rounded-lg bg-sky-500 px-3 py-1.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-sky-600 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? "保存中..." : "保存"}
              </button>
              {autoSaveStatus === "saved" && (
                <span className="text-xs text-emerald-600 dark:text-emerald-400 whitespace-nowrap">已自动保存</span>
              )}
              {autoSaveStatus === "dirty" && (
                <span className="text-xs text-amber-600 dark:text-amber-400 whitespace-nowrap">有未保存更改</span>
              )}
            </div>
            <button
              onClick={handleRegenerate}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors duration-150 hover:bg-slate-50 hover:border-slate-400 active:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              重新生成
            </button>
          </div>

          {/* Quick Actions */}
          <div className="mt-6">
            <h3 className="mb-1 px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500">常用操作</h3>
            <div className="space-y-1">
              <QuickAction label="生成评审报告" onClick={() => handleQuickAction("agenda")} />
              <QuickAction label="生成预览 Q&A" onClick={() => handleQuickAction("qa")} />
              <QuickAction label="检查风险点" onClick={() => handleQuickAction("risks")} />
              <QuickAction label="合规检查" onClick={() => handleQuickAction("compliance")} />
            </div>
          </div>

          {/* AI Demo Generator */}
          <div className="mt-6">
            <h3 className="mb-1 px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500">原型Demo</h3>
            <div className="space-y-2 px-2.5">
              <button
                onClick={async () => {
                  if (!projectId) {
                    setAiMessage("缺少项目关联，无法生成 Demo");
                    return;
                  }
                  if (!content || content.length < 100) {
                    setAiMessage("PRD 内容不足，请先完善 PRD 后再生成 Demo");
                    return;
                  }
                  // 清理旧的缓存
                  if (protoIntervalRef.current) {
                    clearInterval(protoIntervalRef.current);
                    protoIntervalRef.current = null;
                  }
                  setPrototypeLoading(true);
                  setProtoPhase("extracting");
                  setProtoProgressMsg("正在提交骨架提取任务...");
                  setProtoProgress("0/0");
                  setProtoSkeleton(null);
                  setProtoReport(null);
                  setAiMessage("🔍 已提交骨架提取任务，AI 正在后台处理...");

                  try {
                    // Step 1: 提交异步任务
                    const { task_id } = await codeApi.extractPrototypeSkeletonAsync(content);
                    setProtoProgressMsg("正在解析 PRD 产品骨架...（AI 后台处理中）");

                    // Step 2: 轮询任务状态
                    protoPollCountRef.current = 0;
                    let pollDone = false;
                    const poll = setInterval(async () => {
                      if (pollDone) return;
                      protoPollCountRef.current++;
                      if (protoPollCountRef.current > MAX_POLL_ATTEMPTS) {
                        clearInterval(poll);
                        protoIntervalRef.current = null;
                        pollDone = true;
                        setProtoPhase("error");
                        setProtoProgressMsg("骨架提取超时，请重试");
                        setAiMessage("⏰ 原型生成超时");
                        setPrototypeLoading(false);
                        return;
                      }
                      try {
                        const task = await codeApi.getPrototypeTask(task_id);
                        if (task.status === "done") {
                          clearInterval(poll);
                          protoIntervalRef.current = null;
                          pollDone = true;
                          const skeleton = task.skeleton as unknown as PrototypeSkeleton;
                          setProtoSkeleton(skeleton);
                          setProtoPhase("generating");
                          setProtoProgressMsg(`已提取骨架：${skeleton.product_name}（${skeleton.pages.length} 页面，${skeleton.roles.length} 角色）`);
                          setAiMessage(`✅ 骨架提取完成：${skeleton.product_name} · ${skeleton.pages.length} 页· ${skeleton.roles.length} 角色`);

                          // Step 3: 生成原型（非流式）
                          setProtoProgressMsg("正在生成高保真原型，请稍候...");
                          const { html, report } = await codeApi.generatePrototype(content, projectId || undefined, {
                            skeleton,
                            style: "high-fidelity",
                          });

                          if (!html) throw new Error("生成内容为空");

                          setProtoReport(report);
                          setProtoPhase("done");
                          setProtoProgressMsg(`原型生成完成：${report.pages || skeleton.pages.length} 页...`);
                          setAiMessage(`🎨 原型生成完成：${report.pages || skeleton.pages.length} 页 · ${report.interactions?.total || 0} 交互 · ${report.html_size_kb || 0}KB`);
                          setPrototypeHtml(html);
                          setShowPrototypePanel(true);
                          setPrototypeLoading(false);
                        } else if (task.status === "failed") {
                          clearInterval(poll);
                          protoIntervalRef.current = null;
                          pollDone = true;
                          throw new Error(task.error || "骨架提取失败");
                        }
                        // else: pending/extracting，继续处理中
                      } catch (err: unknown) {
                        clearInterval(poll);
                        protoIntervalRef.current = null;
                        pollDone = true;
                        setProtoPhase("error");
                        const msg = err instanceof Error ? err.message : "生成失败";
                        setProtoProgressMsg(`🎨${msg}`);
                        setAiMessage("🎨 原型生成失败: " + msg);
                        setPrototypeLoading(false);
                      }
                    }, 2000);
                    protoIntervalRef.current = poll;
                  } catch (err: unknown) {
                    setProtoPhase("error");
                    const msg = err instanceof Error ? err.message : "生成失败";
                    setProtoProgressMsg(`🎨${msg}`);
                    setAiMessage("🎨 原型生成失败: " + msg);
                    setPrototypeLoading(false);
                  }
                }}
                disabled={prototypeLoading}
                className="w-full rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {prototypeLoading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    {protoPhase === "extracting" ? "解析骨架中..." : protoPhase === "generating" ? "生成原型中..." : "处理中..."}
                  </span>
                ) : (
                  "🎨 AI 生成 Demo"
                )}
              </button>

              {/* 生成进度 / 报告 */}
              {prototypeLoading && protoPhase !== "idle" && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                      <div
                        className="h-full rounded-full bg-violet-500 transition-all duration-300"
                        style={{
                          width: protoPhase === "extracting" ? "15%" : protoPhase === "generating" ? "60%" : protoPhase === "done" ? "100%" : "0%",
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">{protoProgress}</span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400">{protoProgressMsg}</p>
                  {protoSkeleton && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {protoSkeleton.roles.map((r) => (
                        <span
                          key={r.name}
                          className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium ${
                            r.primary
                              ? "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                          }`}
                        >
                          {r.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 生成完成报告 */}
              {protoPhase === "done" && protoReport && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-900/30 dark:bg-green-900/10">
                  <p className="text-xs font-medium text-green-700 dark:text-green-400">原型生成报告</p>
                  <div className="mt-1.5 grid grid-cols-2 gap-2">
                    <div className="text-center">
                      <p className="text-lg font-bold text-green-700 dark:text-green-400">{protoReport.pages}</p>
                      <p className="text-[10px] text-green-600 dark:text-green-500">页面</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-green-700 dark:text-green-400">{protoReport.interactions?.total || 0}</p>
                      <p className="text-[10px] text-green-600 dark:text-green-500">交互数</p>
                    </div>
                  </div>
                  <p className="mt-1 text-[10px] text-green-600 dark:text-green-500">
                    {protoReport.cached ? "🚀 缓存命中，秒级响应" : `⏱️ 实时生成 · ${protoReport.html_size_kb}KB`}
                  </p>
                </div>
              )}

              {prototypeHtml && (
                <button
                  onClick={() => setShowPrototypePanel(!showPrototypePanel)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors duration-150 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                >
                  {showPrototypePanel ? "隐藏预览" : "查看 Demo"}
                </button>
              )}
            </div>
          </div>

          {/* Review Checklist */}
          <div ref={reviewRef}>
          <ReviewPanel
            items={checklistItems}
            state={checklistState}
            onToggle={handleChecklistToggle}
            onNoteChange={handleChecklistNoteChange}
            loading={checklistLoading}
            saving={checklistSaving}
            result={checklistResult}
            aiReviewLoading={aiReviewLoading}
            onAIReview={handleAIReview}
            onSubmit={handleSubmitChecklist}
          />
          </div>

          {/* Chapter Navigation */}
          <div className="mt-6">
            <h3 className="mb-1 px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500">章节导航</h3>
            <div className="space-y-1">
              {chapters.map((ch) => {
                const lineIdx = findChapterLineIndex(content, ch.title);
                const hasContent = chapterHasRealContent(content, ch.title);
                const rawStatus = chapterStatus[ch.num];
                const status: "pending" | "active" | "done" | "failed" =
                  rawStatus === "active"
                    ? "active"
                    : rawStatus === "failed"
                      ? "failed"
                      : hasContent
                        ? "done"
                        : "pending";
                return (
                  <ChapterItem
                    key={ch.num}
                    title={/^\d+[\.\s]/.test(ch.title) ? ch.title : `${ch.num}. ${ch.title}`}
                    status={status}
                    onJump={lineIdx >= 0 ? () => scrollToLine(lineIdx) : undefined}
                    onGenerate={status === "pending" ? () => handleGenerateChapter(ch.num, ch.title) : undefined}
                    onRegenerate={status === "done" ? () => handleGenerateChapter(ch.num, ch.title) : undefined}
                    onRetry={status === "failed" ? () => {
                      handleGenerateChapter(ch.num, ch.title);
                    } : undefined}
                  />
                );
              })}
            </div>
          </div>

          {/* Version History */}
          <VersionPanel
            prdId={params.id}
            versions={versions}
            onRestore={handleRestoreVersion}
            onOpen={loadVersions}
          />

          {/* Annotations */}
          <AnnotationPanel
            annotations={annotations}
            stats={annotationStats}
            filter={annotationFilter}
            onFilterChange={setAnnotationFilter}
            loading={isLoadingAnnotations}
            showForm={showAnnotationForm}
            onToggleForm={openAnnotationForm}
            selectedText={selectedTextForAnnotation}
            annotationType={newAnnotationType}
            onTypeChange={setNewAnnotationType}
            content={newAnnotationContent}
            onContentChange={setNewAnnotationContent}
            onSubmit={handleAddAnnotation}
            onCancel={handleAnnotationCancel}
            onResolve={handleResolveAnnotation}
            onDismiss={handleDismissAnnotation}
            onDelete={handleDeleteAnnotation}
            onConvertToTask={handleConvertToTask}
            onAutoReview={handleAutoReview}
            autoReviewLoading={autoReviewLoading}
            onOpen={loadAnnotations}
            open={showAnnotationPanel}
            onToggle={() => {
              const next = !showAnnotationPanel;
              setShowAnnotationPanel(next);
              if (next) loadAnnotations();
            }}
            prdId={params.id}
            onApplyFix={(fixedContent: string) => {
              setContent(fixedContent);
              setAutoSaveStatus("dirty");
            }}
          />

          {/* Revision Tasks */}
          <RevisionTaskPanel
            tasks={tasks}
            stats={taskStats}
            filter={taskFilter}
            onFilterChange={setTaskFilter}
            loading={isLoadingTasks}
            onComplete={handleCompleteTask}
            onUpdateStatus={handleUpdateTaskStatus}
            onDelete={handleDeleteTask}
            onOpen={loadTasks}
            open={showTaskPanel}
            onToggle={() => {
              const next = !showTaskPanel;
              setShowTaskPanel(next);
              if (next) loadTasks();
            }}
          />

        </aside>

        {/* Editor Area */}
        <main className="relative flex flex-1 flex-col overflow-hidden bg-white dark:bg-slate-950">
          {/* Prototype Preview Panel */}
          {showPrototypePanel && prototypeHtml && (
            <PrototypePanel
              html={prototypeHtml}
              device={prototypeDevice}
              onDeviceChange={setPrototypeDevice}
              onClose={() => setShowPrototypePanel(false)}
            />
          )}
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="h-full p-6 space-y-4 bg-white dark:bg-slate-950">
                <SkeletonText lines={4} />
                <SkeletonText lines={3} />
                <SkeletonText lines={5} />
                <SkeletonText lines={2} />
              </div>
            ) : (
              <MarkdownEditor
                value={content}
                onChange={setContent}
                placeholder="开始编写 PRD..."
                isStreaming={isStreaming}
              />
            )}
          </div>

          {/* Right workspace tabs — persistent on desktop, toggle on mobile */}
          {showTaskPanel && (
            <div className="fixed inset-0 z-30 bg-black/20 md:hidden" onClick={() => setShowTaskPanel(false)} />
          )}
          <aside className={`${showTaskPanel ? "fixed right-0 top-0 z-40 h-full w-80 shadow-xl" : "hidden"} md:relative md:block md:w-80 shrink-0 bg-white dark:bg-gray-900`}>
            <WorkspaceTabs
              prdId={params.id}
              projectId={projectId || ""}
              markdown={content || ""}
              versions={versions}
              annotations={annotations}
              onRefreshAnnotations={loadAnnotations}
              onRefreshTasks={loadTasks}
            />
          </aside>
        </main>
      </div>
    </div>
  );
}
