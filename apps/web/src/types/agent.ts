// Agent 类型定义

export type AgentRole = 'ceo' | 'designer' | 'engManager' | 'qaEngineer' | 'orchestrator';

export interface Agent {
  id: string;
  role: AgentRole;
  name: string;
  avatar: string;
  description: string;
  skills: string[];
  status: 'idle' | 'working' | 'completed' | 'error';
  currentTask?: string;
}

export interface AgentReasoning {
  id: string;
  agentId: string;
  agentRole: AgentRole;
  action: string;
  confidence: number; // 0-1
  reasoning: string;
  evidence: string[];
  timestamp: Date;
  input?: string;
  output?: string;
}

export interface AgentConflict {
  id: string;
  agentA: AgentRole;
  agentB: AgentRole;
  issue: string;
  severity: 'low' | 'medium' | 'high';
  resolved: boolean;
  resolution?: string;
}

export interface AgentMessage {
  id: string;
  agentId: string;
  agentRole: AgentRole;
  content: string;
  type: 'thinking' | 'suggestion' | 'question' | 'decision';
  timestamp: Date;
}

export interface WorkflowNode {
  id: string;
  type: AgentRole;
  position: { x: number; y: number };
  data: {
    agent: Agent;
    status: 'pending' | 'running' | 'completed' | 'error';
    progress: number;
    output?: string;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: 'default' | 'conditional';
  label?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  status: 'draft' | 'running' | 'paused' | 'completed';
  createdAt: Date;
  updatedAt: Date;
}

// 预置工作流模板
export const WORKFLOW_TEMPLATES = [
  {
    id: 'from-scratch',
    name: '从 0 开发新功能',
    description: '完整的从需求到 PRD 的工作流',
    nodes: [
      { role: 'ceo', x: 100, y: 100 },
      { role: 'designer', x: 400, y: 100 },
      { role: 'engManager', x: 700, y: 100 },
      { role: 'qaEngineer', x: 1000, y: 100 },
    ],
    edges: [
      { source: 'ceo', target: 'designer', label: '需求分析' },
      { source: 'designer', target: 'engManager', label: '设计评审' },
      { source: 'engManager', target: 'qaEngineer', label: '技术方案' },
    ],
  },
  {
    id: 'security-review',
    name: '安全审查流程',
    description: '全面的安全风险评估',
    nodes: [
      { role: 'engManager', x: 100, y: 100 },
      { role: 'qaEngineer', x: 400, y: 100 },
      { role: 'ceo', x: 700, y: 100 },
    ],
    edges: [
      { source: 'engManager', target: 'qaEngineer', label: '技术审计' },
      { source: 'qaEngineer', target: 'ceo', label: '风险评估' },
    ],
  },
  {
    id: 'prd-review',
    name: 'PRD 评审流程',
    description: '多角色 PRD 评审',
    nodes: [
      { role: 'ceo', x: 100, y: 100 },
      { role: 'designer', x: 400, y: 50 },
      { role: 'engManager', x: 400, y: 150 },
      { role: 'qaEngineer', x: 700, y: 100 },
    ],
    edges: [
      { source: 'ceo', target: 'designer', label: '产品评审' },
      { source: 'ceo', target: 'engManager', label: '技术评审' },
      { source: 'designer', target: 'qaEngineer', label: '设计确认' },
      { source: 'engManager', target: 'qaEngineer', label: '技术确认' },
    ],
  },
];

// Agent 配置
export const AGENT_CONFIGS: Record<AgentRole, Omit<Agent, 'id' | 'status'>> = {
  ceo: {
    role: 'ceo',
    name: '产品战略官',
    avatar: '👔',
    description: '负责产品战略、需求分析和商业逻辑',
    skills: ['brainstorming', 'business-model', 'pricing-strategy', 'scope-manager'],
  },
  designer: {
    role: 'designer',
    name: '体验设计师',
    avatar: '🎨',
    description: '负责 UI/UX 设计和用户流程',
    skills: ['frontend-design', 'ux-designer', 'prototype-prompt-generator'],
  },
  engManager: {
    role: 'engManager',
    name: '工程经理',
    avatar: '⚙️',
    description: '负责技术架构和代码实现',
    skills: ['tech-architect', 'code-developer', 'api-design', 'refactoring'],
  },
  qaEngineer: {
    role: 'qaEngineer',
    name: '质量工程师',
    avatar: '🔍',
    description: '负责测试策略和质量保证',
    skills: ['security-audit', 'security-scanner', 'test-validator', 'auto-test'],
  },
  orchestrator: {
    role: 'orchestrator',
    name: '任务协调器',
    avatar: '🎭',
    description: '协调各 Agent 协作，分配任务',
    skills: ['all'],
  },
};
