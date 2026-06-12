// Agent API service — thin wrapper over the central request() function
import { request } from "@/lib/api";

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
  skip_evaluation?: boolean;
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
  async listAgents(): Promise<AgentInfo[]> {
    return request<AgentInfo[]>('/agents');
  },

  async generatePRD(data: PRDRequest): Promise<TaskResponse> {
    return request<TaskResponse>('/agents/prd/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getTaskStatus(taskId: string): Promise<TaskResult> {
    return request<TaskResult>(`/agents/tasks/${taskId}`);
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
    return request<{ progress: { total_steps: number; completed_steps: number; latest_update: unknown; updates: unknown[] } }>(`/agents/tasks/${taskId}/progress`);
  },
};
