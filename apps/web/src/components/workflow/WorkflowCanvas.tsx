'use client';

import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
  type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';

import AgentNode from './AgentNode';
import { useAgentStore } from '@/stores/agentStore';
import { WORKFLOW_TEMPLATES, AGENT_CONFIGS, type AgentRole } from '@/types/agent';

const nodeTypes = {
  agent: AgentNode,
};

interface WorkflowCanvasProps {
  templateId?: string;
  isExecuting?: boolean;
  executionResults?: Array<Record<string, unknown>> | null;
}

export default function WorkflowCanvas({
  templateId,
  isExecuting,
  executionResults,
}: WorkflowCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const { initializeAgents, updateAgentStatus, updateProgress } = useAgentStore();

  // 初始化 Agents
  useEffect(() => {
    initializeAgents();
  }, [initializeAgents]);

  // 加载模板
  useEffect(() => {
    if (templateId) {
      const template = WORKFLOW_TEMPLATES.find((t) => t.id === templateId);
      if (template) {
        loadTemplate(template);
      }
    } else {
      setNodes([]);
      setEdges([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId]);

  // 根据执行结果更新节点状态
  useEffect(() => {
    if (!executionResults || executionResults.length === 0 || !templateId) return;

    const template = WORKFLOW_TEMPLATES.find((t) => t.id === templateId);
    if (!template) return;

    // 按顺序更新每个节点状态
    executionResults.forEach((step, index) => {
      const nodeRole = template.nodes[index]?.role;
      if (!nodeRole) return;
      const nodeId = `node-${nodeRole}`;

      let status: 'pending' | 'running' | 'completed' | 'error' = 'pending';
      if (step.status === 'completed') status = 'completed';
      else if (step.status === 'failed') status = 'error';
      else if (step.status === 'running') status = 'running';
      else if (step.status === 'skipped') status = 'pending';

      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, status, progress: status === 'completed' ? 100 : status === 'error' ? 0 : 50 } }
            : n
        )
      );

      // 更新边动画：如果当前步骤已完成，激活指向下一个节点的边
      if (status === 'completed') {
        const nextRole = template.nodes[index + 1]?.role;
        if (nextRole) {
          setEdges((eds) =>
            eds.map((e) =>
              e.source === nodeId && e.target === `node-${nextRole}`
                ? { ...e, animated: true }
                : e
            )
          );
        }
      }
    });

    // 更新总进度
    const completedCount = executionResults.filter((r) => r.status === 'completed').length;
    updateProgress(Math.round((completedCount / executionResults.length) * 100));
  }, [executionResults, templateId, setEdges, setNodes, updateProgress]);

  // 执行中时，显示所有节点为运行中（按顺序）
  useEffect(() => {
    if (!isExecuting || !templateId) return;

    const template = WORKFLOW_TEMPLATES.find((t) => t.id === templateId);
    if (!template) return;

    // 重置所有节点为 pending
    template.nodes.forEach((node) => {
      const nodeId = `node-${node.role}`;
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, status: 'pending', progress: 0 } } : n
        )
      );
    });

    // 依次高亮每个节点为 running
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex >= template.nodes.length) {
        clearInterval(interval);
        return;
      }

      // 把当前节点设为 running
      const role = template.nodes[currentIndex].role;
      const nodeId = `node-${role}`;
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, status: 'running', progress: 30 } } : n
        )
      );
      updateAgentStatus(`agent-${role}`, 'working', '执行中...');

      // 激活指向当前节点的边
      setEdges((eds) =>
        eds.map((e) =>
          e.target === nodeId ? { ...e, animated: true } : { ...e, animated: false }
        )
      );

      currentIndex++;
    }, 1500);

    return () => clearInterval(interval);
  }, [isExecuting, templateId, setEdges, setNodes, updateAgentStatus]);

  const loadTemplate = (template: typeof WORKFLOW_TEMPLATES[0]) => {
    const newNodes: Node[] = template.nodes.map((node, index) => ({
      id: `node-${node.role}`,
      type: 'agent',
      position: { x: node.x, y: node.y },
      data: {
        agentRole: node.role,
        status: 'pending',
        progress: 0,
      },
    }));

    const newEdges: Edge[] = template.edges.map((edge, index) => ({
      id: `edge-${index}`,
      source: `node-${edge.source}`,
      target: `node-${edge.target}`,
      label: edge.label,
      animated: false,
    }));

    setNodes(newNodes);
    setEdges(newEdges);
  };

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds));
    },
    [setEdges]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <div className="flex items-center gap-4">
          <h2 className="font-semibold">工作流画布</h2>
          <span className="text-sm text-slate-500">
            {nodes.length} 个节点 · {edges.length} 个连接
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isExecuting && (
            <span className="text-sm text-sky-600 animate-pulse">
              正在调用后端 AI 执行...
            </span>
          )}
          {!isExecuting && executionResults && executionResults.length > 0 && (
            <span className="text-sm text-emerald-600">
              执行完成
            </span>
          )}
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        {nodes.length > 0 ? (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap
              nodeStrokeWidth={3}
              zoomable
              pannable
            />
          </ReactFlow>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400">
            选择一个模板开始编排工作流
          </div>
        )}
      </div>
    </div>
  );
}
