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
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.login(email, password);
      const user = await authApi.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '登录失败';
      // Fallback: if backend in single-user mode, auto-login
      try {
        const user = await authApi.getCurrentUser();
        if (user && user.id) {
          set({ user, isAuthenticated: true, isLoading: false, error: null });
          return;
        }
      } catch { /* fall through */ }
      set({ isLoading: false, error: msg });
      throw e;
    }
  },

  register: async (email: string, password: string, name: string) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register(email, password, name);
      const user = await authApi.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '注册失败';
      set({ isLoading: false, error: msg });
      throw e;
    }
  },

  logout: () => {
    authApi.logout();
    set({ user: null, isAuthenticated: false, error: null });
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const user = await authApi.getCurrentUser();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      // Fallback to single-user mode
      set({ user: DEFAULT_USER, isAuthenticated: true, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
