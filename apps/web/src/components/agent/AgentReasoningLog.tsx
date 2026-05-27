'use client'

import { useState } from 'react'
import type { AgentReasoning, AgentConflict } from '@/types/agent'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui-from-ai-pm/card'
import { Badge } from '@/components/ui-from-ai-pm/badge'
import { Button } from '@/components/ui-from-ai-pm/button'
import { ScrollArea } from '@/components/ui-from-ai-pm/scroll-area'
import {
  Brain,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  GitPullRequest,
  MessageSquare,
  BarChart3
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface AgentReasoningLogProps {
  reasoning?: AgentReasoning[]
  conflicts?: AgentConflict[]
  taskName: string
  onResolveConflict?: (conflictId: string, resolution: string) => void
}

export function AgentReasoningLog({
  reasoning = [],
  conflicts = [],
  taskName,
  onResolveConflict
}: AgentReasoningLogProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [resolvingConflict, setResolvingConflict] = useState<string | null>(null)
  const [resolutionText, setResolutionText] = useState('')

  const toggleStep = (id: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedSteps(newExpanded)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-emerald-500'
    if (confidence >= 0.5) return 'bg-amber-500'
    return 'bg-rose-500'
  }

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Brain className="w-4 h-4" />
          Agent 决策日志
          <Badge variant="outline" className="ml-2 text-xs">
            {taskName}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 决策步骤 */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground">思考过程</h4>
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {reasoning.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-8">
                  <Brain className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  暂无决策日志
                </div>
              ) : (
                reasoning.map((step, index) => (
                  <div
                    key={step.id}
                    className="border rounded-lg overflow-hidden"
                  >
                    <button
                      onClick={() => toggleStep(step.id)}
                      className="w-full flex items-center gap-3 p-3 hover:bg-muted transition-colors"
                    >
                      {expandedSteps.has(step.id) ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}

                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        getConfidenceColor(step.confidence)
                      )} />

                      <span className="text-sm font-medium flex-1 text-left">
                        步骤 {index + 1}: {step.action}
                      </span>

                      <Badge variant="secondary" className="text-xs">
                        置信度 {Math.round(step.confidence * 100)}%
                      </Badge>
                    </button>

                    {expandedSteps.has(step.id) && (
                      <div className="px-3 pb-3 space-y-3 border-t bg-muted/50">
                        <p className="text-sm pt-2">{step.reasoning}</p>

                        {step.evidence && step.evidence.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">依据</p>
                            <ul className="space-y-1">
                              {step.evidence.map((ev, idx) => (
                                <li key={idx} className="text-xs flex items-start gap-2">
                                  <span className="text-muted-foreground">•</span>
                                  {ev}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {step.input && (
                          <div className="text-xs text-muted-foreground">
                            <span className="font-medium">输入:</span> {step.input}
                          </div>
                        )}

                        {step.output && (
                          <div className="text-xs text-muted-foreground">
                            <span className="font-medium">输出:</span> {step.output}
                          </div>
                        )}

                        <div className="text-xs text-muted-foreground">
                          {new Date(step.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        {/* 冲突标记 */}
        {conflicts.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-2">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              Agent 意见冲突 ({conflicts.length})
            </h4>
            <div className="space-y-2">
              {conflicts.map((conflict) => (
                <div
                  key={conflict.id}
                  className={cn(
                    "border rounded-lg p-3",
                    !conflict.resolved ? 'border-amber-500/50 bg-amber-50/50' : 'border-emerald-500/50 bg-emerald-50/50'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <GitPullRequest className="w-4 h-4 mt-0.5 text-amber-600" />
                    <div className="flex-1 space-y-2">
                      <div>
                        <p className="text-sm font-medium">{conflict.issue}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {conflict.agentA} vs {conflict.agentB}
                        </p>
                      </div>

                      {!conflict.resolved ? (
                        resolvingConflict === conflict.id ? (
                          <div className="space-y-2">
                            <textarea
                              className="w-full p-2 text-sm border rounded-md"
                              placeholder="输入您的裁决..."
                              value={resolutionText}
                              onChange={(e) => setResolutionText(e.target.value)}
                              rows={2}
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => {
                                  onResolveConflict?.(conflict.id, resolutionText)
                                  setResolvingConflict(null)
                                  setResolutionText('')
                                }}
                              >
                                确认裁决
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setResolvingConflict(null)}
                              >
                                取消
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setResolvingConflict(conflict.id)}
                          >
                            <MessageSquare className="w-3 h-3 mr-1" />
                            裁决冲突
                          </Button>
                        )
                      ) : (
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-emerald-500" />
                          <span>已解决: {conflict.resolution}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
