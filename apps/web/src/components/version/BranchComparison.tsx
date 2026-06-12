'use client'

import { useState, useEffect } from 'react'
import { useBranchStore, type Branch, type FeatureComparison } from '@/stores/branchStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui-from-ai-pm/card'
import { Button } from '@/components/ui-from-ai-pm/button'
import { Badge } from '@/components/ui-from-ai-pm/badge'
import { ScrollArea } from '@/components/ui-from-ai-pm/scroll-area'
import {
  GitCompare,
  Building2,
  CheckCircle,
  XCircle,
  AlertCircle,
  MapPin,
  Settings,
  Plus,
  ChevronDown,
  ChevronRight,
  Filter,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const STATUS_CONFIG = {
  enabled: { label: '已启用', color: 'bg-emerald-500', icon: CheckCircle },
  disabled: { label: '未启用', color: 'bg-gray-400', icon: XCircle },
  pending: { label: '待上线', color: 'bg-amber-500', icon: AlertCircle },
}

const CATEGORY_CONFIG = {
  standard: { label: '标准功能', color: 'bg-sky-500' },
  custom: { label: '分院特性', color: 'bg-purple-500' },
}

const TYPE_CONFIG = {
  headquarters: { label: '总部', color: 'bg-rose-500' },
  branch: { label: '分院', color: 'bg-sky-500' },
  partner: { label: '合作', color: 'bg-emerald-500' },
}

export function BranchComparison() {
  const {
    branches,
    selectedBranches,
    comparisonView,
    toggleBranchSelection,
    compareBranches,
  } = useBranchStore()

  const [expandedFeatures, setExpandedFeatures] = useState<Set<string>>(new Set())
  const [filterCategory, setFilterCategory] = useState<'all' | 'standard' | 'custom'>('all')
  const [showDifferencesOnly, setShowDifferencesOnly] = useState(false)

  const headquarters = branches.find((b) => b.type === 'headquarters')
  const branchOffices = branches.filter((b) => b.type === 'branch')

  // Auto-select headquarters + branches when selection changes
  useEffect(() => {
    if (selectedBranches.length >= 2) {
      compareBranches(selectedBranches)
    }
  }, [selectedBranches, compareBranches])

  const toggleFeature = (featureName: string) => {
    const newSet = new Set(expandedFeatures)
    if (newSet.has(featureName)) {
      newSet.delete(featureName)
    } else {
      newSet.add(featureName)
    }
    setExpandedFeatures(newSet)
  }

  const filteredComparison = comparisonView.filter((item) => {
    if (filterCategory !== 'all' && item.category !== filterCategory) return false
    if (showDifferencesOnly && item.isConsistent) return false
    return true
  })

  const getDifferencesCount = () => {
    return comparisonView.filter((item) => !item.isConsistent).length
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5" />
            多院区功能对比
          </div>
          <div className="flex items-center gap-2">
            {getDifferencesCount() > 0 && (
              <Badge variant="destructive">
                {getDifferencesCount()} 处差异
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Branch Selection */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            选择要对比的院区（至少2个）
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {branches.map((branch) => {
              const typeConfig = TYPE_CONFIG[branch.type]
              const isSelected = selectedBranches.includes(branch.id)
              return (
                <label
                  key={branch.id}
                  className={cn(
                    'flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors',
                    isSelected
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleBranchSelection(branch.id)}
                    className="w-4 h-4 rounded border-gray-300"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="font-medium text-sm truncate">
                        {branch.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge
                        className={cn('text-[10px] px-1 py-0 h-4 text-white', typeConfig.color)}
                      >
                        {typeConfig.label}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                        <MapPin className="w-3 h-3" />
                        {branch.location}
                      </span>
                    </div>
                  </div>
                </label>
              )
            })}
          </div>
        </div>

        {/* Filters */}
        {comparisonView.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/50 rounded-lg">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">筛选:</span>
            <div className="flex gap-1">
              {(['all', 'standard', 'custom'] as const).map((cat) => (
                <Button
                  key={cat}
                  size="sm"
                  variant={filterCategory === cat ? 'default' : 'outline'}
                  className="h-7 text-xs"
                  onClick={() => setFilterCategory(cat)}
                >
                  {cat === 'all' ? '全部' : CATEGORY_CONFIG[cat].label}
                </Button>
              ))}
            </div>
            <label className="flex items-center gap-2 ml-4 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={showDifferencesOnly}
                onChange={(e) => setShowDifferencesOnly(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300"
              />
              仅显示差异
            </label>
          </div>
        )}

        {/* Comparison Table */}
        {selectedBranches.length < 2 ? (
          <div className="text-center py-12 text-muted-foreground border rounded-lg">
            <GitCompare className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">请选择至少2个院区进行对比</p>
          </div>
        ) : comparisonView.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground border rounded-lg">
            <Building2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">点击&ldquo;开始对比&rdquo;查看功能差异</p>
            <Button
              className="mt-4"
              onClick={() => compareBranches(selectedBranches)}
            >
              开始对比
            </Button>
          </div>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            {/* Header */}
            <div className="flex items-center bg-muted/50 border-b">
              <div className="w-48 p-3 font-medium text-sm border-r">
                功能名称
              </div>
              <div className="flex-1 grid" style={{ gridTemplateColumns: `repeat(${selectedBranches.length}, 1fr)` }}>
                {selectedBranches.map((branchId) => {
                  const branch = branches.find((b) => b.id === branchId)
                  return (
                    <div key={branchId} className="p-3 text-center border-r last:border-r-0">
                      <div className="font-medium text-sm">{branch?.name}</div>
                      <div className="text-[10px] text-muted-foreground">
                        {branch?.features.length} 项功能
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Body */}
            <ScrollArea className="max-h-[400px]">
              <div className="divide-y">
                {filteredComparison.map((item) => {
                  const isExpanded = expandedFeatures.has(item.featureName)
                  const categoryConfig = CATEGORY_CONFIG[item.category]

                  return (
                    <div key={item.featureName}>
                      <button
                        onClick={() => toggleFeature(item.featureName)}
                        className={cn(
                          'w-full flex items-center hover:bg-muted/50 transition-colors',
                          !item.isConsistent && 'bg-rose-50/50'
                        )}
                      >
                        <div className="w-48 p-3 text-left border-r flex items-center gap-2">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                          )}
                          <span className="text-sm truncate">{item.featureName}</span>
                          <Badge
                            className={cn('text-[10px] px-1 py-0 h-4 text-white shrink-0', categoryConfig.color)}
                          >
                            {categoryConfig.label}
                          </Badge>
                          {!item.isConsistent && (
                            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                          )}
                        </div>
                        <div
                          className="flex-1 grid"
                          style={{ gridTemplateColumns: `repeat(${selectedBranches.length}, 1fr)` }}
                        >
                          {item.branches.map((branchStatus) => {
                            const statusConfig = STATUS_CONFIG[branchStatus.status]
                            const StatusIcon = statusConfig.icon

                            return (
                              <div
                                key={branchStatus.branchId}
                                className={cn(
                                  'p-3 text-center border-r last:border-r-0',
                                  branchStatus.hasDifferences && 'bg-rose-50'
                                )}
                              >
                                <div className="flex items-center justify-center gap-1.5">
                                  <StatusIcon className={cn('w-4 h-4', statusConfig.color.replace('bg-', 'text-'))} />
                                  <span className="text-sm">{statusConfig.label}</span>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </button>

                      {/* Expanded Details */}
                      {isExpanded && (
                        <div className="bg-muted/30 border-t">
                          <div className="flex">
                            <div className="w-48 p-3 border-r">
                              <p className="text-xs text-muted-foreground">
                                功能类型: {categoryConfig.label}
                              </p>
                              {!item.isConsistent && (
                                <p className="text-xs text-rose-600 mt-1">
                                  ⚠️ 各院区配置不一致
                                </p>
                              )}
                            </div>
                            <div
                              className="flex-1 grid"
                              style={{ gridTemplateColumns: `repeat(${selectedBranches.length}, 1fr)` }}
                            >
                              {item.branches.map((branchStatus) => (
                                <div
                                  key={branchStatus.branchId}
                                  className="p-3 border-r last:border-r-0 text-xs space-y-1"
                                >
                                  {branchStatus.config && (
                                    <div className="text-muted-foreground">
                                      {Object.entries(branchStatus.config).map(([key, value]) => (
                                        <div key={key}>
                                          {key}: {JSON.stringify(value)}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Summary Stats */}
        {comparisonView.length > 0 && (
          <div className="grid grid-cols-4 gap-3">
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold">{comparisonView.length}</div>
              <div className="text-xs text-muted-foreground">总功能数</div>
            </div>
            <div className="p-3 bg-emerald-50 rounded-lg text-center">
              <div className="text-2xl font-bold text-emerald-600">
                {comparisonView.filter((i) => i.isConsistent).length}
              </div>
              <div className="text-xs text-emerald-700">一致功能</div>
            </div>
            <div className="p-3 bg-rose-50 rounded-lg text-center">
              <div className="text-2xl font-bold text-rose-600">
                {comparisonView.filter((i) => !i.isConsistent).length}
              </div>
              <div className="text-xs text-rose-700">差异功能</div>
            </div>
            <div className="p-3 bg-sky-50 rounded-lg text-center">
              <div className="text-2xl font-bold text-sky-600">
                {comparisonView.filter((i) => i.category === 'custom').length}
              </div>
              <div className="text-xs text-sky-700">分院特性</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
