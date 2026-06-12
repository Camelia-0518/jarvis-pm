import { create } from 'zustand';
import { promptApi, type PromptTemplate } from '@/lib/api';
import { setLoading, setError } from '@/lib/storeHelpers';

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
    setLoading(set);
    try {
      const result = await promptApi.list(params);
      set({ prompts: result.items, isLoading: false });
    } catch (error) {
      setError(set, error, 'Failed to fetch prompts');
    }
  },

  fetchVersions: async (name) => {
    setLoading(set);
    try {
      const versions = await promptApi.versions(name);
      set({ versions, isLoading: false });
    } catch (error) {
      setError(set, error, "Failed to fetch versions");
    }
  },

  createPrompt: async (data) => {
    setLoading(set);
    try {
      await promptApi.create(data);
      await get().fetchPrompts();
    } catch (error) {
      setError(set, error, "Failed to create prompt");
      throw error;
    }
  },

  activatePrompt: async (id) => {
    setLoading(set);
    try {
      await promptApi.activate(id);
      await get().fetchPrompts();
    } catch (error) {
      setError(set, error, "Failed to activate prompt");
    }
  },

  deletePrompt: async (id) => {
    setLoading(set);
    try {
      await promptApi.delete(id);
      await get().fetchPrompts();
    } catch (error) {
      setError(set, error, "Failed to delete prompt");
    }
  },

  clearError: () => set({ error: null }),
}));
