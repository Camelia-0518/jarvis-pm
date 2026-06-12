"use client";

import Link from "next/link";

interface AnnotationTaskStats {
  open: number;
  resolved: number;
  dismissed: number;
  total: number;
}

interface TaskStats {
  todo: number;
  in_progress: number;
  done: number;
  cancelled: number;
  total: number;
}

interface Task {
  id: string;
  status: string;
  re_review_status: string | null;
}

interface Props {
  /** Current recommendation context */
  hasUnfinishedChecklist: boolean;
  openAnnotations: number;
  activeTaskCount: number;
  hasFailedReReview: boolean;
  prdStatus: string;
  projectId: string | null;
  /** Callbacks */
  onScrollToReview: () => void;
  onOpenAnnotations: () => void;
  onOpenTasks: () => void;
}

interface Step {
  key: string;
  title: string;
  description: string;
  variant: "action" | "warning" | "info" | "success";
  action?: { label: string; onClick?: () => void; href?: string };
}

function computeStep(props: Props): Step {
  const {
    hasUnfinishedChecklist,
    openAnnotations,
    activeTaskCount,
    hasFailedReReview,
    prdStatus,
    projectId,
    onScrollToReview,
    onOpenAnnotations,
    onOpenTasks,
  } = props;

  // 1. Unfinished checklist
  if (hasUnfinishedChecklist) {
    return {
      key: "review",
      title: "先完成评审",
      description: "还有必选项未通过，完成评审后才能继续推进。",
      variant: "warning",
      action: { label: "打开评审", onClick: onScrollToReview },
    };
  }

  // 2. Open annotations
  if (openAnnotations > 0) {
    return {
      key: "annotations",
      title: `先处理 ${openAnnotations} 条批注`,
      description: "有未处理的评审批注，处理后可以进入修订阶段。",
      variant: "action",
      action: { label: "打开批注", onClick: onOpenAnnotations },
    };
  }

  // 3. Todo/in-progress revision tasks
  if (activeTaskCount > 0) {
    return {
      key: "tasks",
      title: `继续修订任务（${activeTaskCount} 个待完成）`,
      description: "修订任务正在进行中，完成后可发起复审。",
      variant: "action",
      action: { label: "打开修订任务", onClick: onOpenTasks },
    };
  }

  // 4. Failed re-review after completed tasks
  if (hasFailedReReview) {
    return {
      key: "rereview",
      title: "查看复审结果",
      description: "有复审未通过的任务，需要重新修订。",
      variant: "warning",
      action: { label: "查看任务", onClick: onOpenTasks },
    };
  }

  // 5. Status stable (published/approved) → suggest delivery
  const stableStatuses = ["published", "approved", "implemented"];
  if (prdStatus && stableStatuses.includes(prdStatus)) {
    return {
      key: "delivery",
      title: "进入交付规划",
      description: "PRD 内容已稳定，可以开始制定交付计划。",
      variant: "info",
      action: {
        label: "去交付中心",
        href: projectId ? `/delivery?project_id=${projectId}` : "/delivery",
      },
    };
  }

  // 6. All done
  return {
    key: "done",
    title: "当前文档状态良好",
    description: "评审、批注、修订均已完成。",
    variant: "success",
  };
}

export default function NextStepCard(props: Props) {
  const step = computeStep(props);

  const colorClasses = {
    action: "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20",
    warning: "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20",
    info: "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20",
    success: "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20",
  };

  const dotColors = {
    action: "text-blue-600",
    warning: "text-amber-600",
    info: "text-emerald-600",
    success: "text-green-600",
  };

  return (
    <div className={`rounded-xl border p-4 ${colorClasses[step.variant]}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 text-lg ${dotColors[step.variant]}`}>
          {step.variant === "warning" ? "⚠" : step.variant === "action" ? "→" : step.variant === "info" ? "✦" : "✓"}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            {step.title}
          </p>
          <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-400">
            {step.description}
          </p>
          {step.action && (
            <div className="mt-2">
              {step.action.href ? (
                <Link
                  href={step.action.href}
                  className={`inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    step.variant === "warning"
                      ? "bg-amber-600 text-white hover:bg-amber-700"
                      : step.variant === "info"
                        ? "bg-emerald-600 text-white hover:bg-emerald-700"
                        : "bg-blue-600 text-white hover:bg-blue-700"
                  }`}
                >
                  {step.action.label}
                </Link>
              ) : (
                <button
                  onClick={step.action.onClick}
                  className={`inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    step.variant === "warning"
                      ? "bg-amber-600 text-white hover:bg-amber-700"
                      : step.variant === "info"
                        ? "bg-emerald-600 text-white hover:bg-emerald-700"
                        : "bg-blue-600 text-white hover:bg-blue-700"
                  }`}
                >
                  {step.action.label}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
