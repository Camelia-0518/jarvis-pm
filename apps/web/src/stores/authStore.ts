import { create } from 'zustand';
import { authApi, type User } from '@/lib/api';

const DEFAULT_USER: User = {
  id: 'single-user',
  email: 'admin@jarvis.pm',
  name: 'Admin',
  role: 'admin',
  is_active: true,
};

interface AuthState {
  // State
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions (kept for compatibility, but no-op in single-user mode)
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: DEFAULT_USER,
  isAuthenticated: true,
  isLoading: false,
  error: null,

  login: async () => {
    // Single-user mode: no login required
    set({ user: DEFAULT_USER, isAuthenticated: true, error: null });
  },

  register: async () => {
    // Single-user mode: no registration required
    set({ user: DEFAULT_USER, isAuthenticated: true, error: null });
  },

  logout: () => {
    // Single-user mode: keep default user
    set({ user: DEFAULT_USER, isAuthenticated: true, error: null });
  },

  fetchUser: async () => {
    if (!get().isAuthenticated) return;
    set({ isLoading: true });
    try {
      const user = await authApi.getCurrentUser();
      set({ user, isLoading: false });
    } catch {
      set({ user: DEFAULT_USER, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
