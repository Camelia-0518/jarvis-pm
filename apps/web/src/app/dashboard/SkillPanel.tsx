"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { workflowApi, skillsApi, type SkillExecutionRecord } from "@/lib/api";
import { useProjectStore } from "@/stores/projectStore";
import { toast } from "sonner";

function getWSBase() {
  if (typeof window !== "undefined") {
    return `ws://${window.location.hostname}:8000/api/v1`;
  }
  return process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1";
}

const SKILL_CHAINS = [
  {
    id: "full-delivery",
    name: "完整交付方案",
    icon: "🚀",
    description: "需求探索 → PRD → 交付计划 → 合规审查",
    steps: 4,
    featured: true,
  },
  {
    id: "project-kickoff",
    name: "项目启动包",
    icon: "📋",
    description: "需求分析 → 里程碑 → 项目章程",
    steps: 3,
  },
  {
    id: "weekly-report",
    name: "周报/状态报告",
    icon: "📊",
    description: "一键生成专业项目周报",
    steps: 1,
    featured: true,
  },
  {
    id: "stakeholder-brief",
    name: "干系人沟通",
    icon: "💬",
    description: "按受众定制化简报（客户/研发/高层）",
    steps: 1,
  },
  {
    id: "requirement-discovery",
    name: "需求探索",
    icon: "🔍",
    description: "需求分析 → 商业模式 → 洞察报告",
    steps: 3,
  },
  {
    id: "delivery-playbook",
    name: "交付路径手册",
    icon: "📖",
    description: "标准化交付方法论 + 踩坑手册 + 检查清单",
    steps: 1,
  },
  {
    id: "retrospective",
    name: "项目复盘",
    icon: "🔄",
    description: "Keep/Improve/Stop/Start + 量化总结 + 行动项",
    steps: 1,
  },
  {
    id: "compliance-audit",
    name: "合规审查",
    icon: "🔒",
    description: "合规检查 → 医疗评审 → 审查报告",
    steps: 3,
  },
  {
    id: "quick-prd",
    name: "快速 PRD",
    icon: "📝",
    description: "医疗PRD一键生成",
    steps: 1,
  },
  {
    id: "ai-model-prd",
    name: "AI 产品 PRD",
    icon: "🤖",
    description: "大模型产品专用模板",
    steps: 1,
  },
  {
    id: "devops-prd",
    name: "DevOps PRD",
    icon: "⚙️",
    description: "内部工具/平台专用模板",
    steps: 1,
  },
];

export default function SkillPanel() {
  const router = useRouter();
  const { projects } = useProjectStore();
  const [recentSkills, setRecentSkills] = useState<
    Array<{ id: string; name: string; status: string; time: string }>
  >([]);
  const [runningChains, setRunningChains] = useState<Record<string, boolean>>({});
  const [chainProgress, setChainProgress] = useState<{
    current: number;
    total: number;
    stepName: string;
  } | null>(null);
  const [pendingChainId, setPendingChainId] = useState<string | null>(null);
  const [stepDetails, setStepDetails] = useState<Record<string, { timeMs: number; tokens: number }>>({});
  const [elapsedSec, setElapsedSec] = useState(0);
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connectWorkflowWS = (
    executionId: string,
    projectId: string,
    toastId: string | number
  ) => {
    const ws = new WebSocket(`${getWSBase()}/ws/workflow/${executionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      toast.loading("技能链已启动，实时监控中...", { id: toastId });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "start":
            setChainProgress({
              current: 0,
              total: msg.totalSteps || msg.total_steps || 3,
              stepName: "启动中...",
            });
            setStepDetails({});
            setElapsedSec(0);
            if (elapsedRef.current) clearInterval(elapsedRef.current);
            elapsedRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000);
            break;
          case "step_start":
            setChainProgress((prev) => ({
              current: (msg.step || 0),
              total: prev?.total || msg.total || 3,
              stepName: msg.step_name || msg.stepName || "",
            }));
            toast.loading(
              `执行中: ${msg.step_name || msg.stepName} (${msg.step || 0}/${msg.total || "?"})`,
              { id: toastId }
            );
            break;
          case "step_complete":
            toast.loading(
              `完成: ${msg.step_name || msg.stepName}`,
              { id: toastId }
            );
            break;
          case "step_detail":
            setStepDetails((prev) => ({
              ...prev,
              [msg.step_name || msg.skill_id || ""]: {
                timeMs: msg.execution_time_ms || 0,
                tokens: msg.token_usage?.total || 0,
              },
            }));
            break;
          case "monitoring_update":
            break;
          case "complete":
            if (elapsedRef.current) { clearInterval(elapsedRef.current); elapsedRef.current = null; }
            toast.success("技能链执行完成！", { id: toastId });
            setRunningChains((prev) => ({ ...prev, [executionId]: false }));
            setChainProgress(null);
            ws.close();
            router.push(`/workspace?id=${projectId}`);
            break;
          case "error":
            if (elapsedRef.current) { clearInterval(elapsedRef.current); elapsedRef.current = null; }
            toast.error(`执行失败: ${msg.error || "未知错误"}`, { id: toastId });
            setRunningChains((prev) => ({ ...prev, [executionId]: false }));
            setChainProgress(null);
            ws.close();
            break;
        }
      } catch {
        // 非 JSON 消息，忽略
      }
    };

    ws.onerror = () => {
      // WebSocket 连接失败，降级到轮询
      toast.error("实时连接失败，切换到轮询模式", { id: toastId });
      pollExecutionFallback(executionId, projectId, toastId);
    };

    ws.onclose = () => {
      setChainProgress(null);
    };
  };

  // 降级轮询（WebSocket 不可用时）
  const pollExecutionFallback = async (
    executionId: string,
    projectId: string,
    toastId: string | number
  ) => {
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      try {
        const status = await workflowApi.getExecution(executionId);
        if (status.status === "completed") {
          toast.success("技能链执行完成！", { id: toastId });
          setRunningChains((prev) => ({ ...prev, [executionId]: false }));
          router.push(`/workspace?id=${projectId}`);
          return;
        }
        if (status.status === "failed") {
          toast.error("执行失败", { id: toastId });
          setRunningChains((prev) => ({ ...prev, [executionId]: false }));
          return;
        }
      } catch {
        // continue
      }
    }
    toast.error("执行超时", { id: toastId });
    setRunningChains((prev) => ({ ...prev, [executionId]: false }));
  };

  const handleExecuteChain = async (chainId: string) => {
    if (projects.length === 0) {
      toast.error("请先创建一个项目");
      return;
    }
    if (projects.length === 1) {
      executeChainOnProject(chainId, projects[0]);
      return;
    }
    setPendingChainId(chainId);
  };

  const getChainInputs = (chainId: string, project: typeof projects[0]) => {
    const base = {
      idea: project.description || project.name,
      targetUsers: "产品团队（含医护人员和患者）",
      industry: project.industry || "medical",
      constraints: "须符合等保三级要求，支持多院区部署",
      teamSize: "5",
    };
    switch (chainId) {
      case "full-delivery":
        return { ...base };
      case "requirement-discovery":
        return { idea: base.idea, targetUsers: base.targetUsers, industry: base.industry, constraints: base.constraints };
      case "compliance-audit":
        return { prdContent: project.description || project.name, complianceLevel: "level3", featureType: "other" };
      case "quick-prd":
        return { requirementAnalysis: project.description || project.name, template: base.industry, detailLevel: "standard" };
      case "ai-model-prd":
        return { requirementAnalysis: project.description || project.name, template: "ai-model", detailLevel: "detailed" };
      case "devops-prd":
        return { requirementAnalysis: project.description || project.name, template: "devops", detailLevel: "detailed" };
      case "project-kickoff":
        return { idea: base.idea, targetUsers: base.targetUsers, industry: base.industry, constraints: base.constraints, teamSize: base.teamSize };
      case "weekly-report":
        return { requirementAnalysis: "请基于以下项目信息生成本周项目状态报告：\n" + (project.description || project.name) + "\n\n本周完成工作：\n- [请填写本周完成的主要工作]\n\n下周计划：\n- [请填写下周计划]\n\n当前风险：\n- [请填写当前活跃风险]" };
      case "stakeholder-brief":
        return { requirementAnalysis: "请基于以下项目信息生成面向[客户/研发/高层]的沟通简报：\n" + (project.description || project.name) + "\n\n最新进展：\n- [填写最新进展]\n\n需要沟通的事项：\n- [填写需要沟通的事项]" };
      case "delivery-playbook":
        return { requirementAnalysis: "请基于以下项目类型生成标准化交付路径手册：\n" + (project.description || project.name) + "\n\n项目类型：医疗信息化系统交付\n团队规模：" + base.teamSize + "人\n目标：将复杂医疗业务抽象为标准化交付路径" };
      case "retrospective":
        return { requirementAnalysis: "请基于以下项目信息生成项目复盘报告：\n" + (project.description || project.name) + "\n\n项目实际工期：[填写]\n做得好的：[填写]\n需要改进的：[填写]\n踩过的坑：[填写]\n下个项目应该尝试的：[填写]" };
      default:
        return { ...base };
    }
  };

  const executeChainOnProject = async (chainId: string, project: typeof projects[0]) => {
    setPendingChainId(null);
    const toastId = toast.loading("正在启动技能链...");
    try {
      const res = await workflowApi.executeChain({
        chain_id: chainId,
        inputs: getChainInputs(chainId, project),
        project_id: project.id,
      });
      setRunningChains((prev) => ({ ...prev, [res.execution_id]: true }));
      connectWorkflowWS(res.execution_id, project.id, toastId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "启动失败";
      toast.error(`技能链启动失败：${msg}`, { id: toastId });
    }
  };

  useEffect(() => {
    async function fetchSkillData() {
      try {
        const executions = await skillsApi.getExecutions({ limit: 50 });
        const records = Array.isArray(executions) ? executions : [];

        const mapped = records.slice(0, 5).map((item: SkillExecutionRecord) => ({
          id: item.id || `skill-${Math.random()}`,
          name: item.skillName || item.skillId || "技能执行",
          status: item.status || "completed",
          time: item.completedAt
            ? new Date(item.completedAt).toLocaleString()
            : item.createdAt
            ? new Date(item.createdAt).toLocaleString()
            : "-",
        }));
        setRecentSkills(mapped);
      } catch {
        setRecentSkills([]);
      }
    }
    fetchSkillData();
  }, []);

  return (
    <div className="mb-8 rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
        ⚡ 技能面板
      </h2>

      <div className="mb-6">
        <h3 className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
          技能链（一键执行）
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SKILL_CHAINS.map((chain) => (
            <button
              key={chain.id}
              disabled={runningChains[chain.id]}
              onClick={() => handleExecuteChain(chain.id)}
              className="relative flex items-start gap-3 rounded-lg border border-slate-200 p-4 text-left transition-colors hover:border-sky-300 hover:bg-sky-50 dark:border-slate-700 dark:hover:border-sky-700 dark:hover:bg-sky-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {chain.featured && (
                <span className="absolute -top-2 -right-2 rounded-full bg-sky-500 px-2 py-0.5 text-xs text-white font-medium">
                  推荐
                </span>
              )}
              <span className="text-2xl">{chain.icon}</span>
              <div>
                <div className="font-medium text-slate-900 dark:text-white">
                  {chain.name}
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  {chain.description}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {chain.steps} 个步骤
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {chainProgress && (
        <div className="mb-4 rounded-lg bg-sky-50 p-4 dark:bg-sky-900/20">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-sky-700 dark:text-sky-300">
              技能链执行中
            </span>
            <div className="flex items-center gap-3 text-xs text-sky-500">
              <span>{chainProgress.current}/{chainProgress.total}</span>
              <span className="font-mono">⏱ {elapsedSec}s</span>
            </div>
          </div>
          <div className="w-full h-2 rounded-full bg-sky-200 dark:bg-sky-800">
            <div
              className="h-2 rounded-full bg-sky-500 transition-all duration-500"
              style={{
                width: `${Math.round((Math.min(chainProgress.current, chainProgress.total) / chainProgress.total) * 100)}%`,
              }}
            />
          </div>
          <p className="mt-1 text-xs text-sky-600 dark:text-sky-400">
            {chainProgress.stepName}
          </p>
          {/* Per-step timing details */}
          {Object.keys(stepDetails).length > 0 && (
            <div className="mt-3 space-y-1 border-t border-sky-200 pt-2 dark:border-sky-700">
              {Object.entries(stepDetails).map(([name, detail]) => (
                <div key={name} className="flex items-center justify-between text-xs">
                  <span className="text-sky-600 dark:text-sky-400">✓ {name}</span>
                  <span className="text-sky-500 font-mono">
                    {(detail.timeMs / 1000).toFixed(1)}s
                    {detail.tokens > 0 && ` · ${detail.tokens} tokens`}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Project Picker Modal */}
      {pendingChainId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl dark:bg-slate-800">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
              选择目标项目
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              技能链将对所选项目执行 {SKILL_CHAINS.find((c) => c.id === pendingChainId)?.steps || 0} 个步骤
            </p>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => executeChainOnProject(pendingChainId!, project)}
                  className="w-full text-left rounded-lg border border-slate-200 p-3 transition-colors hover:border-sky-300 hover:bg-sky-50 dark:border-slate-600 dark:hover:border-sky-700 dark:hover:bg-sky-900/20"
                >
                  <div className="font-medium text-slate-900 dark:text-white text-sm">
                    {project.name}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {project.industry || "其他"} · {project.prd_count} 个 PRD · {project.status === "active" ? "进行中" : "已归档"}
                  </div>
                </button>
              ))}
            </div>
            <button
              onClick={() => setPendingChainId(null)}
              className="mt-3 w-full rounded-lg border border-slate-200 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-400 dark:hover:bg-slate-700"
            >
              取消
            </button>
          </div>
        </div>
      )}

      <div>
        <h3 className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
          最近执行
        </h3>
        {recentSkills.length === 0 ? (
          <div className="text-sm text-slate-400 text-center py-4">
            暂无执行记录
          </div>
        ) : (
          <div className="space-y-2">
            {recentSkills.map((skill) => (
              <div
                key={skill.id}
                className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2 dark:bg-slate-700/50"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      skill.status === "completed"
                        ? "bg-emerald-500"
                        : skill.status === "running"
                        ? "bg-sky-500 animate-pulse"
                        : "bg-slate-400"
                    }`}
                  />
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {skill.name}
                  </span>
                </div>
                <span className="text-xs text-slate-500">{skill.time}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
