import { create } from 'zustand';
import { projectApi, prdApi, type Project, type ProjectDetail, type PRD } from '@/lib/api';

// Utility: trigger browser download for blob content (kept outside store to avoid side effects)
export function downloadFile(content: string, filename: string, contentType: string) {
  const blob = new Blob([content], { type: contentType });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

interface ProjectState {
  // State
  projects: Project[];
  currentProject: ProjectDetail | null;
  currentPRD: PRD | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: {
    name: string;
    description?: string;
    industry?: string;
  }) => Promise<Project>;
  updateProject: (id: string, data: {
    name?: string;
    description?: string;
    industry?: string;
    status?: string;
  }) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;

  // PRD Actions
  fetchPRD: (id: string) => Promise<void>;
  createPRD: (data: {
    project_id: string;
    title: string;
    template?: string;
  }) => Promise<PRD>;
  updatePRD: (id: string, data: {
    title?: string;
    content?: Record<string, unknown>;
    markdown?: string;
    status?: string;
  }) => Promise<void>;
  generateChapter: (id: string, chapter: string, prompt: string) => Promise<{
    chapter: string;
    content: string;
    markdown: string;
  }>;
  exportPRD: (id: string, format: 'markdown' | 'json') => Promise<{ format: string; content: string; filename: string; encoding?: string }>;

  clearError: () => void;
  clearCurrentProject: () => void;
  clearCurrentPRD: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  currentPRD: null,
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true, error: null });
    try {
      const { items: projects } = await projectApi.list();
      set({ projects, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch projects',
        isLoading: false,
      });
    }
  },

  fetchProject: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectApi.get(id);
      set({ currentProject: project, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch project',
        isLoading: false,
      });
    }
  },

  createProject: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectApi.create(data);
      set((state) => ({
        projects: [project, ...state.projects],
        isLoading: false,
      }));
      return project;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create project',
        isLoading: false,
      });
      throw error;
    }
  },

  updateProject: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectApi.update(id, data);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? project : p)),
        currentProject: state.currentProject?.id === id
          ? { ...state.currentProject, ...project }
          : state.currentProject,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update project',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteProject: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await projectApi.delete(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete project',
        isLoading: false,
      });
      throw error;
    }
  },

  fetchPRD: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const prd = await prdApi.get(id);
      set({ currentPRD: prd, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch PRD',
        isLoading: false,
      });
    }
  },

  createPRD: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const prd = await prdApi.create(data);
      set((state) => ({
        currentProject: state.currentProject
          ? {
              ...state.currentProject,
              prds: [
                ...state.currentProject.prds,
                {
                  id: prd.id,
                  title: prd.title,
                  version: prd.version,
                  status: prd.status,
                  created_at: prd.created_at,
                },
              ],
            }
          : null,
        isLoading: false,
      }));
      return prd;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create PRD',
        isLoading: false,
      });
      throw error;
    }
  },

  updatePRD: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const prd = await prdApi.update(id, data);
      set((state) => ({
        currentPRD: state.currentPRD?.id === id ? prd : state.currentPRD,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update PRD',
        isLoading: false,
      });
      throw error;
    }
  },

  generateChapter: async (id, chapter, prompt) => {
    set({ isLoading: true, error: null });
    try {
      const result = await prdApi.generate(id, { chapter, prompt });
      // Refresh PRD to get updated content
      const prd = await prdApi.get(id);
      set({ currentPRD: prd, isLoading: false });
      return result;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to generate chapter',
        isLoading: false,
      });
      throw error;
    }
  },

  exportPRD: async (id, format) => {
    set({ isLoading: true, error: null });
    try {
      const result = await prdApi.export(id, format);
      set({ isLoading: false });
      return result;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to export PRD',
        isLoading: false,
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),
  clearCurrentProject: () => set({ currentProject: null }),
  clearCurrentPRD: () => set({ currentPRD: null }),
}));
