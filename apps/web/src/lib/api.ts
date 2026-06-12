/**
 * API Client for Jarvis PM Backend
 * Connects to FastAPI backend
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

// Single-user mode: no token management needed

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return '';
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length > 0 ? `?${parts.join('&')}` : '';
}

function getFriendlyErrorMessage(error: unknown, endpoint: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof TypeError) {
    // Network or CORS failure
    if (error.message.includes('fetch') || error.message.includes('Failed to fetch')) {
      return `网络连接失败：无法连接到后端服务 (${API_BASE_URL})。请确认后端服务已启动。`;
    }
    if (error.message.includes('CORS') || error.message.includes('cross-origin')) {
      return '跨域请求被阻止 (CORS)。请检查后端 CORS 配置。';
    }
    return `网络错误：${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '未知错误，请稍后重试';
}

// Request helper
export async function request<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number; _retry?: boolean } = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  // Per-endpoint timeout defaults to prevent excessively long waits
  const DEFAULT_TIMEOUTS: Record<string, number> = {
    '/agents/prd/generate': 60000,
    '/tools/': 60000,
    '/skills/execute': 60000,
    '/workflows/execute': 60000,
  };
  let defaultTimeout = 10000; // 10s for list/CRUD endpoints
  if (endpoint.includes('/export')) defaultTimeout = 30000;
  if (endpoint.startsWith('/prds/') && !endpoint.includes('/generate')) defaultTimeout = 30000;
  for (const [prefix, ms] of Object.entries(DEFAULT_TIMEOUTS)) {
    if (endpoint.startsWith(prefix)) {
      defaultTimeout = ms;
      break;
    }
  }
  const timeoutMs = options.timeoutMs ?? defaultTimeout;

  // Generate or reuse request ID for tracing
  const requestId = (options.headers as Record<string, string>)?.['X-Request-ID']
    || (typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `req-${Date.now()}-${Math.random().toString(36).slice(2)}`);

  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers: Record<string, string> = {
    'X-Request-ID': requestId,
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...((options.headers as Record<string, string>) || {}),
  };

  // Attach auth token if available (for non-single-user mode compatibility)
  const accessToken = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (fetchError: unknown) {
    clearTimeout(timeoutId);
    if (fetchError instanceof Error && fetchError.name === 'AbortError') {
      throw new ApiError(`请求超时（${timeoutMs / 1000}秒）。后端处理较慢或网络不稳定，请稍后重试。[Request ID: ${requestId}]`, 0, 'TIMEOUT');
    }
    const msg = getFriendlyErrorMessage(fetchError, endpoint);
    throw new ApiError(`${msg} [Request ID: ${requestId}]`, 0, 'NETWORK_ERROR');
  }
  clearTimeout(timeoutId);

  // JWT refresh on 401 (framework for multi-user mode)
  if (response.status === 401 && accessToken && !options._retry) {
    try {
      const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null;
      if (refreshToken) {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${refreshToken}` },
        });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          if (refreshData.success && refreshData.data?.access_token) {
            localStorage.setItem('access_token', refreshData.data.access_token);
            // Retry original request
            return request(endpoint, { ...options, _retry: true });
          }
        }
      }
    } catch {
      // Refresh failed, fall through to normal error handling
    }
  }

  type ApiEnvelope = {
    success?: boolean;
    data?: unknown;
    detail?: string;
    error?: { code?: string; message?: string } | string;
  };
  let result: ApiEnvelope | unknown;
  try {
    result = await response.json();
  } catch {
    // Non-JSON response
    const text = await response.text().catch(() => '');
    if (!response.ok) {
      throw new ApiError(`${text || `HTTP ${response.status} 错误`} [Request ID: ${requestId}]`, response.status, 'HTTP_ERROR');
    }
    return text as T;
  }

  const env = (result || {}) as ApiEnvelope;

  if (!response.ok) {
    const errorObj = typeof env.error === 'object' ? env.error : null;
    const message = env.detail || errorObj?.message || `HTTP ${response.status} 错误`;
    throw new ApiError(`${message} [Request ID: ${requestId}]`, response.status, errorObj?.code || 'HTTP_ERROR');
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T;
  }

  // Unwrap standardized backend response wrapper {success, data, error, meta}
  if (env && typeof env === 'object' && 'success' in env) {
    if (!env.success) {
      const errorObj = typeof env.error === 'object' ? env.error : null;
      const msg = errorObj?.message || (typeof env.error === 'string' ? env.error : 'Request failed');
      throw new ApiError(msg, response.status, errorObj?.code || 'BACKEND_ERROR');
    }
    return env.data as T;
  }

  return result as T;
}

// ==================== Auth API ====================

export const authApi = {
  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string; refresh_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data.access_token) {
      if (typeof window !== 'undefined') localStorage.setItem('access_token', data.access_token);
    }
    if (data.refresh_token) {
      if (typeof window !== 'undefined') localStorage.setItem('refresh_token', data.refresh_token);
    }
    return data;
  },

  register: async (email: string, password: string, name: string) => {
    const data = await request<{ access_token: string; refresh_token: string; token_type: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    });
    if (data.access_token) {
      if (typeof window !== 'undefined') localStorage.setItem('access_token', data.access_token);
    }
    if (data.refresh_token) {
      if (typeof window !== 'undefined') localStorage.setItem('refresh_token', data.refresh_token);
    }
    return data;
  },

  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },

  getCurrentUser: async () => request<User>('/auth/me'),

  isAuthenticated: () => {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem('access_token');
  },
};

// ==================== Project API ====================

export const projectApi = {
  list: async (params?: { page?: number; limit?: number; status?: string; industry?: string }) => {
    const query = buildQuery(params);
    return request<{ items: Project[]; total: number; page: number; limit: number }>(`/projects${query}`);
  },

  get: async (id: string) => {
    return request<ProjectDetail>(`/projects/${id}`);
  },

  create: async (data: {
    name: string;
    description?: string;
    industry?: string;
  }) => {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (
    id: string,
    data: {
      name?: string;
      description?: string;
      industry?: string;
      status?: string;
    }
  ) => {
    return request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<{ message: string; id: string }>(`/projects/${id}`, {
      method: 'DELETE',
    });
  },

  health: async () => {
    return request<ProjectHealthResponse>('/projects/projects-health-check');
  },
  healthDetail: async (projectId: string) => {
    return request<ProjectHealthItem>(`/projects/${projectId}/health`);
  },
};

export interface ProjectHealthItem {
  project_id: string;
  project_name: string;
  industry: string;
  health_score: number;
  risk_level: 'on_track' | 'at_risk' | 'critical';
  score_breakdown?: Record<string, number>;
  metrics: {
    total_prds: number;
    published_prds: number;
    draft_prds: number;
    has_delivery_plan: boolean;
    delivery_status: string | null;
    days_since_update: number | null;
    milestones_completed?: number;
    milestones_total?: number;
    milestone_progress_pct?: number;
    issue_resolution_rate?: number;
    open_issues?: number;
    high_risks?: number;
    active_risks?: number;
  };
  bottlenecks: Array<{ type: string; message: string; severity: string }>;
}

export interface ProjectHealthResponse {
  summary: {
    total_projects: number;
    on_track: number;
    at_risk: number;
    critical: number;
    average_health_score: number;
  };
  projects: ProjectHealthItem[];
}

// ==================== PRD API ====================

export const prdApi = {
  list: async (params?: { projectId?: string; limit?: number; offset?: number }) => {
    const query = buildQuery(params && { project_id: params.projectId, limit: params.limit, offset: params.offset });
    return request<{ items: PRD[]; total: number }>(`/prds${query}`);
  },

  get: async (id: string) => {
    return request<PRD>(`/prds/${id}`);
  },

  create: async (data: {
    project_id: string;
    title: string;
    template?: string;
  }) => {
    return request<PRD>('/prds', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (
    id: string,
    data: {
      title?: string;
      content?: Record<string, unknown>;
      markdown?: string;
      status?: string;
    }
  ) => {
    return request<PRD>(`/prds/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<{ message: string; id: string }>(`/prds/${id}`, {
      method: 'DELETE',
    });
  },

  generate: async (
    id: string,
    data: {
      chapter: string;
      prompt: string;
      context?: Record<string, unknown>;
      bypass_cache?: boolean;
    }
  ) => {
    return request<{
      chapter: string;
      content: string;
      markdown: string;
    }>(`/prds/${id}/generate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  generateStream: (
    id: string,
    data: {
      chapter: string;
      prompt: string;
      context?: Record<string, unknown>;
      bypass_cache?: boolean;
    },
    onChunk: (text: string) => void,
    onDone: (markdown: string) => void,
    onError: (error: string) => void
  ): (() => void) => {
    const url = `${API_BASE_URL}/prds/${id}/generate-stream`;
    const controller = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const text = await response.text().catch(() => '');
          onError(`HTTP ${response.status}: ${text}`);
          return;
        }
        const reader = response.body?.getReader();
        if (!reader) {
          onError('Response body is not readable');
          return;
        }
        const decoder = new TextDecoder();
        let fullMarkdown = '';
        let lineBuffer = '';
        let streamEnded = false;

        const processLines = (raw: string) => {
          lineBuffer += raw;
          const parts = lineBuffer.split('\n\n');
          lineBuffer = parts.pop() || '';
          for (const part of parts) {
            const lines = part.split('\n');
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith('data: ')) continue;
              const dataStr = trimmed.slice(6);
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.type === 'chunk' && parsed.text) {
                  fullMarkdown += parsed.text;
                  onChunk(parsed.text);
                } else if (parsed.type === 'done') {
                  streamEnded = true;
                  onDone(parsed.markdown || fullMarkdown);
                } else if (parsed.type === 'error') {
                  onError(parsed.message);
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          processLines(decoder.decode(value, { stream: true }));
        }
        // Flush decoder internal buffer (handles UTF-8 multi-byte characters)
        processLines(decoder.decode());
        // If stream ended without a "done" SSE event, treat remaining buffer as final
        if (!streamEnded && lineBuffer.trim()) {
          processLines('\n\n');
        }
        if (!streamEnded) {
          onDone(fullMarkdown);
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err instanceof Error ? err.message : 'Stream error');
        }
      });

    return () => controller.abort();
  },

  export: async (id: string, format: 'markdown' | 'json' | 'pdf' | 'docx' = 'markdown') => {
    return request<{
      format: string;
      content: string;
      filename: string;
      encoding?: string;
    }>(`/prds/${id}/export?format=${format}`);
  },

  versions: async (id: string, params?: { limit?: number; offset?: number }) => {
    const query = buildQuery(params);
    return request<{ items: PRDVersionItem[]; total: number }>(`/prds/${id}/versions${query}`);
  },

  getVersion: async (id: string, versionId: string) => {
    return request<PRDVersionDetail>(`/prds/${id}/versions/${versionId}`);
  },

  restoreVersion: async (id: string, versionId: string) => {
    return request<{ message: string; restored_version: number }>(
      `/prds/${id}/versions/${versionId}/restore`,
      { method: 'POST' }
    );
  },
};

// ==================== Tools API ====================

export const toolsApi = {
  userResearch: async (data: {
    project_id: string;
    research_type: string;
    target_audience: string;
    questions?: string[];
    context?: Record<string, unknown>;
  }) => {
    return request<UserResearch>('/tools/user-research', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  stakeholderAnalysis: async (data: {
    project_id: string;
    stakeholders?: Record<string, string>[];
  }) => {
    return request<StakeholderAnalysis>('/tools/stakeholders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  competitorAnalysis: async (data: {
    project_id: string;
    competitors: string[];
    analysis_dimensions?: string[];
    confirmed_candidates?: Record<string, string>[];
  }) => {
    return request<CompetitorAnalysis & { needs_confirmation?: boolean; candidates?: Record<string, string>[]; verified?: Record<string, string>[] }>('/tools/competitors', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  confirmCompetitorAnalysis: async (data: {
    project_id: string;
    competitors: string[];
    confirmed_candidates: Record<string, string>[];
    analysis_dimensions?: string[];
  }) => {
    return request<CompetitorAnalysis & { confirmed?: boolean }>('/tools/competitors/confirm', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  dataAnalysis: async (data: {
    project_id: string;
    data_source: string;
    metrics: string[];
    time_range?: string;
  }) => {
    return request<DataAnalysis>('/tools/data-analysis', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  dataAnalysisUpload: (formData: FormData) => {
    return request<DataAnalysis & { schema: Record<string, unknown>; preview_rows: Record<string, string>[]; markdown: string }>('/tools/data-analysis-upload', {
      method: 'POST',
      body: formData,
    });
  },

  reviewMaterials: async (data: {
    project_id: string;
    prd_id?: string;
    material_type: string;
  }) => {
    return request<ReviewMaterial>('/tools/review-materials', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  reviewMaterialsStream: (
    data: {
      project_id: string;
      prd_id?: string;
      material_type: string;
    },
    onChunk: (text: string) => void,
    onDone: (markdown: string) => void,
    onError: (error: string) => void
  ): (() => void) => {
    const url = `${API_BASE_URL}/tools/review-materials-stream`;
    let aborted = false;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'text';
    xhr.timeout = 120000;

    let fullMarkdown = '';
    let buffer = '';

    xhr.onprogress = () => {
      if (aborted) return;
      const newData = xhr.responseText.slice(buffer.length);
      buffer = xhr.responseText;

      const lines = newData.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6);
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.type === 'chunk' && parsed.text) {
              fullMarkdown += parsed.text;
              onChunk(parsed.text);
            } else if (parsed.type === 'done') {
              onDone(parsed.markdown || fullMarkdown);
            } else if (parsed.type === 'error') {
              onError(parsed.message);
            }
          } catch {
            // ignore
          }
        }
      }
    };

    xhr.onload = () => {
      if (aborted) return;
      const newData = xhr.responseText.slice(buffer.length);
      const lines = newData.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6);
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.type === 'done') {
              onDone(parsed.markdown || fullMarkdown);
            } else if (parsed.type === 'error') {
              onError(parsed.message);
            }
          } catch {
            // ignore
          }
        }
      }
    };

    xhr.onerror = () => {
      if (!aborted) onError('Network error');
    };

    xhr.ontimeout = () => {
      if (!aborted) onError('请求超时');
    };

    xhr.send(JSON.stringify(data));

    return () => {
      aborted = true;
      xhr.abort();
    };
  },

  prototype: async (data: {
    project_id: string;
    feature_description: string;
    prototype_type?: string;
  }) => {
    return request<Prototype>('/tools/prototype', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  stats: async (projectId: string) => {
    return request<{
      project_id: string;
      usage: Record<
        string,
        { count: number; last_used: string }
      >;
      ai_calls: number;
      documents_generated: number;
    }>(`/tools/stats/${projectId}`);
  },
};

// ==================== Skills API ====================

export const skillsApi = {
  getAll: async (params?: {
    category?: string;
    agent_role?: string;
    search?: string;
  }) => {
    const query = params
      ? '?' +
        Object.entries(params)
          .filter(([, v]) => v)
          .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
          .join('&')
      : '';
    return request<{
      skills: SkillDefinition[];
      total: number;
    }>(`/skills/definitions${query}`);
  },

  getById: async (skillId: string) => {
    return request<SkillDefinition>(`/skills/definitions/${skillId}`);
  },

  getByRole: async (role: string) => {
    return request<{
      role: string;
      skills: SkillDefinition[];
      total: number;
    }>(`/skills/by-role/${role}`);
  },

  getCategories: async () => {
    return request<Array<{ value: string; label: string; icon: string }>>(
      '/skills/categories'
    );
  },

  validate: async (skillId: string, inputs: Record<string, unknown>) => {
    return request<{
      valid: boolean;
      errors: string[];
    }>('/skills/validate', {
      method: 'POST',
      body: JSON.stringify({ skillId, inputs }),
    });
  },

  execute: async (
    skillId: string,
    inputs: Record<string, unknown>,
    context?: {
      projectId?: string;
      conversationId?: string;
      userId?: string;
    }
  ) => {
    return request<SkillExecutionResponse>('/skills/execute', {
      method: 'POST',
      body: JSON.stringify({
        skillId,
        inputs,
        context,
      }),
      timeoutMs: 180000,
    });
  },

  executeAsync: async (
    skillId: string,
    inputs: Record<string, unknown>,
    context?: {
      projectId?: string;
      conversationId?: string;
      userId?: string;
    }
  ) => {
    return request<{
      executionId: string;
      status: string;
      message: string;
    }>('/skills/execute-async', {
      method: 'POST',
      body: JSON.stringify({
        skillId,
        inputs,
        context,
      }),
    });
  },

  getExecutionStatus: async (executionId: string) => {
    return request<SkillExecutionRecord>(`/skills/executions/${executionId}`);
  },

  getExecutions: async (params?: {
    skill_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = buildQuery(params);
    return request<
      SkillExecutionRecord[]
    >(`/skills/executions${query}`);
  },

  getExamples: async (skillId: string) => {
    return request<SkillExample[]>(`/skills/examples/${skillId}`);
  },

  getAgentRoles: async () => {
    return request<
      Record<
        string,
        {
          name: string;
          description: string;
          skills: SkillDefinition[];
        }
      >
    >('/skills/agent-roles');
  },
};

// ==================== AI API ====================

export const aiApi = {
  chat: async (message: string, context?: Record<string, unknown>) => {
    return request<{ response: string }>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
      timeoutMs: 180000,
    });
  },

  optimizePrompt: async (input: string, context?: Record<string, unknown>) => {
    return request<{
      task_type: string;
      structured_prompt: string;
      next_steps: string;
    }>('/ai/optimize-prompt', {
      method: 'POST',
      body: JSON.stringify({ input, context }),
      timeoutMs: 180000,
    });
  },

  generatePRD: async (data: {
    title: string;
    description: string;
    industry?: string;
    context?: Record<string, unknown>;
  }) => {
    return request<{
      outline: Record<string, unknown>;
      content: Record<string, unknown>;
      suggestions: string[];
    }>('/ai/generate-prd', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: 180000,
    });
  },

  generatePRDStream: (
    data: {
      title: string;
      description: string;
      industry?: string;
      context?: Record<string, unknown>;
    },
    onChunk: (text: string) => void,
    onDone: (markdown: string) => void,
    onError: (error: string) => void
  ): (() => void) => {
    const url = `${API_BASE_URL}/ai/generate-prd-stream`;
    const controller = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const text = await response.text();
          onError(`HTTP ${response.status}: ${text}`);
          return;
        }
        const reader = response.body?.getReader();
        if (!reader) {
          onError('Response body is not readable');
          return;
        }
        const decoder = new TextDecoder();
        let fullMarkdown = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.type === 'chunk') {
                  fullMarkdown += parsed.text;
                  onChunk(parsed.text);
                } else if (parsed.type === 'done') {
                  onDone(parsed.markdown || fullMarkdown);
                } else if (parsed.type === 'error') {
                  onError(parsed.message);
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err instanceof Error ? err.message : 'Stream error');
        }
      });

    return () => controller.abort();
  },

  chatStream: (
    message: string,
    context: Record<string, unknown> | undefined,
    onChunk: (text: string) => void,
    onDone: (fullText: string) => void,
    onError: (error: string) => void
  ): (() => void) => {
    const url = `${API_BASE_URL}/ai/chat/stream`;
    const controller = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content: message,
        conversation_id: (context?.conversation_id as string) || 'default',
      }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const text = await response.text();
          onError(`HTTP ${response.status}: ${text}`);
          return;
        }
        const reader = response.body?.getReader();
        if (!reader) {
          onError('Response body is not readable');
          return;
        }
        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.done) {
                  onDone(fullText);
                } else if (parsed.content) {
                  fullText += parsed.content;
                  onChunk(parsed.content);
                }
              } catch {
                // ignore parse errors
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err instanceof Error ? err.message : 'Stream error');
        }
      });

    return () => controller.abort();
  },
};

// ==================== Annotation API ====================

export const annotationApi = {
  list: async (prdId: string, params?: { status?: string; chapter_num?: string; limit?: number; offset?: number }) => {
    const query = buildQuery(params);
    return request<{
      items: AnnotationItem[];
      total: number;
      page: number;
      limit: number;
    }>(`/prds/${prdId}/annotations${query}`);
  },

  create: async (prdId: string, data: {
    chapter_num?: string;
    chapter_title?: string;
    line_index?: number;
    selected_text?: string;
    content: string;
    annotation_type?: 'comment' | 'question' | 'suggestion' | 'issue';
    parent_id?: string;
  }) => {
    return request<{ id: string; message: string }>(`/prds/${prdId}/annotations`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (prdId: string, annotationId: string, data: {
    content?: string;
    status?: 'open' | 'resolved' | 'dismissed';
  }) => {
    return request<{ id: string; message: string }>(`/prds/${prdId}/annotations/${annotationId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (prdId: string, annotationId: string) => {
    return request<{ message: string }>(`/prds/${prdId}/annotations/${annotationId}`, {
      method: 'DELETE',
    });
  },

  stats: async (prdId: string) => {
    return request<{
      open: number;
      resolved: number;
      dismissed: number;
      total: number;
    }>(`/prds/${prdId}/annotations/stats`);
  },

  convertToTask: async (prdId: string, annotationId: string) => {
    return request<{ id: string; annotation_id: string; title: string; status: string; message: string }>(
      `/prds/${prdId}/annotations/${annotationId}/convert-to-task`,
      { method: 'POST' }
    );
  },

  autoReview: async (prdId: string) => {
    return request<{
      message: string;
      issues_found: number;
      annotations_created: number;
      sample_issues: Array<{ chapter: string; severity: string; content: string }>;
    }>(`/prds/${prdId}/annotations/auto-review`, { method: 'POST', timeoutMs: 180000 });
  },

  fixAnnotation: async (prdId: string, annotationId: string) => {
    return request<{
      fixed_content: string;
      annotation_id: string;
      message: string;
    }>(`/prds/${prdId}/annotations/${annotationId}/fix`, { method: 'POST', timeoutMs: 180000 });
  },
};

// ==================== Revision Task API ====================

export const revisionTaskApi = {
  list: async (prdId: string, params?: { status?: string }) => {
    const query = buildQuery({ status: params?.status });
    return request<Array<{
      id: string;
      prd_id: string;
      annotation_id: string | null;
      title: string;
      description: string | null;
      status: string;
      assigned_to: string | null;
      created_by: string;
      completed_at: string | null;
      completion_note: string | null;
      re_review_status: string | null;
      created_at: string;
      updated_at: string;
    }>>(`/prds/${prdId}/revision-tasks${query}`);
  },

  create: async (prdId: string, data: {
    annotation_id: string;
    title: string;
    description?: string;
    assigned_to?: string;
  }) => {
    return request<{ id: string; message: string }>(`/prds/${prdId}/revision-tasks`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (prdId: string, taskId: string, data: {
    title?: string;
    description?: string;
    status?: string;
    assigned_to?: string;
  }) => {
    return request<{ id: string; message: string }>(`/prds/${prdId}/revision-tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  complete: async (prdId: string, taskId: string, data: {
    completion_note: string;
    trigger_re_review?: boolean;
  }) => {
    return request<{ id: string; status: string; re_review_status: string | null; message: string }>(
      `/prds/${prdId}/revision-tasks/${taskId}/complete`,
      { method: 'POST', body: JSON.stringify(data) }
    );
  },

  delete: async (prdId: string, taskId: string) => {
    return request<{ message: string }>(`/prds/${prdId}/revision-tasks/${taskId}`, {
      method: 'DELETE',
    });
  },

  stats: async (prdId: string) => {
    return request<{
      todo: number;
      in_progress: number;
      done: number;
      cancelled: number;
      total: number;
    }>(`/prds/${prdId}/revision-tasks/stats`);
  },
};

// ==================== RAG / Memory Search API ====================

export const ragApi = {
  memorySearch: async (data: {
    query: string;
    top_k?: number;
    source_type?: string;
  }) => {
    return request<{
      query: string;
      results: Array<{
        id: string;
        source_type: string;
        source_id: string;
        content: string;
        score: number;
        metadata: Record<string, unknown>;
      }>;
    }>('/rag/memory-search', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  indexDocument: async (sourceType: string, sourceId: string, data: {
    content: string;
    metadata?: Record<string, unknown>;
  }) => {
    return request<{
      indexed_chunks: number;
      source_type: string;
      source_id: string;
    }>(`/rag/memory-index/${sourceType}/${sourceId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ==================== Feedback API ====================

export const feedbackApi = {
  submit: async (data: {
    category: 'bug' | 'feature' | 'quality' | 'other';
    content: string;
    rating?: number;
    context?: string;
  }) => {
    return request<{ id: string; message: string }>('/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  list: async (params?: { category?: string; limit?: number; offset?: number }) => {
    const query = buildQuery(params);
    return request<
      { items: FeedbackItem[]; total: number }
    >(`/feedback${query}`);
  },
};

// ==================== Prompt API ====================

export interface PromptTemplate {
  id: string;
  name: string;
  description?: string;
  content: string;
  version: string;
  is_active: boolean;
  tags: string[];
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export const promptApi = {
  list: async (params?: { name?: string; tag?: string; is_active?: boolean; page?: number; limit?: number }) => {
    const query = buildQuery(params);
    return request<{ items: PromptTemplate[]; total: number; page: number; limit: number }>(`/prompts${query}`);
  },

  get: async (id: string) => {
    return request<PromptTemplate>(`/prompts/${id}`);
  },

  create: async (data: {
    name: string;
    content: string;
    version?: string;
    description?: string;
    tags?: string[];
  }) => {
    return request<PromptTemplate>('/prompts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: { description?: string; tags?: string[] }) => {
    return request<PromptTemplate>(`/prompts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<void>(`/prompts/${id}`, { method: 'DELETE' });
  },

  activate: async (id: string) => {
    return request<PromptTemplate>(`/prompts/${id}/activate`, { method: 'POST' });
  },

  versions: async (name: string) => {
    return request<PromptTemplate[]>(`/prompts/by-name/${name}/versions`);
  },
};

// ==================== Workflow API ====================

export const workflowApi = {
  listTemplates: async () => {
    return request<
      {
        name: string;
        description: string;
        version: string;
        steps_count: number;
      }[]
    >('/workflows/templates');
  },

  getTemplate: async (name: string) => {
    return request<{
      name: string;
      description: string;
      version: string;
      timeout: number;
      steps: {
        step_name: string;
        skill_id: string;
        inputs_mapping: Record<string, string>;
        condition?: string;
        depends_on: string[];
      }[];
    }>(`/workflows/templates/${name}`);
  },

  execute: async (data: {
    workflow_name: string;
    inputs: Record<string, unknown>;
    project_id?: string;
    context?: Record<string, string>;
  }) => {
    return request<{
      execution_id: string;
      workflow: string;
      completed: boolean;
      results: {
        step_name: string;
        skill_id: string;
        status: string;
        output: Record<string, unknown>;
        error?: string;
        duration?: number;
      }[];
      outputs: Record<string, Record<string, unknown>>;
      duration?: number;
      error?: string;
    }>('/workflows/execute', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: 360000,
    });
  },

  getExecution: async (executionId: string) => {
    return request<{
      execution_id: string;
      workflow: string;
      status: string;
      result: {
        completed: boolean;
        results: {
          step_name: string;
          skill_id: string;
          status: string;
          output: Record<string, unknown>;
          error?: string;
          duration?: number;
        }[];
        outputs: Record<string, Record<string, unknown>>;
        duration?: number;
        error?: string;
      };
    }>(`/workflows/executions/${executionId}`);
  },

  executeChain: async (data: {
    chain_id: string;
    inputs: Record<string, unknown>;
    project_id?: string;
    context?: Record<string, string>;
  }) => {
    return request<{
      execution_id: string;
      chain_id: string;
      workflow: string;
      status: string;
      message: string;
    }>('/workflows/execute-chain', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: 30000,
    });
  },
};

// ==================== Personas API ====================

export interface Persona {
  id: string;
  project_id: string;
  name: string;
  role: string;
  description: string | null;
  pain_points: string | null;
  goals: string | null;
  scenarios: string | null;
  demographics: string | null;
  created_at: string;
  updated_at: string | null;
}

export const personaApi = {
  list: async (projectId: string) => {
    return request<Persona[]>(`/projects/${projectId}/personas`);
  },

  create: async (projectId: string, data: {
    name: string;
    role: string;
    description?: string;
    pain_points?: string;
    goals?: string;
    scenarios?: string;
    demographics?: string;
  }) => {
    return request<Persona>(`/projects/${projectId}/personas`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<Omit<Persona, 'id' | 'project_id' | 'created_at' | 'updated_at'>>) => {
    return request<Persona>(`/personas/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<{ deleted: boolean }>(`/personas/${id}`, {
      method: 'DELETE',
    });
  },
};

// ==================== Competitors API ====================

export interface Competitor {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  strengths: string | null;
  weaknesses: string | null;
  features: string[] | null;
  pricing: string | null;
  market_position: string | null;
  source: string | null;
  created_at: string;
  updated_at: string | null;
}

export const competitorApi = {
  list: async (projectId: string) => {
    return request<Competitor[]>(`/projects/${projectId}/competitors`);
  },

  create: async (projectId: string, data: {
    name: string;
    description?: string;
    strengths?: string;
    weaknesses?: string;
    features?: string[];
    pricing?: string;
    market_position?: string;
    source?: string;
  }) => {
    return request<Competitor>(`/projects/${projectId}/competitors`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<Omit<Competitor, 'id' | 'project_id' | 'created_at' | 'updated_at'>>) => {
    return request<Competitor>(`/competitors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<{ deleted: boolean }>(`/competitors/${id}`, {
      method: 'DELETE',
    });
  },
};

// ==================== Requirements API ====================

export interface Requirement {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  rice_reach: number;
  rice_impact: number;
  rice_confidence: number;
  rice_effort: number;
  rice_score: number;
  kano_category: string;
  created_at: string;
  updated_at: string | null;
}

export interface PriorityMatrix {
  total: number;
  rice_top: Requirement[];
  kano_distribution: Record<string, number>;
  kano_groups: Record<string, Requirement[]>;
}

export const requirementApi = {
  list: async (projectId: string, params?: { sort_by?: string; order?: string }) => {
    const query = buildQuery(params);
    return request<Requirement[]>(`/projects/${projectId}/requirements${query}`);
  },

  create: async (projectId: string, data: {
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    rice_reach?: number;
    rice_impact?: number;
    rice_confidence?: number;
    rice_effort?: number;
    kano_category?: string;
  }) => {
    return request<Requirement>(`/projects/${projectId}/requirements`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<Omit<Requirement, 'id' | 'project_id' | 'created_at' | 'updated_at'>>) => {
    return request<Requirement>(`/requirements/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<{ deleted: boolean }>(`/requirements/${id}`, {
      method: 'DELETE',
    });
  },

  getPriorityMatrix: async (projectId: string) => {
    return request<PriorityMatrix>(`/projects/${projectId}/requirements/priority-matrix`);
  },
};

// ==================== Code API ====================

export interface PrototypeData {
  files: Record<string, string>;
  metadata: {
    name: string;
    description: string;
    page_count: number;
    pages: Array<{ name: string; route: string; title: string }>;
    generated_by?: string;
  };
}

export interface PrototypeSkeleton {
  product_name: string;
  industry: string;
  roles: Array<{ name: string; permissions: string[]; primary?: boolean }>;
  user_journeys: Array<{ name: string; steps: string[]; pages: string[] }>;
  pages: Array<{ name: string; role: string; type: string; key_features: string[] }>;
  key_entities: string[];
  design_hints: Record<string, any>;
}

export interface SkeletonResponse {
  skeleton: PrototypeSkeleton;
  message: string;
}

export interface StreamEvent {
  event: string;
  data: any;
}

export const codeApi = {
  /** 兼容旧接口：同步生成原型 */
  generatePrototypeAI: async (prdContent: string, projectId?: string) => {
    return request<PrototypeData>('/code/prototype-ai', {
      method: 'POST',
      body: JSON.stringify({ prd_content: prdContent, project_id: projectId }),
      timeoutMs: 180000,
    });
  },

  /** Step 1: 提交异步骨架提取任务 */
  extractPrototypeSkeletonAsync: async (prdContent: string, options?: Record<string, any>) => {
    return request<{ task_id: string; message: string }>('/code/prototype-ai/extract', {
      method: 'POST',
      body: JSON.stringify({ prd_content: prdContent, options }),
      timeoutMs: 10000,
    });
  },

  /** Step 1b: 轮询查询任务状态 */
  getPrototypeTask: async (taskId: string) => {
    return request<{
      task_id: string;
      status: string;
      skeleton: Record<string, unknown> | null;
      html: string | null;
      report: Record<string, unknown> | null;
      error: string | null;
      created_at: number;
      updated_at: number;
    }>('/code/prototype-ai/tasks/' + encodeURIComponent(taskId));
  },

  /** Step 2: 生成原型（非流式一次性返回） */
  generatePrototype: async (
    prdContent: string,
    projectId?: string,
    options?: Record<string, any>,
  ): Promise<{ html: string; report: any }> => {
    return request<{ html: string; report: any }>('/code/prototype-ai/generate', {
      method: 'POST',
      body: JSON.stringify({ prd_content: prdContent, project_id: projectId, options }),
      timeoutMs: 300000,
    });
  },
};

// ==================== Reviews API ====================

export interface ChecklistItem {
  id: string;
  category: string;
  text: string;
  required: boolean;
}

export interface ChecklistState {
  item_id: string;
  checked: boolean;
  note?: string | null;
}

export const reviewApi = {
  getChecklist: async (projectId: string) => {
    return request<{
      project_id: string;
      industry: string;
      items: ChecklistItem[];
    }>(`/projects/${projectId}/reviews/checklist`);
  },

  submitChecklist: async (projectId: string, items: ChecklistState[]) => {
    return request<{
      project_id: string;
      industry: string;
      total_items: number;
      checked_count: number;
      required_items: number;
      required_checked: number;
      all_required_passed: boolean;
      items: ChecklistState[];
    }>(`/projects/${projectId}/reviews/checklist`, {
      method: 'POST',
      body: JSON.stringify({ items }),
    });
  },
};

// ==================== Types ====================

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string | null;
  role: string;
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  industry: string;
  status: string;
  prd_count: number;
  created_by?: string;
  workspace_id?: string;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectDetail extends Project {
  prds: PRDSummary[];
}

export interface PRDSummary {
  id: string;
  title: string;
  version: string;
  status: string;
  doc_type?: string;
  created_at: string;
}

export interface PRD {
  id: string;
  project_id: string;
  title: string;
  version: string;
  status: string;
  content: {
    chapters: Record<
      string,
      {
        title: string;
        content: string;
        status: string;
      }
    >;
    template: string;
    industry: string;
  };
  markdown: string;
  created_by?: string;
  workspace_id?: string;
  created_at: string;
  updated_at: string | null;
}

export interface UserResearch {
  id: string;
  project_id: string;
  research_type: string;
  target_audience: string;
  findings: Record<string, unknown>;
  insights: string[];
  recommendations: string[];
  markdown: string;
  created_at: string;
}

export interface StakeholderAnalysis {
  id: string;
  project_id: string;
  stakeholders: Record<string, string>[];
  influence_matrix: Record<string, unknown>;
  communication_plan: Record<string, string>[];
  markdown: string;
  created_at: string;
}

export interface CompetitorAnalysis {
  id: string;
  project_id: string;
  competitors: Record<string, unknown>[];
  comparison_matrix: Record<string, unknown>;
  differentiation_opportunities: string[];
  markdown: string;
  created_at: string;
}

export interface DataAnalysis {
  id: string;
  project_id: string;
  summary: Record<string, unknown>;
  trends: Record<string, unknown>[];
  anomalies: Record<string, unknown>[];
  recommendations: string[];
  markdown: string;
  created_at: string;
}

export interface ReviewMaterial {
  id: string;
  project_id: string;
  prd_id: string | null;
  material_type: string;
  content: Record<string, unknown>;
  markdown: string;
  created_at: string;
}

export interface Prototype {
  id: string;
  project_id: string;
  feature_description: string;
  prototype_type: string;
  pages: Record<string, unknown>[];
  user_flows: Record<string, unknown>[];
  markdown: string;
  created_at: string;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface FeedbackItem {
  id: string;
  category: string;
  content: string;
  rating?: number;
  context?: string;
  created_at: string;
}

export interface PRDVersionItem {
  id: string;
  version_number: number;
  title: string;
  change_summary?: string;
  created_at: string;
}

export interface PRDVersionDetail extends PRDVersionItem {
  markdown: string;
  content: string;
}

export interface AnnotationItem {
  id: string;
  prd_id: string;
  parent_id: string | null;
  chapter_num: string | null;
  chapter_title: string | null;
  line_index: number | null;
  selected_text: string | null;
  content: string;
  annotation_type: 'comment' | 'question' | 'suggestion' | 'issue';
  status: 'open' | 'resolved' | 'dismissed';
  created_by: string;
  created_at: string;
  updated_at: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
}

// ==================== Skill Types ====================

export interface SkillParameter {
  name: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'textarea' | 'array';
  description?: string;
  required?: boolean;
  defaultValue?: unknown;
  options?: { label: string; value: string }[];
  placeholder?: string;
}

export interface SkillDefinition {
  id: string;
  name: string;
  description: string;
  agentRole: string;
  category: 'analysis' | 'design' | 'development' | 'review' | 'medical' | 'planning';
  parameters: SkillParameter[];
  outputSchema: Record<string, unknown>;
  examples?: SkillExample[];
  icon?: string;
  tags?: string[];
}

export interface SkillExample {
  id: string;
  name: string;
  description: string;
  inputs: Record<string, unknown>;
  outputPreview?: string;
}

export interface SkillExecutionResponse {
  success: boolean;
  skillId: string;
  output: Record<string, unknown>;
  formattedOutput?: string;
  executionTime: number;
  tokenUsage?: {
    prompt: number;
    completion: number;
    total: number;
  };
  error?: string;
}

export interface SkillExecutionRecord {
  id: string;
  skillId: string;
  skillName: string;
  agentRole: string;
  inputs: Record<string, unknown>;
  output: Record<string, unknown>;
  formattedOutput?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
  executionTime?: number;
  error?: string;
}

// ==================== Template Types ====================

export interface Template {
  id: string;
  name: string;
  description?: string;
  industry: string;
  chapters: string[];
  icon: string;
  color: string;
  is_builtin: boolean;
  created_at: string;
  updated_at?: string;
}

export const templateApi = {
  list: async (params?: { page?: number; limit?: number; industry?: string }) => {
    const query = buildQuery(params);
    return request<{ items: Template[]; total: number; page: number; limit: number }>(`/templates${query}`);
  },

  get: async (id: string) => {
    return request<Template>(`/templates/${id}`);
  },

  create: async (data: {
    name: string;
    description?: string;
    industry?: string;
    chapters?: string[];
    icon?: string;
    color?: string;
  }) => {
    return request<Template>('/templates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<Omit<Template, 'id' | 'is_builtin' | 'created_at' | 'updated_at'>>) => {
    return request<Template>(`/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<{ deleted: boolean }>(`/templates/${id}`, {
      method: 'DELETE',
    });
  },
};

// ==================== Evaluation Types ====================

export interface PRDQualityResult {
  prd_id: string;
  overall_score: number;
  grade: string;
  completeness_score: number;
  accuracy_score: number;
  usability_score: number;
  compliance_score: number;
  suggestions: string[];
}

// ==================== Evaluation API ====================

export const evaluationApi = {
  evaluatePRD: async (prdContent: string, prdId?: string) => {
    return request<PRDQualityResult>('/evaluation/evaluate-prd', {
      method: 'POST',
      body: JSON.stringify({ prd_content: prdContent, prd_id: prdId || '' }),
      timeoutMs: 120000,
    });
  },
};

// ==================== Delivery Types ====================

export interface WbsTask {
  id: string;
  phase_id: string;
  phase_name: string;
  name: string;
  effort_days: number;
  dependencies: string[];
  role: string;
  priority: string;
  phase: string;
  /** Runtime extensions — set by frontend during editing. */
  status?: string;
}

export interface MilestonePhase {
  phase_id: string;
  name: string;
  start: string;
  end: string;
  duration_weeks: number;
  deliverables: string[];
  milestone: string;
  checkpoint: boolean;
  /** Agent / runtime extensions — may not be present in all data. */
  progress?: number;
  templates?: string[];
  /** Alternate field names from agent output */
  duration?: number;
  startDate?: string;
  endDate?: string;
}

export interface GanttItem {
  id: string;
  name: string;
  phase: string;
  start_offset_days: number;
  duration_weeks: number;
  dependencies: string[];
  priority: string;
  role: string;
  phase_label: string;
}

export interface RiskItem {
  id: string;
  category: string;
  risk: string;
  probability: number;
  impact: number;
  risk_score: number;
  risk_level: string;
  prevention: string;
  contingency: string;
  trigger: string;
  owner: string;
  /** Alternate field names from agent output */
  description?: string;
  mitigation?: string;
}

export interface Stakeholder {
  id: string;
  role: string;
  dept: string;
  concern: string;
  influence: string;
  interest: string;
  comm_freq: string;
  comm_channel: string;
}

export interface RaciMatrix {
  activities: { id: string; name: string; phase: string }[];
  roles: { id: string; name: string; dept: string }[];
  assignments: Record<string, Record<string, string>>;
  total_activities: number;
  total_roles: number;
}

export interface CommunicationPlan {
  meetings: {
    id: string;
    name: string;
    participants: string[];
    frequency: string;
    duration: string;
    format: string;
    output: string;
    agenda: string[];
  }[];
  reports: {
    name: string;
    audience: string;
    content: string;
    template: string;
  }[];
  escalation_path: string[];
}

export interface DeliveryPlanSummary {
  id: string;
  project_id: string;
  prd_id: string | null;
  title: string;
  status: string;
  industry: string;
  created_at: string;
  updated_at: string | null;
  wbs_task_count: number;
  risk_count: number;
  milestone_count: number;
}

export interface DeliveryPlanDetail extends DeliveryPlanSummary {
  wbs: { tasks: WbsTask[]; total_tasks: number; total_effort_days: number };
  milestones: { phases: MilestonePhase[]; total_weeks: number; start_date: string; end_date: string };
  resources: { team_size: number; total_person_days: number; recommendation: string };
  gantt: { items: GanttItem[]; total_days: number; start_date: string };
  risks: RiskItem[];
  risk_matrix: { grid: Record<string, { count: number; risks: string[] }>; summary: Record<string, number> };
  risk_response_plan: { top_risks: RiskItem[] };
  stakeholders: Stakeholder[];
  raci: RaciMatrix;
  communication_plan: CommunicationPlan;
  status_template: { sections: { name: string; fields: string[] }[] };
  plan_markdown: string;
  risk_markdown: string;
  stakeholder_markdown: string;
}

export interface DeliveryDashboardData {
  total_plans: number;
  draft: number;
  at_risk: number;
  in_progress: number;
  completed: number;
  total_risks: number;
  high_risks: number;
  risk_health: 'red' | 'yellow' | 'green';
  delivery_health: 'red' | 'yellow' | 'green';
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  task_completion_rate: number;
  total_phases: number;
  avg_phase_progress: number;
  overdue_phases: number;
  health_detail: {
    risk: { score: string; at_risk_plans: number; high_risk_ratio: number; avg_risks_per_plan: number };
    delivery: { score: string; active_ratio: number; task_completion: number; overdue_phases: number };
  };
}

// ==================== Delivery API ====================

export const deliveryApi = {
  generate: async (data: {
    project_id: string;
    prd_id?: string;
    industry?: string;
    team_size?: number;
    start_date?: string;
  }) => {
    return request<DeliveryPlanDetail>('/delivery/generate', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: 180000,
    });
  },

  generateSingle: async (data: {
    project_id: string;
    prd_id?: string;
    industry?: string;
    agent_type: 'delivery_planner' | 'risk_manager' | 'stakeholder_coordinator';
  }) => {
    return request<{ agent_type: string; output: string; data: Record<string, unknown> }>(
      '/delivery/generate-single',
      {
        method: 'POST',
        body: JSON.stringify(data),
        timeoutMs: 120000,
      }
    );
  },

  list: async (params?: { project_id?: string; status?: string; page?: number; limit?: number }) => {
    const query = buildQuery(params);
    return request<{ items: DeliveryPlanSummary[]; total: number; page: number; limit: number }>(
      `/delivery/plans${query}`
    );
  },

  get: async (id: string) => {
    return request<DeliveryPlanDetail>(`/delivery/plans/${id}`);
  },

  update: async (id: string, data: Record<string, unknown>) => {
    return request<DeliveryPlanDetail>(`/delivery/plans/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<void>(`/delivery/plans/${id}`, {
      method: 'DELETE',
    });
  },

  getDashboard: async (projectId?: string) => {
    const query = buildQuery({ project_id: projectId });
    return request<DeliveryDashboardData>(`/delivery/dashboard${query}`);
  },
};

// ==================== Methodology API ====================

export interface MethodologyStage {
  name: string;
  description: string;
  entry_criteria: string[];
  exit_criteria: string[];
  deliverables: string[];
  duration_days: number;
}

export interface MethodologyTemplate {
  id: string;
  name: string;
  description: string;
  industry: string;
  stages: MethodologyStage[];
  best_practices: string[];
  pitfalls: string[];
  templates: Array<{ name: string; type: string }>;
  created_at: string;
  updated_at: string | null;
}

export const methodologyApi = {
  list: async (params?: { industry?: string; page?: number; limit?: number }) => {
    const query = buildQuery(params);
    return request<{ items: MethodologyTemplate[]; total: number }>(`/methodologies${query}`);
  },

  get: async (id: string) => {
    return request<MethodologyTemplate>(`/methodologies/${id}`);
  },

  create: async (data: {
    name: string;
    description?: string;
    industry?: string;
    stages?: MethodologyStage[];
    best_practices?: string[];
    pitfalls?: string[];
    templates?: Array<{ name: string; type: string }>;
  }) => {
    return request<MethodologyTemplate>('/methodologies', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string) => {
    return request<void>(`/methodologies/${id}`, { method: 'DELETE' });
  },
};

// ==================== Retrospectives API ====================

export interface RetroLessonItem {
  id: string;
  category: string;
  lesson: string;
  action_item: string;
  impact?: string;
  owner?: string;
}

export interface RetroLessons {
  id: string;
  project_id: string;
  title: string;
  lessons: RetroLessonItem[];
  ai_analysis?: string;
  created_at?: string;
}

export const retrospectiveApi = {
  list: async (params?: { limit?: number }) => {
    const query = buildQuery(params);
    return request<{ items: RetroLessons[]; total: number }>(`/retrospectives${query}`);
  },

  create: async (data: { project_id: string; title: string; lessons: RetroLessonItem[] }) => {
    return request<RetroLessons>('/retrospectives', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  aiAnalyze: async (id: string) => {
    return request<{ success: boolean; data: Record<string, unknown> }>(`/retrospectives/${id}/ai-analyze`, {
      method: 'POST',
    });
  },
};

// ── Jobs ──

export interface JobInfo {
  id: string;
  job_type: string | null;
  status: string | null;
  failure_type: string | null;
  project_id: string | null;
  prd_id: string | null;
  task_id: string | null;
  triggered_by: string;
  attempt: number;
  max_attempts: number;
  duration_ms: number | null;
  error_message: string | null;
  error_code: string | null;
  retryable: boolean;
  retry_backoff_seconds: number | null;
  next_retry_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}

// ── System ──

export const systemApi = {
  health: async () => request<{ status: string; database: string; feature_tiers: { total_endpoints: number; by_tier: Record<string, number>; production_pct: number } }>('/system/health'),
  featureTiers: async () => request<{ summary: Record<string, unknown>; tiers: Record<string, string> }>('/system/feature-tiers'),
};

export const jobsApi = {
  list: async (params?: Record<string, string | number | undefined>) => {
    const query = buildQuery(params);
    return request<{ items: JobInfo[]; total: number; page: number; limit: number }>(`/jobs${query}`);
  },
  get: async (id: string) => request<JobInfo>(`/jobs/${id}`),
  retry: async (id: string) =>
    request<{ id: string; attempt: number; next_retry_at: string | null; backoff_seconds: number; message: string }>(`/jobs/${id}/retry`, { method: 'POST' }),
};

// ── Workspaces ──

export interface WorkspaceInfo {
  workspace_id: string;
  name: string;
  slug: string;
  role: string;
  joined_at: string | null;
}

export interface WorkspaceMember {
  user_id: string;
  email: string;
  name: string;
  role: string;
  joined_at: string | null;
}

export const workspaceApi = {
  list: async () => request<WorkspaceInfo[]>('/workspaces'),

  create: async (data: { name: string; slug: string }) =>
    request<WorkspaceInfo>('/workspaces', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMembers: async (workspaceId: string) =>
    request<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`),

  updateMemberRole: async (workspaceId: string, userId: string, role: string) =>
    request<{ message: string }>(`/workspaces/${workspaceId}/members/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ user_id: userId, role }),
    }),

  invite: async (workspaceId: string, email: string, role: string) =>
    request<{ message: string }>(`/workspaces/${workspaceId}/invite`, {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    }),
};

// ── Audit ──

export interface AuditEntry {
  id: string;
  user_id: string;
  workspace_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  summary: string | null;
  created_at: string;
}

export const auditApi = {
  list: async (params?: Record<string, string>) => {
    const query = buildQuery(params);
    return request<AuditEntry[]>(`/system/audit${query}`);
  },
};
