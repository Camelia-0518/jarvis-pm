import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ReviewStage =
  | 'draft'
  | 'medical-review'
  | 'compliance-review'
  | 'technical-review'
  | 'branch-review'
  | 'approved'
  | 'rejected';

export type ReviewStatus = 'pending' | 'in-progress' | 'approved' | 'rejected' | 'needs-revision';

export interface Reviewer {
  id: string;
  name: string;
  role: 'product-manager' | 'medical-officer' | 'compliance-officer' | 'tech-lead' | 'branch-rep';
  department: string;
}

export interface ReviewComment {
  id: string;
  stage: ReviewStage;
  reviewerId: string;
  reviewerName: string;
  reviewerRole: string;
  content: string;
  type: 'comment' | 'approval' | 'rejection' | 'revision-request';
  attachments?: string[];
  createdAt: string;
}

export interface ReviewStageConfig {
  stage: ReviewStage;
  name: string;
  description: string;
  requiredRoles: Reviewer['role'][];
  order: number;
}

export interface ReviewWorkflow {
  id: string;
  requirementId: string;
  requirementTitle: string;
  submitterId: string;
  submitterName: string;
  currentStage: ReviewStage;
  status: ReviewStatus;
  stages: {
    stage: ReviewStage;
    status: ReviewStatus;
    startedAt?: string;
    completedAt?: string;
    assignedReviewers: string[];
  }[];
  comments: ReviewComment[];
  createdAt: string;
  updatedAt: string;
}

interface ReviewWorkflowState {
  workflows: ReviewWorkflow[];
  reviewers: Reviewer[];
  currentWorkflow: ReviewWorkflow | null;

  // Actions
  createWorkflow: (workflow: Omit<ReviewWorkflow, 'id' | 'createdAt' | 'updatedAt' | 'stages'>) => ReviewWorkflow;
  updateWorkflow: (id: string, updates: Partial<ReviewWorkflow>) => void;
  moveToStage: (workflowId: string, stage: ReviewStage) => void;
  addComment: (workflowId: string, comment: Omit<ReviewComment, 'id' | 'createdAt'>) => void;
  approveStage: (workflowId: string, stage: ReviewStage, reviewerId: string) => void;
  rejectStage: (workflowId: string, stage: ReviewStage, reviewerId: string, reason: string) => void;
  requestRevision: (workflowId: string, stage: ReviewStage, reviewerId: string, feedback: string) => void;
  getWorkflowsByStatus: (status: ReviewStatus) => ReviewWorkflow[];
  getWorkflowsByStage: (stage: ReviewStage) => ReviewWorkflow[];
  getMyWorkflows: (reviewerId: string) => ReviewWorkflow[];
}

export const STAGE_CONFIG: ReviewStageConfig[] = [
  {
    stage: 'draft',
    name: '草稿',
    description: '需求准备阶段',
    requiredRoles: ['product-manager'],
    order: 0,
  },
  {
    stage: 'medical-review',
    name: '医务审核',
    description: '医务科审核医疗业务合理性',
    requiredRoles: ['medical-officer'],
    order: 1,
  },
  {
    stage: 'compliance-review',
    name: '合规审核',
    description: '合规专员检查政策法规符合性',
    requiredRoles: ['compliance-officer'],
    order: 2,
  },
  {
    stage: 'technical-review',
    name: '技术评审',
    description: '技术负责人评估可行性',
    requiredRoles: ['tech-lead'],
    order: 3,
  },
  {
    stage: 'branch-review',
    name: '分院评估',
    description: '分院代表确认地方适配性',
    requiredRoles: ['branch-rep'],
    order: 4,
  },
  {
    stage: 'approved',
    name: '已通过',
    description: '评审完成，需求已批准',
    requiredRoles: [],
    order: 5,
  },
];

const PRESET_REVIEWERS: Reviewer[] = [
  { id: 'rev-1', name: '张医生', role: 'medical-officer', department: '医务科' },
  { id: 'rev-2', name: '李合规', role: 'compliance-officer', department: '合规部' },
  { id: 'rev-3', name: '王架构', role: 'tech-lead', department: '技术部' },
  { id: 'rev-4', name: '陈产品', role: 'product-manager', department: '产品部' },
  { id: 'rev-5', name: '刘江西', role: 'branch-rep', department: '江西分院' },
  { id: 'rev-6', name: '赵临夏', role: 'branch-rep', department: '临夏分院' },
  { id: 'rev-7', name: '孙浙江', role: 'branch-rep', department: '浙江分院' },
];

// 预设示例数据
const PRESET_WORKFLOWS: ReviewWorkflow[] = [
  {
    id: 'wf-1',
    requirementId: 'req-1',
    requirementTitle: '优化预约挂号爽约处理机制',
    submitterId: 'rev-4',
    submitterName: '陈产品',
    currentStage: 'medical-review',
    status: 'in-progress',
    stages: [
      { stage: 'draft', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-4'] },
      { stage: 'medical-review', status: 'in-progress', startedAt: new Date().toISOString(), assignedReviewers: ['rev-1'] },
      { stage: 'compliance-review', status: 'pending', assignedReviewers: ['rev-2'] },
      { stage: 'technical-review', status: 'pending', assignedReviewers: ['rev-3'] },
      { stage: 'branch-review', status: 'pending', assignedReviewers: ['rev-5', 'rev-6', 'rev-7'] },
    ],
    comments: [
      {
        id: 'c-1',
        stage: 'draft',
        reviewerId: 'rev-4',
        reviewerName: '陈产品',
        reviewerRole: '产品经理',
        content: '需求已提交，请医务科审核业务流程合理性',
        type: 'comment',
        createdAt: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'wf-2',
    requirementId: 'req-2',
    requirementTitle: '新增中药房库存管理功能',
    submitterId: 'rev-5',
    submitterName: '刘江西',
    currentStage: 'approved',
    status: 'approved',
    stages: [
      { stage: 'draft', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-5'] },
      { stage: 'medical-review', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-1'] },
      { stage: 'compliance-review', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-2'] },
      { stage: 'technical-review', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-3'] },
      { stage: 'branch-review', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-5', 'rev-6', 'rev-7'] },
    ],
    comments: [
      {
        id: 'c-2',
        stage: 'medical-review',
        reviewerId: 'rev-1',
        reviewerName: '张医生',
        reviewerRole: '医务科',
        content: '符合中药房管理规范，建议增加有效期预警功能',
        type: 'comment',
        createdAt: new Date().toISOString(),
      },
      {
        id: 'c-3',
        stage: 'medical-review',
        reviewerId: 'rev-1',
        reviewerName: '张医生',
        reviewerRole: '医务科',
        content: '医务审核通过',
        type: 'approval',
        createdAt: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'wf-3',
    requirementId: 'req-3',
    requirementTitle: '调整互联网医院问诊费用',
    submitterId: 'rev-7',
    submitterName: '孙浙江',
    currentStage: 'compliance-review',
    status: 'needs-revision',
    stages: [
      { stage: 'draft', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-7'] },
      { stage: 'medical-review', status: 'approved', completedAt: new Date().toISOString(), assignedReviewers: ['rev-1'] },
      { stage: 'compliance-review', status: 'needs-revision', startedAt: new Date().toISOString(), assignedReviewers: ['rev-2'] },
    ],
    comments: [
      {
        id: 'c-4',
        stage: 'compliance-review',
        reviewerId: 'rev-2',
        reviewerName: '李合规',
        reviewerRole: '合规专员',
        content: '定价不符合浙江省医疗服务价格管理规范，需要重新调整定价策略',
        type: 'revision-request',
        createdAt: new Date().toISOString(),
      },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

export const useReviewWorkflowStore = create<ReviewWorkflowState>()(
  persist(
    (set, get) => ({
      workflows: PRESET_WORKFLOWS,
      reviewers: PRESET_REVIEWERS,
      currentWorkflow: null,

      createWorkflow: (workflow) => {
        const now = new Date().toISOString();
        const stages = STAGE_CONFIG
          .filter((s) => s.order < 5)
          .map((config) => ({
            stage: config.stage,
            status: config.stage === 'draft' ? 'in-progress' : ('pending' as ReviewStatus),
            assignedReviewers: config.requiredRoles.map((role) => {
              const reviewer = get().reviewers.find((r) => r.role === role);
              return reviewer?.id || '';
            }),
          }));

        const newWorkflow: ReviewWorkflow = {
          ...workflow,
          id: `wf-${Date.now()}`,
          stages,
          createdAt: now,
          updatedAt: now,
        };

        set((state) => ({
          workflows: [newWorkflow, ...state.workflows],
        }));

        return newWorkflow;
      },

      updateWorkflow: (id, updates) => {
        set((state) => ({
          workflows: state.workflows.map((w) =>
            w.id === id ? { ...w, ...updates, updatedAt: new Date().toISOString() } : w
          ),
        }));
      },

      moveToStage: (workflowId, stage) => {
        set((state) => ({
          workflows: state.workflows.map((w) =>
            w.id === workflowId
              ? {
                  ...w,
                  currentStage: stage,
                  stages: w.stages.map((s) =>
                    s.stage === stage
                      ? { ...s, status: 'in-progress' as ReviewStatus, startedAt: new Date().toISOString() }
                      : s
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : w
          ),
        }));
      },

      addComment: (workflowId, comment) => {
        const newComment: ReviewComment = {
          ...comment,
          id: `c-${Date.now()}`,
          createdAt: new Date().toISOString(),
        };

        set((state) => ({
          workflows: state.workflows.map((w) =>
            w.id === workflowId
              ? { ...w, comments: [...w.comments, newComment], updatedAt: new Date().toISOString() }
              : w
          ),
        }));
      },

      approveStage: (workflowId, stage, reviewerId) => {
        set((state) => {
          const workflow = state.workflows.find((w) => w.id === workflowId);
          if (!workflow) return state;

          const currentStageIndex = STAGE_CONFIG.findIndex((s) => s.stage === stage);
          const nextStage = STAGE_CONFIG[currentStageIndex + 1];

          const newComment: ReviewComment = {
            id: `c-${Date.now()}`,
            stage,
            reviewerId,
            reviewerName: state.reviewers.find((r) => r.id === reviewerId)?.name || '',
            reviewerRole: state.reviewers.find((r) => r.id === reviewerId)?.role || '',
            content: '审核通过',
            type: 'approval',
            createdAt: new Date().toISOString(),
          };

          return {
            workflows: state.workflows.map((w) =>
              w.id === workflowId
                ? {
                    ...w,
                    currentStage: nextStage?.stage || 'approved',
                    status: nextStage ? w.status : 'approved',
                    stages: w.stages.map((s) =>
                      s.stage === stage
                        ? { ...s, status: 'approved' as ReviewStatus, completedAt: new Date().toISOString() }
                        : s.stage === nextStage?.stage
                        ? { ...s, status: 'in-progress' as ReviewStatus, startedAt: new Date().toISOString() }
                        : s
                    ),
                    comments: [...w.comments, newComment],
                    updatedAt: new Date().toISOString(),
                  }
                : w
            ),
          };
        });
      },

      rejectStage: (workflowId, stage, reviewerId, reason) => {
        set((state) => {
          const newComment: ReviewComment = {
            id: `c-${Date.now()}`,
            stage,
            reviewerId,
            reviewerName: state.reviewers.find((r) => r.id === reviewerId)?.name || '',
            reviewerRole: state.reviewers.find((r) => r.id === reviewerId)?.role || '',
            content: reason,
            type: 'rejection',
            createdAt: new Date().toISOString(),
          };

          return {
            workflows: state.workflows.map((w) =>
              w.id === workflowId
                ? {
                    ...w,
                    status: 'rejected',
                    stages: w.stages.map((s) =>
                      s.stage === stage ? { ...s, status: 'rejected' as ReviewStatus } : s
                    ),
                    comments: [...w.comments, newComment],
                    updatedAt: new Date().toISOString(),
                  }
                : w
            ),
          };
        });
      },

      requestRevision: (workflowId, stage, reviewerId, feedback) => {
        set((state) => {
          const newComment: ReviewComment = {
            id: `c-${Date.now()}`,
            stage,
            reviewerId,
            reviewerName: state.reviewers.find((r) => r.id === reviewerId)?.name || '',
            reviewerRole: state.reviewers.find((r) => r.id === reviewerId)?.role || '',
            content: feedback,
            type: 'revision-request',
            createdAt: new Date().toISOString(),
          };

          return {
            workflows: state.workflows.map((w) =>
              w.id === workflowId
                ? {
                    ...w,
                    status: 'needs-revision',
                    stages: w.stages.map((s) =>
                      s.stage === stage ? { ...s, status: 'needs-revision' as ReviewStatus } : s
                    ),
                    comments: [...w.comments, newComment],
                    updatedAt: new Date().toISOString(),
                  }
                : w
            ),
          };
        });
      },

      getWorkflowsByStatus: (status) => {
        return get().workflows.filter((w) => w.status === status);
      },

      getWorkflowsByStage: (stage) => {
        return get().workflows.filter((w) => w.currentStage === stage);
      },

      getMyWorkflows: (reviewerId) => {
        return get().workflows.filter((w) =>
          w.stages.some(
            (s) => s.assignedReviewers.includes(reviewerId) && (s.status === 'pending' || s.status === 'in-progress')
          )
        );
      },
    }),
    {
      name: 'review-workflow-store',
    }
  )
);
