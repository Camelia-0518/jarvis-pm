import { create } from 'zustand';
import { promptApi, type PromptTemplate } from '@/lib/api';

interface PromptState {
  prompts: PromptTemplate[];
  versions: PromptTemplate[];
  isLoading: boolean;
  error: string | null;

  fetchPrompts: (params?: { name?: string; tag?: string; is_active?: boolean; page?: number; limit?: number }) => Promise<void>;
  fetchVersions: (name: string) => Promise<void>;
  createPrompt: (data: {
    name: string;
    content: string;
    version?: string;
    description?: string;
    tags?: string[];
  }) => Promise<void>;
  activatePrompt: (id: string) => Promise<void>;
  deletePrompt: (id: string) => Promise<void>;
  clearError: () => void;
}

export const usePromptStore = create<PromptState>((set, get) => ({
  prompts: [],
  versions: [],
  isLoading: false,
  error: null,

  fetchPrompts: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const result = await promptApi.list(params);
      set({ prompts: result.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch prompts',
        isLoading: false,
      });
    }
  },

  fetchVersions: async (name) => {
    set({ isLoading: true, error: null });
    try {
      const versions = await promptApi.versions(name);
      set({ versions, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch versions',
        isLoading: false,
      });
    }
  },

  createPrompt: async (data) => {
    set({ isLoading: true, error: null });
    try {
      await promptApi.create(data);
      await get().fetchPrompts();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create prompt',
        isLoading: false,
      });
      throw error;
    }
  },

  activatePrompt: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await promptApi.activate(id);
      await get().fetchPrompts();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to activate prompt',
        isLoading: false,
      });
    }
  },

  deletePrompt: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await promptApi.delete(id);
      await get().fetchPrompts();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete prompt',
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
