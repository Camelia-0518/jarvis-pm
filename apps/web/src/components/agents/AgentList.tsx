import React, { useEffect, useState } from 'react';
import { AgentService, AgentInfo } from '@/services/agent';

export const AgentList: React.FC = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AgentService.listAgents()
      .then(setAgents)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="agent-list">
      <h2>可用 Agent</h2>
      <div className="grid gap-4">
        {agents.map((agent) => (
          <div key={agent.name} className="agent-card border p-4 rounded">
            <h3>{agent.name}</h3>
            <p>{agent.description}</p>
            <div className="text-sm text-gray-500">
              版本: {agent.version}
            </div>
            <div className="mt-2">
              {agent.capabilities.map((cap) => (
                <span key={cap} className="tag">
                  {cap}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
