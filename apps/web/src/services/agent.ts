// Agent API 服务
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface AgentInfo {
  name: string;
  description: string;
  version: string;
  capabilities: string[];
}

export interface PRDRequest {
  product_name: string;
  description: string;
  target_users: string;
  key_features: string[];
  constraints?: string[];
  sections?: string[];
  skip_evaluation?: boolean; // 默认 true，跳过 AI 评估以加快速度
}

export interface TaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskResult {
  task_id: string;
  status: string;
  result?: {
    success: boolean;
    output: string;
    data: unknown;
    error?: string;
  };
  error?: string;
}

export const AgentService = {
  // 获取所有 Agent
  async listAgents(): Promise<AgentInfo[]> {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error('Failed to fetch agents');
    return res.json();
  },

  // 生成 PRD
  async generatePRD(data: PRDRequest): Promise<TaskResponse> {
    const res = await fetch(`${API_BASE}/agents/prd/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to submit PRD task');
    return res.json();
  },

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<TaskResult> {
    const res = await fetch(`${API_BASE}/agents/tasks/${taskId}`);
    if (!res.ok) throw new Error('Failed to fetch task status');
    return res.json();
  },

  // 轮询任务状态（支持进度更新）
  async pollTaskStatus(
    taskId: string,
    onUpdate: (result: TaskResult) => void,
    interval = 2000
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const check = async () => {
        try {
          // 同时获取状态和进度
          const [statusResult, progressResult] = await Promise.all([
            this.getTaskStatus(taskId),
            this.getTaskProgress(taskId).catch(() => null),
          ]);

          // 合并进度信息到结果中
          if (progressResult?.progress) {
            (statusResult as TaskResult & { progress?: unknown }).progress = progressResult.progress;
          }

          onUpdate(statusResult);

          if (statusResult.status === 'completed' || statusResult.status === 'failed') {
            resolve();
          } else {
            setTimeout(check, interval);
          }
        } catch (error) {
          reject(error);
        }
      };
      check();
    });
  },

  // 获取任务进度
  async getTaskProgress(taskId: string): Promise<{ progress: { total_steps: number; completed_steps: number; latest_update: unknown; updates: unknown[] } }> {
    const res = await fetch(`${API_BASE}/agents/tasks/${taskId}/progress`);
    if (!res.ok) throw new Error('Failed to fetch task progress');
    return res.json();
  },
};
