'use client'

import { useState } from 'react'
import { useReviewWorkflowStore, STAGE_CONFIG, type ReviewWorkflow, type ReviewStage, type ReviewComment } from '@/stores/reviewWorkflowStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui-from-ai-pm/card'
import { Button } from '@/components/ui-from-ai-pm/button'
import { Badge } from '@/components/ui-from-ai-pm/badge'
import { Input } from '@/components/ui-from-ai-pm/input'
import { ScrollArea } from '@/components/ui-from-ai-pm/scroll-area'
import { Textarea } from '@/components/ui-from-ai-pm/textarea'
import {
  GitPullRequest,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  MessageSquare,
  ChevronRight,
  RotateCcw,
  Send,
  User,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const STATUS_CONFIG = {
  pending: { label: '待处理', color: 'bg-gray-400', icon: Clock },
  'in-progress': { label: '进行中', color: 'bg-sky-500', icon: RotateCcw },
  approved: { label: '已通过', color: 'bg-emerald-500', icon: CheckCircle },
  rejected: { label: '已驳回', color: 'bg-rose-500', icon: XCircle },
  'needs-revision': { label: '需修改', color: 'bg-amber-500', icon: AlertCircle },
}

const STAGE_ICONS: Record<ReviewStage, typeof CheckCircle> = {
  draft: Clock,
  'medical-review': User,
  'compliance-review': AlertCircle,
  'technical-review': RotateCcw,
  'branch-review': User,
  approved: CheckCircle,
  rejected: XCircle,
}

interface WorkflowDetailProps {
  workflow: ReviewWorkflow
  onBack: () => void
}

function WorkflowDetail({ workflow, onBack }: WorkflowDetailProps) {
  const { addComment, approveStage, rejectStage, requestRevision, reviewers } = useReviewWorkflowStore()
  const [comment, setComment] = useState('')
  const currentUserId = 'rev-1' // Mock current user

  const handleAddComment = () => {
    if (!comment.trim()) return
    addComment(workflow.id, {
      stage: workflow.currentStage,
      reviewerId: currentUserId,
      reviewerName: reviewers.find(r => r.id === currentUserId)?.name || '',
      reviewerRole: reviewers.find(r => r.id === currentUserId)?.role || '',
      content: comment,
      type: 'comment',
    })
    setComment('')
  }

  const handleApprove = () => {
    approveStage(workflow.id, workflow.currentStage, currentUserId)
  }

  const handleReject = () => {
    const reason = prompt('请输入驳回原因：')
    if (reason) {
      rejectStage(workflow.id, workflow.currentStage, currentUserId, reason)
    }
  }

  const handleRequestRevision = () => {
    const feedback = prompt('请输入修改建议：')
    if (feedback) {
      requestRevision(workflow.id, workflow.currentStage, currentUserId, feedback)
    }
  }

  const currentStageConfig = STAGE_CONFIG.find(s => s.stage === workflow.currentStage)
  const isCurrentStageApprover = workflow.stages.find(s => s.stage === workflow.currentStage)?.assignedReviewers.includes(currentUserId)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onBack}>
          ← 返回列表
        </Button>
      </div>

      {/* Header */}
      <div className="p-4 bg-muted rounded-lg">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-medium">{workflow.requirementTitle}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              提交人: {workflow.submitterName} | 提交时间: {new Date(workflow.createdAt).toLocaleDateString()}
            </p>
          </div>
          <Badge className={cn('text-white', STATUS_CONFIG[workflow.status].color)}>
            {STATUS_CONFIG[workflow.status].label}
          </Badge>
        </div>
      </div>

      {/* Stage Progress */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {STAGE_CONFIG.filter(s => s.order < 5).map((stage, index) => {
          const stageStatus = workflow.stages.find(s => s.stage === stage.stage)?.status
          const StageIcon = STAGE_ICONS[stage.stage]
          const isActive = workflow.currentStage === stage.stage

          return (
            <div key={stage.stage} className="flex items-center shrink-0">
              <div className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg',
                isActive ? 'bg-primary text-primary-foreground' :
                stageStatus === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                'bg-muted'
              )}>
                <StageIcon className="w-4 h-4" />
                <span className="text-sm font-medium">{stage.name}</span>
                {stageStatus === 'approved' && <CheckCircle className="w-4 h-4" />}
              </div>
              {index < STAGE_CONFIG.filter(s => s.order < 5).length - 1 && (
                <ChevronRight className="w-4 h-4 mx-1 text-muted-foreground" />
              )}
            </div>
          )
        })}
      </div>

      {/* Comments */}
      <div className="space-y-3">
        <h3 className="font-medium">评审记录</h3>
        <ScrollArea className="h-64 border rounded-lg p-4">
          <div className="space-y-4">
            {workflow.comments.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">暂无评审记录</p>
            ) : (
              workflow.comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{c.reviewerName}</span>
                      <Badge variant="secondary" className="text-xs">{c.reviewerRole}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {new Date(c.createdAt).toLocaleString()}
                      </span>
                    </div>
                    <div className="mt-1 p-2 bg-muted rounded text-sm">
                      {c.content}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Actions */}
      {isCurrentStageApprover && workflow.status !== 'approved' && workflow.status !== 'rejected' && (
        <div className="space-y-3">
          <h3 className="font-medium">添加评审意见</h3>
          <Textarea
            placeholder="输入评审意见..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
          <div className="flex gap-2">
            <Button onClick={handleAddComment} variant="outline">
              <MessageSquare className="w-4 h-4 mr-1" />
              添加评论
            </Button>
            <Button onClick={handleApprove} className="bg-emerald-600 hover:bg-emerald-700">
              <CheckCircle className="w-4 h-4 mr-1" />
              通过
            </Button>
            <Button onClick={handleRequestRevision} variant="outline" className="text-amber-600">
              <AlertCircle className="w-4 h-4 mr-1" />
              需修改
            </Button>
            <Button onClick={handleReject} variant="outline" className="text-rose-600">
              <XCircle className="w-4 h-4 mr-1" />
              驳回
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export function ReviewWorkflowList() {
  const { workflows, getWorkflowsByStatus, reviewers } = useReviewWorkflowStore()
  const [selectedWorkflow, setSelectedWorkflow] = useState<ReviewWorkflow | null>(null)
  const [filter, setFilter] = useState<'all' | 'pending' | 'in-progress' | 'approved' | 'rejected'>('all')

  const filteredWorkflows = filter === 'all' ? workflows : getWorkflowsByStatus(filter)

  const currentUserId = 'rev-1' // Mock current user
  const myWorkflows = workflows.filter(w =>
    w.stages.some(s =>
      s.assignedReviewers.includes(currentUserId) &&
      (s.status === 'pending' || s.status === 'in-progress')
    )
  )

  if (selectedWorkflow) {
    return (
      <Card>
        <CardContent className="p-6">
          <WorkflowDetail
            workflow={selectedWorkflow}
            onBack={() => setSelectedWorkflow(null)}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-5 h-5" />
            需求评审工作流
          </div>
          <Button size="sm">
            <Send className="w-4 h-4 mr-1" />
            提交需求
          </Button>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* My Tasks */}
        {myWorkflows.length > 0 && (
          <div className="p-3 bg-sky-50 border border-sky-200 rounded-lg">
            <h3 className="text-sm font-medium text-sky-800 mb-2">待我处理 ({myWorkflows.length})</h3>
            <div className="space-y-2">
              {myWorkflows.slice(0, 3).map((wf) => (
                <button
                  key={wf.id}
                  onClick={() => setSelectedWorkflow(wf)}
                  className="w-full flex items-center justify-between p-2 bg-white rounded border hover:border-sky-300 transition-colors"
                >
                  <span className="text-sm truncate">{wf.requirementTitle}</span>
                  <Badge className={cn('text-white text-xs', STATUS_CONFIG[wf.status].color)}>
                    {STAGE_CONFIG.find(s => s.stage === wf.currentStage)?.name}
                  </Badge>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          {(['all', 'in-progress', 'pending', 'approved', 'rejected'] as const).map((f) => (
            <Button
              key={f}
              size="sm"
              variant={filter === f ? 'default' : 'outline'}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? '全部' : STATUS_CONFIG[f]?.label || f}
            </Button>
          ))}
        </div>

        {/* Workflow List */}
        <div className="space-y-2">
          {filteredWorkflows.map((workflow) => {
            const currentStageName = STAGE_CONFIG.find(s => s.stage === workflow.currentStage)?.name
            const StatusIcon = STATUS_CONFIG[workflow.status].icon

            return (
              <button
                key={workflow.id}
                onClick={() => setSelectedWorkflow(workflow)}
                className="w-full flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors text-left"
              >
                <div className={cn('w-10 h-10 rounded-full flex items-center justify-center text-white shrink-0', STATUS_CONFIG[workflow.status].color)}>
                  <StatusIcon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{workflow.requirementTitle}</span>
                    <Badge className={cn('text-white text-xs', STATUS_CONFIG[workflow.status].color)}>
                      {STATUS_CONFIG[workflow.status].label}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                    <span>提交人: {workflow.submitterName}</span>
                    <span>当前阶段: {currentStageName}</span>
                    <span>{workflow.comments.length} 条评审</span>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-muted-foreground shrink-0" />
              </button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
