import { create } from 'zustand';
import type {
  Agent,
  AgentRole,
  AgentReasoning,
  AgentConflict,
  AgentMessage,
  Workflow,
} from '@/types/agent';
import { AGENT_CONFIGS } from '@/types/agent';

interface AgentStore {
  // Agent 列表
  agents: Agent[];

  // 决策日志
  reasoningLogs: AgentReasoning[];

  // 冲突列表
  conflicts: AgentConflict[];

  // 消息列表
  messages: AgentMessage[];

  // 工作流
  workflows: Workflow[];
  currentWorkflowId: string | null;

  // 进度
  overallProgress: number;

  // Actions
  initializeAgents: () => void;
  updateAgentStatus: (agentId: string, status: Agent['status'], currentTask?: string) => void;
  addReasoning: (reasoning: Omit<AgentReasoning, 'id' | 'timestamp'>) => void;
  addConflict: (conflict: Omit<AgentConflict, 'id' | 'resolved'>) => void;
  resolveConflict: (conflictId: string, resolution: string) => void;
  addMessage: (message: Omit<AgentMessage, 'id' | 'timestamp'>) => void;
  setWorkflow: (workflow: Workflow) => void;
  updateProgress: (progress: number) => void;
  clearLogs: () => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  reasoningLogs: [],
  conflicts: [],
  messages: [],
  workflows: [],
  currentWorkflowId: null,
  overallProgress: 0,

  initializeAgents: () => {
    const agents: Agent[] = Object.entries(AGENT_CONFIGS).map(([role, config]) => ({
      id: `agent-${role}`,
      ...config,
      status: 'idle',
    }));
    set({ agents });
  },

  updateAgentStatus: (agentId, status, currentTask) => {
    set((state) => ({
      agents: state.agents.map((agent) =>
        agent.id === agentId
          ? { ...agent, status, currentTask: currentTask || agent.currentTask }
          : agent
      ),
    }));
  },

  addReasoning: (reasoning) => {
    const newReasoning: AgentReasoning = {
      ...reasoning,
      id: `reasoning-${Date.now()}`,
      timestamp: new Date(),
    };
    set((state) => ({
      reasoningLogs: [...state.reasoningLogs, newReasoning],
    }));
  },

  addConflict: (conflict) => {
    const newConflict: AgentConflict = {
      ...conflict,
      id: `conflict-${Date.now()}`,
      resolved: false,
    };
    set((state) => ({
      conflicts: [...state.conflicts, newConflict],
    }));
  },

  resolveConflict: (conflictId, resolution) => {
    set((state) => ({
      conflicts: state.conflicts.map((c) =>
        c.id === conflictId ? { ...c, resolved: true, resolution } : c
      ),
    }));
  },

  addMessage: (message) => {
    const newMessage: AgentMessage = {
      ...message,
      id: `msg-${Date.now()}`,
      timestamp: new Date(),
    };
    set((state) => ({
      messages: [...state.messages, newMessage],
    }));
  },

  setWorkflow: (workflow) => {
    set((state) => ({
      workflows: [...state.workflows.filter((w) => w.id !== workflow.id), workflow],
      currentWorkflowId: workflow.id,
    }));
  },

  updateProgress: (progress) => {
    set({ overallProgress: progress });
  },

  clearLogs: () => {
    set({
      reasoningLogs: [],
      conflicts: [],
      messages: [],
      overallProgress: 0,
    });
  },
}));
