'use client';

import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import type { AgentRole } from '@/types/agent';
import { AGENT_CONFIGS } from '@/types/agent';

interface AgentNodeData {
  agentRole: AgentRole;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  output?: string;
}

const statusColors = {
  pending: 'border-slate-300 bg-slate-50',
  running: 'border-sky-500 bg-sky-50 shadow-lg shadow-sky-500/20',
  completed: 'border-emerald-500 bg-emerald-50',
  error: 'border-rose-500 bg-rose-50',
};

const statusIcons = {
  pending: '⏳',
  running: '▶️',
  completed: '✅',
  error: '❌',
};

function AgentNode({ data }: NodeProps<AgentNodeData>) {
  const config = AGENT_CONFIGS[data.agentRole];

  return (
    <div
      className={`w-48 rounded-lg border-2 p-3 transition-all ${statusColors[data.status]}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400" />

      <div className="flex items-center gap-2">
        <span className="text-2xl">{config.avatar}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate">{config.name}</div>
          <div className="text-xs text-slate-500">{statusIcons[data.status]}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-2">
        <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-sky-500 transition-all duration-500"
            style={{ width: `${data.progress}%` }}
          />
        </div>
        <div className="text-xs text-slate-500 mt-1 text-right">{data.progress}%</div>
      </div>

      {/* Output Preview */}
      {data.output && (
        <div className="mt-2 text-xs text-slate-600 bg-white/50 rounded p-1.5 line-clamp-2">
          {data.output}
        </div>
      )}

      <Handle type="source" position={Position.Right} className="!bg-slate-400" />
    </div>
  );
}

export default memo(AgentNode);
