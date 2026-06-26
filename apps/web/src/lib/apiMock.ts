import type { DeliveryDashboardData } from './api';

export const MOCK_DASHBOARD_DATA: DeliveryDashboardData = {
  total_plans: 5,
  draft: 1,
  at_risk: 2,
  in_progress: 2,
  completed: 1,
  total_risks: 14,
  high_risks: 3,
  risk_health: 'yellow',
  delivery_health: 'green',
  total_tasks: 50,
  completed_tasks: 28,
  in_progress_tasks: 10,
  task_completion_rate: 0.56,
  total_phases: 8,
  avg_phase_progress: 62,
  overdue_phases: 1,
  health_detail: {
    risk: { score: '68', at_risk_plans: 2, high_risk_ratio: 0.21, avg_risks_per_plan: 2.8 },
    delivery: { score: '92', active_ratio: 0.8, task_completion: 0.56, overdue_phases: 1 },
  },
  risk_heatmap: [],
  phase_progress: [],
  task_trend: [],
};
