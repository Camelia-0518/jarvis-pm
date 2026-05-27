// 技能系统类型定义
// 参考 AI_EMPLOYEE_UPGRADE.md

import type { AgentRole } from './agent';

// 参数类型
export type SkillParameterType = 'string' | 'number' | 'boolean' | 'select' | 'textarea' | 'array';

// 技能参数定义
export interface SkillParameter {
  name: string;
  label: string;
  type: SkillParameterType;
  description?: string;
  required?: boolean;
  defaultValue?: unknown;
  options?: { label: string; value: string }[]; // 用于 select 类型
  placeholder?: string;
  min?: number; // 用于 number 类型
  max?: number;
}

// 技能定义
export interface SkillDefinition {
  id: string;
  name: string;
  description: string;
  agentRole: AgentRole | string; // 所属 Agent
  category: 'analysis' | 'design' | 'development' | 'review' | 'medical' | 'planning';
  parameters: SkillParameter[];
  outputSchema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
  examples?: SkillExample[];
  icon?: string;
  tags?: string[];
}

// 技能示例
export interface SkillExample {
  id: string;
  name: string;
  description: string;
  inputs: Record<string, unknown>;
  outputPreview?: string;
}

// 技能执行请求
export interface SkillExecutionRequest {
  skillId: string;
  inputs: Record<string, unknown>;
  context?: {
    projectId?: string;
    conversationId?: string;
    userId?: string;
  };
  options?: {
    temperature?: number;
    maxTokens?: number;
    stream?: boolean;
  };
}

// 技能执行响应
export interface SkillExecutionResponse {
  success: boolean;
  skillId: string;
  output: Record<string, unknown>;
  formattedOutput?: string; // Markdown 格式的输出
  executionTime: number; // 毫秒
  tokenUsage?: {
    prompt: number;
    completion: number;
    total: number;
  };
  error?: string;
}

// 技能执行记录
export interface SkillExecutionRecord {
  id: string;
  skillId: string;
  skillName: string;
  agentRole: AgentRole | string;
  inputs: Record<string, unknown>;
  output: Record<string, unknown>;
  formattedOutput?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: Date;
  completedAt?: Date;
  executionTime?: number;
  error?: string;
  projectId?: string;
  conversationId?: string;
}

// 技能执行状态
export interface SkillExecutionState {
  currentExecution: SkillExecutionRecord | null;
  executionHistory: SkillExecutionRecord[];
  isExecuting: boolean;
  error: string | null;
}

// 技能筛选选项
export interface SkillFilterOptions {
  category?: SkillDefinition['category'];
  agentRole?: AgentRole | string;
  searchQuery?: string;
  tags?: string[];
}

// 需求分析输出结构
export interface RequirementAnalysisOutput {
  productOneLiner: string;
  userPersona: {
    who: string;
    painPoints: string;
    currentSolutions: string;
    whyNewProduct: string;
  };
  featureList: {
    p0: string[];
    p1: string[];
    p2: string[];
  };
  userStories: Array<{
    id: string;
    role: string;
    action: string;
    benefit: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  successMetrics: {
    northStar: string;
    metrics: Array<{
      name: string;
      target: string;
      timeFrame: string;
    }>;
  };
}

// PRD 输出结构
export interface PRDOutput {
  title: string;
  overview: string;
  goals: string[];
  userPersonas: Array<{
    name: string;
    description: string;
    needs: string[];
  }>;
  features: Array<{
    id: string;
    name: string;
    description: string;
    priority: 'p0' | 'p1' | 'p2';
    acceptanceCriteria: string[];
  }>;
  userStories: string[];
  nonFunctionalRequirements: {
    performance?: string[];
    security?: string[];
    compliance?: string[];
  };
  timeline: Array<{
    phase: string;
    duration: string;
    deliverables: string[];
  }>;
}

// 技术架构输出结构
export interface TechArchitectureOutput {
  overview: string;
  architectureDiagram: string; // Mermaid 语法
  techStack: {
    frontend: string[];
    backend: string[];
    database: string[];
    infrastructure: string[];
  };
  components: Array<{
    name: string;
    description: string;
    responsibilities: string[];
    dependencies: string[];
  }>;
  dataModel: Array<{
    entity: string;
    fields: Array<{
      name: string;
      type: string;
      description: string;
    }>;
  }>;
  apiDesign: Array<{
    endpoint: string;
    method: string;
    description: string;
    request?: Record<string, unknown>;
    response?: Record<string, unknown>;
  }>;
  securityConsiderations: string[];
}

// UX 设计输出结构
export interface UXDesignOutput {
  overview: string;
  userFlows: Array<{
    name: string;
    steps: Array<{
      step: number;
      screen: string;
      action: string;
      outcome: string;
    }>;
  }>;
  wireframes: Array<{
    name: string;
    description: string;
    layout: string;
    keyElements: string[];
  }>;
  designSystem: {
    colors: Array<{ name: string; value: string; usage: string }>;
    typography: Array<{ name: string; specs: string }>;
    components: string[];
  };
  interactionPatterns: Array<{
    name: string;
    description: string;
    behavior: string;
  }>;
}

// 商业模式输出结构
export interface BusinessModelOutput {
  valueProposition: string;
  customerSegments: Array<{
    segment: string;
    description: string;
    needs: string[];
  }>;
  revenueStreams: Array<{
    stream: string;
    description: string;
    pricing: string;
    projectedRevenue?: string;
  }>;
  costStructure: Array<{
    category: string;
    items: string[];
    estimatedCost?: string;
  }>;
  channels: string[];
  keyMetrics: string[];
  competitiveAdvantage: string;
}

// 里程碑规划输出结构
export interface MilestonePlanOutput {
  overview: string;
  phases: Array<{
    name: string;
    duration: string;
    startDate?: string;
    endDate?: string;
    goals: string[];
    deliverables: string[];
    dependencies: string[];
    risks: Array<{
      risk: string;
      mitigation: string;
    }>;
  }>;
  resources: {
    team: Array<{
      role: string;
      count: number;
      responsibilities: string[];
    }>;
    tools: string[];
    budget?: string;
  };
  criticalPath: string[];
  milestones: Array<{
    name: string;
    date: string;
    criteria: string[];
  }>;
}

// 医疗业务评审输出结构
export interface MedicalReviewOutput {
  summary: string;
  medicalRationality: {
    score: number; // 0-100
    assessment: string;
    concerns: string[];
    recommendations: string[];
  };
  complianceAnalysis: {
    applicableRegulations: string[];
    complianceStatus: 'compliant' | 'partial' | 'non-compliant';
    gaps: string[];
    actions: string[];
  };
  riskAssessment: Array<{
    risk: string;
    level: 'high' | 'medium' | 'low';
    impact: string;
    mitigation: string;
  }>;
  approvalRecommendation: 'approve' | 'approve-with-conditions' | 'reject';
  conditions?: string[];
}

// 合规检查输出结构
export interface ComplianceCheckOutput {
  summary: string;
  overallStatus: 'pass' | 'fail' | 'partial';
  score: number;
  categories: Array<{
    name: string;
    status: 'pass' | 'fail' | 'partial';
    items: Array<{
      requirement: string;
      status: 'pass' | 'fail' | 'na';
      evidence?: string;
      remediation?: string;
    }>;
  }>;
  criticalIssues: string[];
  recommendations: string[];
  checklist: Array<{
    item: string;
    checked: boolean;
    category: string;
  }>;
}

// 多院区需求分析输出结构
export interface MultiBranchAnalysisOutput {
  summary: string;
  standardFeatures: Array<{
    feature: string;
    description: string;
    applicableBranches: string[];
  }>;
  branchSpecificRequirements: Array<{
    branch: string;
    location: string;
    specificPolicies: string[];
    requiredAdaptations: string[];
    estimatedEffort: string;
  }>;
  dataSynchronization: {
    strategy: string;
    syncFrequency: string;
    conflictResolution: string;
  };
  deploymentStrategy: string;
  riskAssessment: string[];
}

// 技能输出类型映射
export type SkillOutputMap = {
  'requirement-analysis': RequirementAnalysisOutput;
  'write-prd': PRDOutput;
  'tech-architecture': TechArchitectureOutput;
  'ux-design': UXDesignOutput;
  'business-model': BusinessModelOutput;
  'milestone-plan': MilestonePlanOutput;
  'medical-review': MedicalReviewOutput;
  'compliance-check': ComplianceCheckOutput;
  'multi-branch-analysis': MultiBranchAnalysisOutput;
};

// 技能 ID 类型
export type SkillId = keyof SkillOutputMap;
