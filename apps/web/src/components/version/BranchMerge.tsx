'use client'

import { useState } from 'react'
import { useVersionStorePersistent } from '@/stores/versionStorePersistent'
import { useProjectStore } from '@/stores/projectStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui-from-ai-pm/card'
import { Button } from '@/components/ui-from-ai-pm/button'
import { Badge } from '@/components/ui-from-ai-pm/badge'
import { Alert, AlertDescription } from '@/components/ui-from-ai-pm/alert'
import { GitMerge, AlertTriangle, CheckCircle2, XCircle, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BranchMergeProps {
  onClose?: () => void
}

export function BranchMerge({ onClose }: BranchMergeProps) {
  const { branches, versions, currentBranch, switchBranch } = useVersionStorePersistent()
  const { currentProject } = useProjectStore()
  const [sourceBranch, setSourceBranch] = useState('')
  const [targetBranch, setTargetBranch] = useState('')
  const [isMerging, setIsMerging] = useState(false)
  const [mergeResult, setMergeResult] = useState<{
    success: boolean
    message: string
    conflicts?: string[]
  } | null>(null)

  const projectBranches = branches.filter(
    (b) => b.projectId === currentProject?.id
  )

  const analyzeMerge = () => {
    if (!sourceBranch || !targetBranch || sourceBranch === targetBranch) {
      return null
    }

    const sourceVersions = versions.filter(
      (v) => v.branchId === sourceBranch && v.projectId === currentProject?.id
    )
    const targetVersions = versions.filter(
      (v) => v.branchId === targetBranch && v.projectId === currentProject?.id
    )

    // Check for potential conflicts
    const conflicts: string[] = []
    const sourceDocIds = new Set(sourceVersions.map((v) => v.documentId))
    const targetDocIds = new Set(targetVersions.map((v) => v.documentId))

    sourceDocIds.forEach((docId) => {
      if (targetDocIds.has(docId)) {
        const sourceVersion = sourceVersions
          .filter((v) => v.documentId === docId)
          .sort((a, b) => b.versionNumber - a.versionNumber)[0]
        const targetVersion = targetVersions
          .filter((v) => v.documentId === docId)
          .sort((a, b) => b.versionNumber - a.versionNumber)[0]

        if (sourceVersion && targetVersion) {
          // Simulate conflict detection
          if (Math.random() > 0.7) {
            conflicts.push(`${sourceVersion.documentId}: ${sourceVersion.message}`)
          }
        }
      }
    })

    return {
      sourceVersions: sourceVersions.length,
      targetVersions: targetVersions.length,
      conflicts,
      canMerge: conflicts.length === 0,
    }
  }

  const analysis = analyzeMerge()

  const handleMerge = async () => {
    if (!analysis?.canMerge) return

    setIsMerging(true)

    // Simulate merge process
    await new Promise((resolve) => setTimeout(resolve, 1500))

    // Create new versions in target branch from source
    const sourceVersions = versions.filter(
      (v) => v.branchId === sourceBranch && v.projectId === currentProject?.id
    )

    // In real implementation, this would create merge commits
    setMergeResult({
      success: true,
      message: `成功将 ${sourceVersions.length} 个版本合并到目标分支`,
    })

    setIsMerging(false)

    // Switch to target branch
    const target = projectBranches.find((b) => b.id === targetBranch)
    if (target) {
      switchBranch(target.name)
    }
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitMerge className="w-5 h-5" />
          分支合并
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Branch Selection */}
        <div className="grid grid-cols-3 gap-4 items-center">
          <div className="space-y-2">
            <label className="text-sm font-medium">源分支</label>
            <select
              value={sourceBranch}
              onChange={(e) => setSourceBranch(e.target.value)}
              className="w-full p-2 border rounded-lg bg-background"
            >
              <option value="">选择源分支</option>
              {projectBranches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-center">
            <ArrowRight className="w-6 h-6 text-muted-foreground" />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">目标分支</label>
            <select
              value={targetBranch}
              onChange={(e) => setTargetBranch(e.target.value)}
              className="w-full p-2 border rounded-lg bg-background"
            >
              <option value="">选择目标分支</option>
              {projectBranches.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Analysis Result */}
        {analysis && (
          <div className="p-4 border rounded-lg space-y-3">
            <h4 className="font-medium">合并分析</h4>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-muted rounded">
                <p className="text-sm text-muted-foreground">源分支版本</p>
                <p className="text-lg font-semibold">{analysis.sourceVersions}</p>
              </div>
              <div className="p-3 bg-muted rounded">
                <p className="text-sm text-muted-foreground">目标分支版本</p>
                <p className="text-lg font-semibold">{analysis.targetVersions}</p>
              </div>
            </div>

            {analysis.conflicts.length > 0 ? (
              <Alert variant="destructive">
                <AlertTriangle className="w-4 h-4" />
                <AlertDescription>
                  <p className="font-medium">发现 {analysis.conflicts.length} 个潜在冲突：</p>
                  <ul className="mt-2 text-sm space-y-1">
                    {analysis.conflicts.map((conflict, i) => (
                      <li key={i}>{conflict}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            ) : (
              <Alert className="bg-emerald-50 border-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <AlertDescription className="text-emerald-800">
                  未发现冲突，可以安全合并
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Merge Result */}
        {mergeResult && (
          <Alert className={mergeResult.success ? 'bg-emerald-50' : 'bg-rose-50'}>
            {mergeResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-600" />
            )}
            <AlertDescription>{mergeResult.message}</AlertDescription>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            className="flex-1"
            onClick={handleMerge}
            disabled={!analysis?.canMerge || isMerging}
          >
            {isMerging ? (
              <>
                <div className="w-4 h-4 mr-2 animate-spin rounded-full border-2 border-white border-t-transparent" />
                合并中...
              </>
            ) : (
              <>
                <GitMerge className="w-4 h-4 mr-2" />
                合并分支
              </>
            )}
          </Button>
          {onClose && (
            <Button variant="outline" onClick={onClose}>
              取消
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
