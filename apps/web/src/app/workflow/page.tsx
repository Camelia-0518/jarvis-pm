'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useAgentStore } from '@/stores/agentStore';
import { WORKFLOW_TEMPLATES, AGENT_CONFIGS, type AgentRole } from '@/types/agent';
import NavHeader from '@/components/global/NavHeader';
import { workflowApi } from '@/lib/api';

const WorkflowCanvas = dynamic(
  () => import('@/components/workflow/WorkflowCanvas'),
  { ssr: false }
);

// 模板到后端 workflow 名称的映射
const TEMPLATE_TO_WORKFLOW: Record<string, string> = {
  'from-scratch': 'product-design',
  'security-review': 'medical-compliance-audit',
  'prd-review': 'product-design',
};

export default function WorkflowPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'canvas' | 'logs' | 'agents' | 'messages' | 'conflicts'>('canvas');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [executionResults, setExecutionResults] = useState<Array<Record<string, unknown>> | null>(null);
  const [workflowInputs, setWorkflowInputs] = useState({
    idea: '医疗信息化产品',
    targetUsers: '医护人员和患者',
    industry: 'medical',
    constraints: '必须符合等保三级和医疗数据隐私规范',
    prdContent: '',
  });

  const {
    agents,
    reasoningLogs,
    conflicts,
    messages,
    overallProgress,
    clearLogs,
    initializeAgents,
    updateAgentStatus,
    addReasoning,
    addMessage,
    updateProgress,
  } = useAgentStore();

  // 初始化 Agents
  useEffect(() => {
    initializeAgents();
  }, [initializeAgents]);

  const handleRunWorkflow = async () => {
    if (!selectedTemplate) return;

    const workflowName = TEMPLATE_TO_WORKFLOW[selectedTemplate];
    if (!workflowName) {
      setExecutionError('该模板暂不支持真实执行');
      return;
    }

    setIsExecuting(true);
    setExecutionError(null);
    setExecutionResults(null);
    clearLogs();
    initializeAgents();

    // Pre-set agents to working state for better UX during long AI calls
    const template = WORKFLOW_TEMPLATES.find((t) => t.id === selectedTemplate);
    template?.nodes.forEach((node) => {
      const agentId = `agent-${node.role}`;
      const agentName = AGENT_CONFIGS[node.role as AgentRole]?.name || node.role;
      updateAgentStatus(agentId, 'working', agentName);
      addMessage({
        agentId,
        agentRole: node.role as AgentRole,
        content: `开始执行: ${agentName}`,
        type: 'thinking',
      });
    });
    updateProgress(10);

    try {
      const inputs: Record<string, string> = {};
      if (workflowName === 'product-design' || workflowName === 'quick-prd') {
        inputs.idea = workflowInputs.idea;
        inputs.targetUsers = workflowInputs.targetUsers;
        inputs.industry = workflowInputs.industry;
        inputs.constraints = workflowInputs.constraints;
      } else {
        inputs.prdContent = workflowInputs.prdContent || '待评审的PRD内容';
        inputs.industry = 'medical';
      }

      const res = await workflowApi.execute({
        workflow_name: workflowName,
        inputs,
      });

      const results = res.results || [];
      const completed = res.completed ?? false;
      setExecutionResults(results);

      // 按顺序更新 agent 状态和日志
      results.forEach((step, index) => {
        // 把步骤映射到模板预设的节点顺序
        const template = WORKFLOW_TEMPLATES.find((t) => t.id === selectedTemplate);
        const mappedRole = template?.nodes[index]?.role || mapSkillToAgentRole(step.skill_id);
        const agentId = `agent-${mappedRole}`;

        if (step.status === 'completed') {
          updateAgentStatus(agentId, 'completed', step.step_name);
          addReasoning({
            agentId,
            agentRole: mappedRole as AgentRole,
            action: `${step.step_name} 完成`,
            confidence: 0.92,
            reasoning: `步骤「${step.step_name}」执行成功，skill=${step.skill_id}`,
            evidence: [`耗时 ${step.duration?.toFixed(1) || '?'}s`],
            input: JSON.stringify(inputs),
            output: JSON.stringify(step.output).slice(0, 500),
          });
          addMessage({
            agentId,
            agentRole: mappedRole as AgentRole,
            content: `${step.step_name} 已执行完成`,
            type: 'decision',
          });
        } else if (step.status === 'failed') {
          updateAgentStatus(agentId, 'error', step.step_name);
          addReasoning({
            agentId,
            agentRole: mappedRole as AgentRole,
            action: `${step.step_name} 失败`,
            confidence: 0.3,
            reasoning: step.error || '未知错误',
            evidence: [],
          });
          addMessage({
            agentId,
            agentRole: mappedRole as AgentRole,
            content: `${step.step_name} 执行失败: ${step.error || ''}`,
            type: 'thinking',
          });
        } else if (step.status === 'skipped') {
          updateAgentStatus(agentId, 'idle', step.step_name);
          addMessage({
            agentId,
            agentRole: mappedRole as AgentRole,
            content: `${step.step_name} 已跳过（条件不满足）`,
            type: 'thinking',
          });
        }
      });

      updateProgress(completed ? 100 : Math.round((results.filter((r) => r.status === 'completed').length / results.length) * 100));
    } catch (err: unknown) {
      setExecutionError(err instanceof Error ? err.message : '执行失败');
    } finally {
      setIsExecuting(false);
    }
  };

  const mapSkillToAgentRole = (skillId: string): AgentRole => {
    const ceoSkills = ['requirement-analysis', 'write-prd', 'business-model', 'pricing-strategy', 'scope-manager'];
    const designerSkills = ['ux-design', 'frontend-design', 'ux-designer', 'prototype-prompt-generator'];
    const engSkills = ['tech-architecture', 'code-developer', 'api-design', 'refactoring', 'milestone-plan'];
    const qaSkills = ['security-audit', 'security-scanner', 'test-validator', 'auto-test', 'compliance-check'];
    if (ceoSkills.includes(skillId)) return 'ceo';
    if (designerSkills.includes(skillId)) return 'designer';
    if (engSkills.includes(skillId)) return 'engManager';
    if (qaSkills.includes(skillId)) return 'qaEngineer';
    return 'orchestrator';
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <NavHeader>
        <div className="text-sm text-slate-500">
          进度: {overallProgress.toFixed(0)}%
        </div>
      </NavHeader>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* Template Selection */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-4">可视化工作流编排</h1>
          <div className="flex gap-3 flex-wrap">
            {WORKFLOW_TEMPLATES.map((template) => (
              <button
                key={template.id}
                onClick={() => setSelectedTemplate(template.id)}
                className={`px-4 py-2 rounded-lg border text-left transition-colors ${
                  selectedTemplate === template.id
                    ? 'border-sky-500 bg-sky-50 text-sky-700'
                    : 'border-slate-300 bg-white hover:border-sky-300'
                }`}
              >
                <div className="font-medium">{template.name}</div>
                <div className="text-xs text-slate-500">{template.description}</div>
              </button>
            ))}
            <button
              onClick={() => setSelectedTemplate('')}
              className="px-4 py-2 rounded-lg border border-dashed border-slate-300 text-slate-500 hover:border-sky-300"
            >
              + 空白画布
            </button>
          </div>
        </div>

        {/* Workflow Inputs */}
        {selectedTemplate && (
          <div className="mb-6 bg-white rounded-lg shadow p-4 dark:bg-slate-800">
            <h3 className="font-semibold mb-3">工作流输入</h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  产品想法 / 主题
                </label>
                <input
                  type="text"
                  value={workflowInputs.idea}
                  onChange={(e) => setWorkflowInputs({ ...workflowInputs, idea: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="描述你的产品想法"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  目标用户
                </label>
                <input
                  type="text"
                  value={workflowInputs.targetUsers}
                  onChange={(e) => setWorkflowInputs({ ...workflowInputs, targetUsers: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="目标用户群体"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  行业
                </label>
                <select
                  value={workflowInputs.industry}
                  onChange={(e) => setWorkflowInputs({ ...workflowInputs, industry: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                >
                  <option value="medical">医疗健康</option>
                  <option value="saas">SaaS</option>
                  <option value="ecommerce">电商</option>
                  <option value="other">其他</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  约束条件
                </label>
                <input
                  type="text"
                  value={workflowInputs.constraints}
                  onChange={(e) => setWorkflowInputs({ ...workflowInputs, constraints: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                  placeholder="预算、时间、合规要求等"
                />
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleRunWorkflow}
                  disabled={isExecuting}
                  className="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50"
                >
                  {isExecuting ? 'AI 处理中，预计 30-60 秒...' : '▶ 运行工作流'}
                </button>
                {executionError && (
                  <span className="text-sm text-rose-600">{executionError}</span>
                )}
              </div>
              {isExecuting && (
                <div className="w-full max-w-md">
                  <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                    <span>执行进度</span>
                    <span>{overallProgress}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-sky-500 transition-all duration-500"
                      style={{ width: `${overallProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Sidebar - Agents */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-3">Multi-Agent 团队</h3>
              <div className="space-y-2">
                {Object.entries(AGENT_CONFIGS).map(([role, config]) => {
                  const agent = agents.find((a) => a.role === role);
                  return (
                    <div
                      key={role}
                      className="flex items-center gap-3 p-2 rounded-lg bg-slate-50"
                    >
                      <span className="text-2xl">{config.avatar}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">
                          {config.name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {agent?.status === 'working'
                            ? '工作中...'
                            : agent?.status === 'completed'
                            ? '已完成'
                            : agent?.status === 'error'
                            ? '出错'
                            : '待命中'}
                        </div>
                      </div>
                      <div
                        className={`w-2 h-2 rounded-full ${
                          agent?.status === 'working'
                            ? 'bg-sky-500 animate-pulse'
                            : agent?.status === 'completed'
                            ? 'bg-emerald-500'
                            : agent?.status === 'error'
                            ? 'bg-rose-500'
                            : 'bg-slate-300'
                        }`}
                      />
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Agent Skills */}
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-3">技能库</h3>
              <div className="space-y-2 text-sm">
                {agents.map((agent) => (
                  <div key={agent.id}>
                    <div className="font-medium text-slate-700">
                      {agent.avatar} {agent.name}
                    </div>
                    <div className="text-xs text-slate-500 ml-6">
                      {agent.skills.slice(0, 3).join(', ')}
                      {agent.skills.length > 3 && '...'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Center - Canvas */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow h-[600px]">
              {selectedTemplate ? (
                <WorkflowCanvas
                  templateId={selectedTemplate}
                  isExecuting={isExecuting}
                  executionResults={executionResults}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-400">
                  选择一个模板或创建空白画布
                </div>
              )}
            </div>
          </div>

          {/* Right Sidebar - Logs */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow h-[600px] flex flex-col">
              {/* Tabs */}
              <div className="flex border-b">
                {(['logs', 'messages', 'conflicts'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab as any)}
                    className={`flex-1 py-2 text-sm font-medium ${
                      activeTab === tab
                        ? 'text-sky-600 border-b-2 border-sky-600'
                        : 'text-slate-500'
                    }`}
                  >
                    {tab === 'logs'
                      ? `决策日志 (${reasoningLogs.length})`
                      : tab === 'messages'
                      ? `消息 (${messages.length})`
                      : `冲突 (${conflicts.length})`}
                  </button>
                ))}
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-4">
                {activeTab === 'logs' && (
                  <div className="space-y-3">
                    {reasoningLogs.length === 0 ? (
                      <div className="text-sm text-slate-400 text-center py-8">
                        暂无决策日志
                      </div>
                    ) : (
                      reasoningLogs.map((log) => (
                        <div
                          key={log.id}
                          className="p-3 rounded-lg bg-slate-50 text-sm"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">
                              {AGENT_CONFIGS[log.agentRole].avatar}{' '}
                              {AGENT_CONFIGS[log.agentRole].name}
                            </span>
                            <span className="text-xs text-slate-400">
                              {log.timestamp.toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="text-slate-600">{log.action}</div>
                          <div className="mt-2 flex items-center gap-2">
                            <div className="flex-1 h-1 bg-slate-200 rounded-full">
                              <div
                                className="h-1 bg-purple-500 rounded-full"
                                style={{ width: `${log.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-slate-500">
                              {(log.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="mt-1 text-xs text-slate-500 italic">
                            "{log.reasoning}"
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'messages' && (
                  <div className="space-y-3">
                    {messages.length === 0 ? (
                      <div className="text-sm text-slate-400 text-center py-8">
                        暂无消息
                      </div>
                    ) : (
                      messages.map((msg) => (
                        <div
                          key={msg.id}
                          className="p-3 rounded-lg bg-slate-50 text-sm"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span>
                              {AGENT_CONFIGS[msg.agentRole].avatar}
                            </span>
                            <span className="font-medium">
                              {AGENT_CONFIGS[msg.agentRole].name}
                            </span>
                          </div>
                          <div className="text-slate-600">{msg.content}</div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'conflicts' && (
                  <div className="space-y-3">
                    {conflicts.length === 0 ? (
                      <div className="text-sm text-slate-400 text-center py-8">
                        暂无冲突
                      </div>
                    ) : (
                      conflicts.map((conflict) => (
                        <div
                          key={conflict.id}
                          className={`p-3 rounded-lg text-sm ${
                            conflict.resolved
                              ? 'bg-emerald-50'
                              : 'bg-rose-50'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span>
                              {AGENT_CONFIGS[conflict.agentA].avatar}
                            </span>
                            <span>vs</span>
                            <span>
                              {AGENT_CONFIGS[conflict.agentB].avatar}
                            </span>
                          </div>
                          <div className="text-slate-700">{conflict.issue}</div>
                          {conflict.resolved && (
                            <div className="mt-1 text-xs text-emerald-600">
                              ✓ 已解决: {conflict.resolution}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* Clear Button */}
              <div className="p-4 border-t">
                <button
                  onClick={clearLogs}
                  className="w-full py-2 text-sm text-slate-500 hover:text-slate-700"
                >
                  清空日志
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
