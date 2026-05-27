// 技能状态管理
// 管理技能执行状态和执行历史

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  SkillDefinition,
  SkillExecutionRequest,
  SkillExecutionResponse,
  SkillExecutionRecord,
  SkillExecutionState,
  SkillId,
} from '@/types/skill';
import type { AgentRole } from '@/types/agent';
import {
  skillRegistry,
  validateSkillInput,
  getDefaultInputs,
} from '@/services/skills/registry';

// 扩展执行记录，添加前端展示相关字段
interface ExtendedSkillExecutionRecord extends SkillExecutionRecord {
  // 前端展示用
  formattedOutputHtml?: string;
  isExpanded?: boolean;
  isFavorite?: boolean;
}

interface SkillState extends SkillExecutionState {
  // 选中的技能
  selectedSkill: SkillDefinition | null;

  // 技能输入值
  skillInputs: Record<string, Record<string, unknown>>; // skillId -> inputs

  // 执行历史（扩展版）
  executionHistory: ExtendedSkillExecutionRecord[];

  // 筛选和搜索
  filterRole: AgentRole | string | null;
  filterCategory: SkillDefinition['category'] | null;
  searchQuery: string;

  // 快捷操作
  recentSkills: string[]; // skillIds
  favoriteSkills: string[]; // skillIds

  // Actions
  setSelectedSkill: (skill: SkillDefinition | null) => void;
  setSkillInput: (skillId: string, inputName: string, value: unknown) => void;
  setSkillInputs: (skillId: string, inputs: Record<string, unknown>) => void;
  resetSkillInputs: (skillId: string) => void;
  fillExampleInputs: (skillId: string, exampleId: string) => void;

  // 执行相关
  executeSkill: (
    skillId: string,
    inputs: Record<string, unknown>,
    context?: SkillExecutionRequest['context']
  ) => Promise<SkillExecutionResponse | null>;
  executeSkillAsync: (
    skillId: string,
    inputs: Record<string, unknown>,
    context?: SkillExecutionRequest['context']
  ) => Promise<string | null>; // 返回 executionId

  // 历史记录管理
  addExecutionRecord: (record: ExtendedSkillExecutionRecord) => void;
  updateExecutionRecord: (
    id: string,
    updates: Partial<ExtendedSkillExecutionRecord>
  ) => void;
  deleteExecutionRecord: (id: string) => void;
  clearExecutionHistory: () => void;
  toggleExecutionExpand: (id: string) => void;
  toggleExecutionFavorite: (id: string) => void;

  // 筛选和搜索
  setFilterRole: (role: AgentRole | string | null) => void;
  setFilterCategory: (category: SkillDefinition['category'] | null) => void;
  setSearchQuery: (query: string) => void;
  clearFilters: () => void;

  // 快捷操作
  addRecentSkill: (skillId: string) => void;
  toggleFavoriteSkill: (skillId: string) => void;
  isFavoriteSkill: (skillId: string) => boolean;

  // 获取筛选后的技能列表
  getFilteredSkills: () => SkillDefinition[];
  getSkillHistory: (skillId: string) => ExtendedSkillExecutionRecord[];
}

// 生成唯一ID
const generateExecutionId = () =>
  `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const useSkillStore = create<SkillState>()(
  persist(
    (set, get) => ({
      // State
      selectedSkill: null,
      currentExecution: null,
      executionHistory: [],
      isExecuting: false,
      error: null,
      skillInputs: {},
      filterRole: null,
      filterCategory: null,
      searchQuery: '',
      recentSkills: [],
      favoriteSkills: [],

      // Actions
      setSelectedSkill: (skill) =>
        set({
          selectedSkill: skill,
          error: null,
        }),

      setSkillInput: (skillId, inputName, value) =>
        set((state) => ({
          skillInputs: {
            ...state.skillInputs,
            [skillId]: {
              ...(state.skillInputs[skillId] || {}),
              [inputName]: value,
            },
          },
        })),

      setSkillInputs: (skillId, inputs) =>
        set((state) => ({
          skillInputs: {
            ...state.skillInputs,
            [skillId]: {
              ...(state.skillInputs[skillId] || {}),
              ...inputs,
            },
          },
        })),

      resetSkillInputs: (skillId) =>
        set((state) => {
          const defaults = getDefaultInputs(skillId);
          return {
            skillInputs: {
              ...state.skillInputs,
              [skillId]: defaults,
            },
          };
        }),

      fillExampleInputs: (skillId, exampleId) => {
        const skill = skillRegistry.getSkillById(skillId);
        if (!skill || !skill.examples) return;

        const example = skill.examples.find((e) => e.id === exampleId);
        if (example) {
          set((state) => ({
            skillInputs: {
              ...state.skillInputs,
              [skillId]: {
                ...(state.skillInputs[skillId] || {}),
                ...example.inputs,
              },
            },
          }));
        }
      },

      // 执行技能（同步，等待结果）
      executeSkill: async (skillId, inputs, context) => {
        // 验证输入
        const validation = validateSkillInput(skillId, inputs);
        if (!validation.valid) {
          set({ error: validation.errors.join(', ') });
          return null;
        }

        const skill = skillRegistry.getSkillById(skillId);
        if (!skill) {
          set({ error: `技能 ${skillId} 不存在` });
          return null;
        }

        // 创建执行记录
        const executionId = generateExecutionId();
        const newRecord: ExtendedSkillExecutionRecord = {
          id: executionId,
          skillId,
          skillName: skill.name,
          agentRole: skill.agentRole,
          inputs,
          output: {},
          status: 'running',
          createdAt: new Date(),
        };

        set({
          isExecuting: true,
          error: null,
          currentExecution: newRecord,
        });

        try {
          // 调用 API 执行技能
          const request: SkillExecutionRequest = {
            skillId,
            inputs,
            context,
            options: {
              stream: false,
            },
          };

          const response = await fetch('/api/v1/skills/execute', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
          });

          if (!response.ok) {
            throw new Error(`执行失败: ${response.statusText}`);
          }

          const result: SkillExecutionResponse = await response.json();

          // 更新执行记录
          const completedRecord: ExtendedSkillExecutionRecord = {
            ...newRecord,
            status: result.success ? 'completed' : 'failed',
            output: result.output,
            formattedOutput: result.formattedOutput,
            completedAt: new Date(),
            executionTime: result.executionTime,
            error: result.error,
          };

          set((state) => ({
            isExecuting: false,
            currentExecution: completedRecord,
            executionHistory: [completedRecord, ...state.executionHistory].slice(0, 100), // 保留最近100条
          }));

          // 添加到最近使用
          get().addRecentSkill(skillId);

          return result;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : '执行过程中发生错误';

          const failedRecord: ExtendedSkillExecutionRecord = {
            ...newRecord,
            status: 'failed',
            completedAt: new Date(),
            error: errorMessage,
          };

          set((state) => ({
            isExecuting: false,
            currentExecution: failedRecord,
            executionHistory: [failedRecord, ...state.executionHistory].slice(0, 100),
            error: errorMessage,
          }));

          return null;
        }
      },

      // 异步执行技能（返回 executionId，通过 SSE 或轮询获取结果）
      executeSkillAsync: async (skillId, inputs, context) => {
        const validation = validateSkillInput(skillId, inputs);
        if (!validation.valid) {
          set({ error: validation.errors.join(', ') });
          return null;
        }

        const skill = skillRegistry.getSkillById(skillId);
        if (!skill) {
          set({ error: `技能 ${skillId} 不存在` });
          return null;
        }

        const executionId = generateExecutionId();
        const newRecord: ExtendedSkillExecutionRecord = {
          id: executionId,
          skillId,
          skillName: skill.name,
          agentRole: skill.agentRole,
          inputs,
          output: {},
          status: 'pending',
          createdAt: new Date(),
        };

        set((state) => ({
          executionHistory: [newRecord, ...state.executionHistory],
          currentExecution: newRecord,
        }));

        // 发起异步执行请求
        try {
          const request: SkillExecutionRequest = {
            skillId,
            inputs,
            context,
            options: {
              stream: true,
            },
          };

          const response = await fetch('/api/v1/skills/execute-async', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
          });

          if (!response.ok) {
            throw new Error(`启动异步执行失败: ${response.statusText}`);
          }

          const { executionId: returnedId } = await response.json();

          // 更新状态为运行中
          set((state) => ({
            executionHistory: state.executionHistory.map((record) =>
              record.id === executionId
                ? { ...record, status: 'running' as const }
                : record
            ),
          }));

          get().addRecentSkill(skillId);

          return returnedId || executionId;
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : '启动执行失败';

          set((state) => ({
            executionHistory: state.executionHistory.map((record) =>
              record.id === executionId
                ? { ...record, status: 'failed' as const, error: errorMessage }
                : record
            ),
            error: errorMessage,
          }));

          return null;
        }
      },

      // 历史记录管理
      addExecutionRecord: (record) =>
        set((state) => ({
          executionHistory: [record, ...state.executionHistory].slice(0, 100),
        })),

      updateExecutionRecord: (id, updates) =>
        set((state) => ({
          executionHistory: state.executionHistory.map((record) =>
            record.id === id ? { ...record, ...updates } : record
          ),
          currentExecution:
            state.currentExecution?.id === id
              ? { ...state.currentExecution, ...updates }
              : state.currentExecution,
        })),

      deleteExecutionRecord: (id) =>
        set((state) => ({
          executionHistory: state.executionHistory.filter((record) => record.id !== id),
        })),

      clearExecutionHistory: () =>
        set({
          executionHistory: [],
          currentExecution: null,
        }),

      toggleExecutionExpand: (id) =>
        set((state) => ({
          executionHistory: state.executionHistory.map((record) =>
            record.id === id ? { ...record, isExpanded: !record.isExpanded } : record
          ),
        })),

      toggleExecutionFavorite: (id) =>
        set((state) => ({
          executionHistory: state.executionHistory.map((record) =>
            record.id === id ? { ...record, isFavorite: !record.isFavorite } : record
          ),
        })),

      // 筛选和搜索
      setFilterRole: (role) => set({ filterRole: role }),
      setFilterCategory: (category) => set({ filterCategory: category }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      clearFilters: () =>
        set({
          filterRole: null,
          filterCategory: null,
          searchQuery: '',
        }),

      // 快捷操作
      addRecentSkill: (skillId) =>
        set((state) => ({
          recentSkills: [
            skillId,
            ...state.recentSkills.filter((id) => id !== skillId),
          ].slice(0, 10), // 保留最近10个
        })),

      toggleFavoriteSkill: (skillId) =>
        set((state) => {
          const isFavorite = state.favoriteSkills.includes(skillId);
          return {
            favoriteSkills: isFavorite
              ? state.favoriteSkills.filter((id) => id !== skillId)
              : [...state.favoriteSkills, skillId],
          };
        }),

      isFavoriteSkill: (skillId) => {
        return get().favoriteSkills.includes(skillId);
      },

      // 获取筛选后的技能列表
      getFilteredSkills: () => {
        const { filterRole, filterCategory, searchQuery } = get();

        let skills = skillRegistry.getAllSkills();

        if (filterRole) {
          skills = skills.filter((skill) => skill.agentRole === filterRole);
        }

        if (filterCategory) {
          skills = skills.filter((skill) => skill.category === filterCategory);
        }

        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          skills = skills.filter(
            (skill) =>
              skill.name.toLowerCase().includes(query) ||
              skill.description.toLowerCase().includes(query) ||
              skill.tags?.some((tag) => tag.toLowerCase().includes(query))
          );
        }

        return skills;
      },

      // 获取特定技能的历史记录
      getSkillHistory: (skillId) => {
        return get().executionHistory.filter((record) => record.skillId === skillId);
      },
    }),
    {
      name: 'aipm-skills',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        executionHistory: state.executionHistory,
        skillInputs: state.skillInputs,
        recentSkills: state.recentSkills,
        favoriteSkills: state.favoriteSkills,
      }),
    }
  )
);

// 导出便捷 hooks
export const useSkillExecution = (skillId?: string) => {
  const store = useSkillStore();

  return {
    selectedSkill: store.selectedSkill,
    isExecuting: store.isExecuting,
    currentExecution: store.currentExecution,
    error: store.error,
    skillInputs: skillId ? store.skillInputs[skillId] || {} : {},
    history: skillId ? store.getSkillHistory(skillId) : [],

    setSelectedSkill: store.setSelectedSkill,
    setSkillInput: (name: string, value: unknown) =>
      skillId && store.setSkillInput(skillId, name, value),
    executeSkill: (inputs: Record<string, unknown>, context?: SkillExecutionRequest['context']) =>
      skillId ? store.executeSkill(skillId, inputs, context) : Promise.resolve(null),
    resetInputs: () => skillId && store.resetSkillInputs(skillId),
  };
};
