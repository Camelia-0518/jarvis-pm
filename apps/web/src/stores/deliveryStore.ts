import { create } from 'zustand';
import { deliveryApi, type DeliveryPlanDetail, type DeliveryPlanSummary, type DeliveryDashboardData } from '@/lib/api';

interface DeliveryState {
  // List state
  plans: DeliveryPlanSummary[];
  isLoadingList: boolean;
  listError: string | null;

  // Current plan
  currentPlan: DeliveryPlanDetail | null;
  isLoadingPlan: boolean;
  planError: string | null;

  // Generation state
  isGenerating: boolean;
  generationError: string | null;
  generationProgress: string;

  // Dashboard
  dashboard: DeliveryDashboardData | null;
  isLoadingDashboard: boolean;

  // Actions
  fetchPlans: (projectId?: string) => Promise<void>;
  fetchPlan: (id: string) => Promise<void>;
  generatePlan: (params: { project_id: string; prd_id?: string; industry?: string; team_size?: number }) => Promise<string | null>;
  generateSingle: (params: { project_id: string; agent_type: 'delivery_planner' | 'risk_manager' | 'stakeholder_coordinator' }) => Promise<Record<string, unknown> | null>;
  updatePlan: (id: string, data: { status?: string; title?: string }) => Promise<void>;
  deletePlan: (id: string) => Promise<void>;
  fetchDashboard: (projectId?: string) => Promise<void>;
  reset: () => void;
}

export const useDeliveryStore = create<DeliveryState>((set) => ({
  plans: [],
  isLoadingList: false,
  listError: null,

  currentPlan: null,
  isLoadingPlan: false,
  planError: null,

  isGenerating: false,
  generationError: null,
  generationProgress: '',

  dashboard: null,
  isLoadingDashboard: false,

  fetchPlans: async (projectId) => {
    set({ isLoadingList: true, listError: null });
    try {
      const result = await deliveryApi.list({ project_id: projectId, limit: 50 });
      set({ plans: result.items, isLoadingList: false });
    } catch (err) {
      set({ listError: err instanceof Error ? err.message : 'Failed to load plans', isLoadingList: false });
    }
  },

  fetchPlan: async (id: string) => {
    set({ isLoadingPlan: true, planError: null });
    try {
      const plan = await deliveryApi.get(id);
      set({ currentPlan: plan, isLoadingPlan: false });
    } catch (err) {
      set({ planError: err instanceof Error ? err.message : 'Failed to load plan', isLoadingPlan: false });
    }
  },

  generatePlan: async (params) => {
    set({ isGenerating: true, generationError: null, generationProgress: '正在生成交付计划...' });
    try {
      set({ generationProgress: '正在生成WBS与里程碑...' });
      const plan = await deliveryApi.generate(params);
      set({ generationProgress: '交付计划生成完成！', isGenerating: false });
      return plan.id;
    } catch (err) {
      set({
        generationError: err instanceof Error ? err.message : 'Generation failed',
        isGenerating: false,
      });
      return null;
    }
  },

  generateSingle: async (params) => {
    set({ isGenerating: true, generationError: null, generationProgress: '正在生成...' });
    try {
      const result = await deliveryApi.generateSingle(params);
      set({ isGenerating: false });
      return result.data;
    } catch (err) {
      set({
        generationError: err instanceof Error ? err.message : 'Generation failed',
        isGenerating: false,
      });
      return null;
    }
  },

  updatePlan: async (id, data) => {
    try {
      await deliveryApi.update(id, data);
    } catch (err) {
      console.error('Failed to update plan:', err);
    }
  },

  deletePlan: async (id) => {
    try {
      await deliveryApi.delete(id);
      set((state) => ({ plans: state.plans.filter((p) => p.id !== id) }));
    } catch (err) {
      console.error('Failed to delete plan:', err);
    }
  },

  fetchDashboard: async (projectId) => {
    set({ isLoadingDashboard: true });
    try {
      const data = await deliveryApi.getDashboard(projectId);
      set({ dashboard: data, isLoadingDashboard: false });
    } catch {
      set({ isLoadingDashboard: false });
    }
  },

  reset: () => set({
    currentPlan: null,
    isLoadingPlan: false,
    planError: null,
    isGenerating: false,
    generationError: null,
    generationProgress: '',
  }),
}));
