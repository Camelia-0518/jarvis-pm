import { create } from 'zustand';
import { prdApi, aiApi, type ChecklistItem } from '@/lib/api';

export type ChecklistMap = Record<string, { checked: boolean; note: string }>;

interface PRDState {
  // Core document state
  content: string;
  documentTitle: string;
  status: string;
  projectId: string | null;
  chapters: { num: string; title: string }[];

  // Loading & save state
  isLoading: boolean;
  isSaving: boolean;
  autoSaveStatus: 'idle' | 'saved' | 'dirty';
  chapterStatus: Record<string, 'pending' | 'active' | 'done' | 'failed'>;

  // Review state
  checklistItems: ChecklistItem[];
  checklistState: ChecklistMap;
  checklistResult: string | null;
  aiReviewLoading: boolean;

  // Actions
  setContent: (content: string | ((prev: string) => string)) => void;
  setDocumentTitle: (title: string) => void;
  setStatus: (status: string) => void;
  setProjectId: (id: string | null) => void;
  setChapters: (chapters: { num: string; title: string }[]) => void;

  setIsLoading: (loading: boolean) => void;
  setIsSaving: (saving: boolean) => void;
  setAutoSaveStatus: (status: 'idle' | 'saved' | 'dirty') => void;
  setChapterStatus: (status: Record<string, 'pending' | 'active' | 'done' | 'failed'>) => void;

  setChecklistItems: (items: ChecklistItem[]) => void;
  setChecklistState: (state: ChecklistMap | ((prev: ChecklistMap) => ChecklistMap)) => void;
  setChecklistResult: (result: string | null) => void;
  setAiReviewLoading: (loading: boolean) => void;

  // Compound actions
  loadPRD: (id: string) => Promise<void>;
  savePRD: (id: string) => Promise<void>;
  runAIReview: (checklistItems: ChecklistItem[], projectId: string | null, prdId: string) => Promise<void>;
  reset: () => void;
}

export const usePRDStore = create<PRDState>((set, get) => ({
  // Initial state
  content: '',
  documentTitle: '未命名 PRD',
  status: 'draft',
  projectId: null,
  chapters: [],

  isLoading: true,
  isSaving: false,
  autoSaveStatus: 'idle',
  chapterStatus: {},

  checklistItems: [],
  checklistState: {},
  checklistResult: null,
  aiReviewLoading: false,

  // Simple setters
  setContent: (content) => set((state) => ({
    content: typeof content === 'function' ? (content as (prev: string) => string)(state.content) : content,
    autoSaveStatus: 'dirty' as const,
  })),
  setDocumentTitle: (documentTitle) => set({ documentTitle }),
  setStatus: (status) => set({ status }),
  setProjectId: (projectId) => set({ projectId }),
  setChapters: (chapters) => set({ chapters }),

  setIsLoading: (isLoading) => set({ isLoading }),
  setIsSaving: (isSaving) => set({ isSaving }),
  setAutoSaveStatus: (autoSaveStatus) => set({ autoSaveStatus }),
  setChapterStatus: (chapterStatus) => set({ chapterStatus }),

  setChecklistItems: (checklistItems) => set({ checklistItems }),
  setChecklistState: (checklistState) => set((state) => ({
    checklistState: typeof checklistState === 'function'
      ? (checklistState as (prev: ChecklistMap) => ChecklistMap)(state.checklistState)
      : checklistState,
  })),
  setChecklistResult: (checklistResult) => set({ checklistResult }),
  setAiReviewLoading: (aiReviewLoading) => set({ aiReviewLoading }),

  // Load PRD
  loadPRD: async (id: string) => {
    set({ isLoading: true });
    try {
      const prd = await prdApi.get(id);
      // Extract chapters from structured content, fall back to parsing markdown
      const prdContent = (prd as unknown as Record<string, unknown>).content as Record<string, unknown> | undefined;
      const prdChapters = prdContent?.chapters as Record<string, { title?: string }> | undefined;
      let chapters: { num: string; title: string }[] = [];
      if (prdChapters && typeof prdChapters === "object") {
        chapters = Object.entries(prdChapters)
          .sort(([a], [b]) => parseInt(a) - parseInt(b))
          .map(([num, ch]) => ({ num, title: ch?.title || `Chapter ${num}` }));
      }
      set({
        content: prd.markdown || '',
        documentTitle: prd.title || '未命名 PRD',
        status: prd.status || 'draft',
        projectId: prd.project_id || null,
        chapters,
        isLoading: false,
      });
    } catch (err) {
      set({ isLoading: false });
      throw err;
    }
  },

  // Save PRD
  savePRD: async (id: string) => {
    const { content, documentTitle } = get();
    set({ isSaving: true, autoSaveStatus: 'idle' });
    try {
      await prdApi.update(id, { title: documentTitle, markdown: content });
      set({ isSaving: false, autoSaveStatus: 'saved' });
    } catch (err) {
      set({ isSaving: false });
      throw err;
    }
  },

  // Run AI Review (chapter-by-chapter)
  runAIReview: async (checklistItems, projectId, prdId) => {
    const { content, checklistState } = get();
    if (!projectId || checklistItems.length === 0 || !content.trim()) {
      set({ checklistResult: '请先加载检查清单并确保 PRD 有内容' });
      setTimeout(() => set({ checklistResult: null }), 3000);
      return;
    }

    set({ aiReviewLoading: true, checklistResult: 'AI 正在分章评审中，请稍候...' });

    try {
      // Split PRD into chapters
      const chunks: string[] = [];
      const chapterRegex = /^#{2,3}\s+.+$/gm;
      const matches = Array.from(content.matchAll(chapterRegex));
      if (matches.length === 0) {
        chunks.push(content);
      } else {
        for (let i = 0; i < matches.length; i++) {
          const start = matches[i].index!;
          const end = i < matches.length - 1 ? matches[i + 1].index! : content.length;
          const chapter = content.slice(start, end).trim();
          if (chapter.length > 3500) {
            for (let j = 0; j < chapter.length; j += 3500) {
              chunks.push(chapter.slice(j, j + 3500));
            }
          } else {
            chunks.push(chapter);
          }
        }
      }

      const itemsText = checklistItems
        .map((i) => `${i.id}. [${i.required ? '必填' : '可选'}] ${i.text}`)
        .join('\n');

      const allResults = await Promise.all(
        chunks.map(async (chunk, idx) => {
          const prompt = `你是一位资深产品经理评审专家。请严格根据以下 PRD 章节内容，对检查清单逐项评估。\n\nPRD 章节（第${idx + 1}/${chunks.length}章）：\n${chunk}\n\n检查清单：\n${itemsText}\n\n请逐条判断该章节是否明确满足该项要求。只返回严格的 JSON 数组，不要任何其他文字：\n[{"id":"m1","passed":true,"reason":"简要说明"},{"id":"m2","passed":false,"reason":"未提及..."}]`;
          const res = await aiApi.chat(prompt, { max_tokens: 4000 });
          let jsonStr = res.response || '';
          const arrMatch = jsonStr.match(/\[\s\S]*\]/);
          if (arrMatch) jsonStr = arrMatch[0];
          return JSON.parse(jsonStr) as Array<{ id: string; passed: boolean; reason: string }>;
        })
      );

      const merged: ChecklistMap = { ...checklistState };
      allResults.flat().forEach((r) => {
        const existing = merged[r.id];
        if (existing) {
          if (existing.checked && !r.passed) {
            merged[r.id] = { checked: false, note: r.reason || '' };
          }
        } else if (checklistItems.find((i) => i.id === r.id)) {
          merged[r.id] = { checked: r.passed, note: r.reason || '' };
        }
      });

      if (projectId) {
        localStorage.setItem(`review-checklist-${projectId}-${prdId}`, JSON.stringify(merged));
      }

      const passedCount = Object.values(merged).filter((r) => r.checked).length;
      set({
        checklistState: merged,
        checklistResult: `AI 分章评审完成：${passedCount}/${checklistItems.length} 项通过（共${chunks.length}章）`,
        aiReviewLoading: false,
      });
      setTimeout(() => set({ checklistResult: null }), 5000);
    } catch (err: unknown) {
      set({
        checklistResult: 'AI 评审失败：' + (err instanceof Error ? err.message : '解析错误'),
        aiReviewLoading: false,
      });
      setTimeout(() => set({ checklistResult: null }), 5000);
    }
  },

  reset: () => set({
    content: '',
    documentTitle: '未命名 PRD',
    status: 'draft',
    projectId: null,
    chapters: [],
    isLoading: true,
    isSaving: false,
    autoSaveStatus: 'idle',
    chapterStatus: {},
    checklistItems: [],
    checklistState: {},
    checklistResult: null,
    aiReviewLoading: false,
  }),
}));
