'use client'

import { cn } from '@/lib/utils'

interface AgentProgressBarProps {
  progress: number
  steps: string[]
  currentStep: number
  status: 'idle' | 'running' | 'completed' | 'error'
}

export function AgentProgressBar({
  progress,
  steps,
  currentStep,
  status
}: AgentProgressBarProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'bg-sky-500'
      case 'completed':
        return 'bg-emerald-500'
      case 'error':
        return 'bg-rose-500'
      default:
        return 'bg-gray-300'
    }
  }

  return (
    <div className="w-full space-y-2">
      {/* 进度条 */}
      <div className="relative h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={cn(
            'absolute left-0 top-0 h-full transition-all duration-500',
            getStatusColor()
          )}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 步骤指示器 */}
      <div className="flex justify-between">
        {steps.map((step, idx) => (
          <div key={idx} className="flex flex-col items-center">
            <div
              className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors',
                idx < currentStep
                  ? 'bg-emerald-500 text-white'
                  : idx === currentStep
                  ? status === 'error'
                    ? 'bg-rose-500 text-white animate-pulse'
                    : 'bg-sky-500 text-white animate-pulse'
                  : 'bg-gray-200 text-gray-500'
              )}
            >
              {idx < currentStep ? (
                '✓'
              ) : idx === currentStep ? (
                idx + 1
              ) : (
                idx + 1
              )}
            </div>
            <span
              className={cn(
                'text-xs mt-1 max-w-20 text-center',
                idx <= currentStep ? 'text-foreground' : 'text-muted-foreground'
              )}
            >
              {step}
            </span>
          </div>
        ))}
      </div>

      {/* 当前步骤说明 */}
      {status === 'running' && currentStep < steps.length && (
        <p className="text-sm text-muted-foreground text-center animate-pulse">
          正在执行: {steps[currentStep]}...
        </p>
      )}
    </div>
  )
}
