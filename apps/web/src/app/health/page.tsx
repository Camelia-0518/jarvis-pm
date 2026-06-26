"use client";

import { useEffect, useState, useRef } from "react";
import { deliveryApi, type DeliveryDashboardData } from "@/lib/api";
import NavHeader from "@/components/global/NavHeader";
import {
  HealthGauge,
  RiskHeatmap,
  TaskBarChart,
  TaskTrendLine,
  TaskStatusPie,
} from "@/components/health";
import {
  Activity,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  BarChart3,
  Heart,
  AlertTriangle,
  CheckCircle2,
  Zap,
  Clock,
} from "lucide-react";
import { toast } from "sonner";

// ============================================================
// Animated counter
// ============================================================
function useCountUp(target: number, duration = 900) {
  const [value, setValue] = useState(0);
  const raf = useRef<number | undefined>();

  useEffect(() => {
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(target * eased));
      if (t < 1) raf.current = requestAnimationFrame(animate);
    };
    raf.current = requestAnimationFrame(animate);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [target, duration]);

  return value;
}

function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const animated = useCountUp(value);
  return (
    <span>
      {animated}
      {suffix}
    </span>
  );
}


// ============================================================
// Helpers
// ============================================================
type HealthLevel = "green" | "yellow" | "red";

function healthScore(health: string): number {
  return health === "green" ? 92 : health === "yellow" ? 68 : 35;
}

function healthColor(health: string): string {
  return health === "green" ? "#22c55e" : health === "yellow" ? "#eab308" : "#ef4444";
}

const HEALTH_META: Record<
  HealthLevel,
  { label: string; icon: typeof CheckCircle2; gradient: string; border: string; text: string }
> = {
  green: {
    label: "项目健康",
    icon: CheckCircle2,
    gradient: "from-emerald-500/15 via-emerald-500/5 to-transparent",
    border: "border-emerald-500/20",
    text: "text-emerald-700 dark:text-emerald-400",
  },
  yellow: {
    label: "需要关注",
    icon: AlertTriangle,
    gradient: "from-amber-500/15 via-amber-500/5 to-transparent",
    border: "border-amber-500/20",
    text: "text-amber-700 dark:text-amber-400",
  },
  red: {
    label: "存在风险",
    icon: AlertTriangle,
    gradient: "from-red-500/15 via-red-500/5 to-transparent",
    border: "border-red-500/20",
    text: "text-red-700 dark:text-red-400",
  },
};

// ============================================================
// KPI Card
// ============================================================
function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  loading,
}: {
  label: string;
  value: number;
  sub: string;
  icon: typeof Activity;
  accent: string;
  loading: boolean;
}) {
  const bgMap: Record<string, string> = {
    sky: "bg-sky-50 text-sky-600 dark:bg-sky-950 dark:text-sky-400",
    emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400",
    rose: "bg-rose-50 text-rose-600 dark:bg-rose-950 dark:text-rose-400",
    purple: "bg-purple-50 text-purple-600 dark:bg-purple-950 dark:text-purple-400",
  };
  const barMap: Record<string, string> = {
    sky: "bg-sky-500",
    emerald: "bg-emerald-500",
    rose: "bg-rose-500",
    purple: "bg-purple-500",
  };

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
      <div className={`absolute top-0 left-0 h-1 w-full rounded-t-2xl ${barMap[accent]}`} />
      <div className="flex items-start justify-between">
        <div className={`rounded-xl p-2.5 ${bgMap[accent]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="text-right">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {label}
          </p>
          <p className="mt-1 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {loading ? (
              <span className="inline-block h-7 w-12 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
            ) : (
              <AnimatedNumber value={value} />
            )}
          </p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500">{sub}</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Page
// ============================================================
export default function HealthDashboard() {
  const [dashboard, setDashboard] = useState<DeliveryDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await deliveryApi.getDashboard();
      setDashboard(data);
    } catch {
      toast.error("加载仪表盘数据失败");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const deliveryScore = dashboard ? healthScore(dashboard.delivery_health) : 0;
  const riskScore = dashboard ? healthScore(dashboard.risk_health) : 0;
  const deliveryColor = dashboard ? healthColor(dashboard.delivery_health) : "#94a3b8";
  const riskColor = dashboard ? healthColor(dashboard.risk_health) : "#94a3b8";

  const worstHealth: HealthLevel =
    !dashboard
      ? "green"
      : dashboard.delivery_health === "red" || dashboard.risk_health === "red"
        ? "red"
        : dashboard.delivery_health === "yellow" || dashboard.risk_health === "yellow"
          ? "yellow"
          : "green";

  const meta = HEALTH_META[worstHealth];
  const StatusIcon = meta.icon;

  const statusPieData = dashboard
    ? [
        { name: "已完成", value: dashboard.completed_tasks, color: "#22c55e" },
        { name: "进行中", value: dashboard.in_progress_tasks, color: "#3b82f6" },
        { name: "待开始", value: Math.max(0, dashboard.total_tasks - dashboard.completed_tasks - dashboard.in_progress_tasks), color: "#94a3b8" },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavHeader>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm transition-all hover:border-slate-300 hover:text-slate-900 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-slate-600 dark:hover:text-slate-100"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">刷新</span>
        </button>
      </NavHeader>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* ========== Health Summary Banner ========== */}
        <div
          className={`relative overflow-hidden rounded-2xl border bg-gradient-to-br ${meta.gradient} p-6 sm:p-8 ${meta.border}`}
        >
          <div className="pointer-events-none absolute -right-6 -top-6 h-32 w-32 rounded-full bg-white/5 blur-2xl" />
          <div className="pointer-events-none absolute -bottom-4 -left-4 h-24 w-24 rounded-full bg-white/5 blur-xl" />

          <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div
                className={`flex h-14 w-14 items-center justify-center rounded-2xl shadow-inner ${
                  worstHealth === "green"
                    ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                    : worstHealth === "yellow"
                      ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                      : "bg-red-500/20 text-red-600 dark:text-red-400"
                }`}
              >
                <StatusIcon className="h-7 w-7" />
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  项目健康度总览
                </p>
                <h2 className={`text-2xl font-bold ${meta.text}`}>{meta.label}</h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {worstHealth === "green"
                    ? "交付进度与风险指标均在安全范围内"
                    : worstHealth === "yellow"
                      ? "部分指标偏离预期，建议关注并制定应对计划"
                      : "关键指标严重偏离，需立即采取纠正措施"}
                </p>
              </div>
            </div>

            <div className="flex gap-8 sm:gap-10">
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-200">
                  {loading ? "—" : <AnimatedNumber value={deliveryScore} />}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">交付评分</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-200">
                  {loading ? "—" : <AnimatedNumber value={riskScore} />}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">风险评分</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-200">
                  {loading ? "—" : dashboard?.total_plans ?? "—"}
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">交付计划</p>
              </div>
            </div>
          </div>
        </div>

        {/* ========== KPI Cards ========== */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="交付计划"
            value={dashboard?.total_plans ?? 0}
            sub={`${dashboard?.completed ?? 0} 完成 · ${dashboard?.in_progress ?? 0} 进行中`}
            icon={Activity}
            accent="sky"
            loading={loading}
          />
          <KpiCard
            label="任务完成率"
            value={dashboard?.task_completion_rate ? Math.round(dashboard.task_completion_rate * 100) : 0}
            sub={`${dashboard?.completed_tasks ?? 0}/${dashboard?.total_tasks ?? 0} 任务`}
            icon={TrendingUp}
            accent="emerald"
            loading={loading}
          />
          <KpiCard
            label="高风险项"
            value={dashboard?.high_risks ?? 0}
            sub={`共 ${dashboard?.total_risks ?? 0} 项风险`}
            icon={ShieldAlert}
            accent="rose"
            loading={loading}
          />
          <KpiCard
            label="逾期阶段"
            value={dashboard?.overdue_phases ?? 0}
            sub={dashboard?.overdue_phases ? "需立即关注" : "暂无逾期"}
            icon={Clock}
            accent="purple"
            loading={loading}
          />
        </div>

        {/* ========== Gauge Row ========== */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-3 mb-1">
              <Heart className="h-5 w-5 text-rose-500" />
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">交付健康度</h3>
              <span
                className={`ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                  dashboard?.delivery_health === "green"
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                    : dashboard?.delivery_health === "yellow"
                      ? "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                      : "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400"
                }`}
              >
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    dashboard?.delivery_health === "green"
                      ? "bg-emerald-500"
                      : dashboard?.delivery_health === "yellow"
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                />
                {dashboard?.delivery_health === "green"
                  ? "健康"
                  : dashboard?.delivery_health === "yellow"
                    ? "需关注"
                    : "有风险"}
              </span>
            </div>
            <HealthGauge score={deliveryScore} title="综合评分" color={deliveryColor} />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-3 mb-1">
              <ShieldAlert className="h-5 w-5 text-amber-500" />
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">风险健康度</h3>
              <span
                className={`ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                  dashboard?.risk_health === "green"
                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                    : dashboard?.risk_health === "yellow"
                      ? "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                      : "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400"
                }`}
              >
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    dashboard?.risk_health === "green"
                      ? "bg-emerald-500"
                      : dashboard?.risk_health === "yellow"
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                />
                {dashboard?.risk_health === "green"
                  ? "安全"
                  : dashboard?.risk_health === "yellow"
                    ? "需关注"
                    : "危险"}
              </span>
            </div>
            <HealthGauge score={riskScore} title="风险评分" color={riskColor} />
          </div>
        </div>

        {/* ========== Trend + Pie Row ========== */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-4">
              <div className="rounded-lg bg-blue-50 p-1.5 dark:bg-blue-500/10">
                <Zap className="h-4 w-4 text-blue-500" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  近7天任务趋势
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  已完成 vs 总任务 — 平滑曲线面积图
                </p>
              </div>
            </div>
            <TaskTrendLine data={dashboard?.task_trend ?? []} />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center gap-2 mb-4">
              <div className="rounded-lg bg-emerald-50 p-1.5 dark:bg-emerald-500/10">
                <BarChart3 className="h-4 w-4 text-emerald-500" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  任务状态分布
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  环形图 — 中心显示总任务数
                </p>
              </div>
            </div>
            <TaskStatusPie
              data={
                statusPieData.length > 0
                  ? statusPieData
                  : [
                      { name: "已完成", value: 28, color: "#22c55e" },
                      { name: "进行中", value: 10, color: "#3b82f6" },
                      { name: "待开始", value: 12, color: "#94a3b8" },
                    ]
              }
            />
          </div>
        </div>

        {/* ========== Risk Heatmap ========== */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-rose-50 p-1.5 dark:bg-rose-500/10">
                <AlertTriangle className="h-4 w-4 text-rose-500" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  风险分布矩阵
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  5×5 概率 × 影响热力图 — 颜色越深风险越集中
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-blue-100 dark:bg-blue-900" /> 安全
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-yellow-100 dark:bg-yellow-900" /> 关注
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-red-100 dark:bg-red-900" /> 危险
              </span>
            </div>
          </div>
          <RiskHeatmap data={dashboard?.risk_heatmap ?? []} />
        </div>

        {/* ========== Task Bar Chart ========== */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-sky-50 p-1.5 dark:bg-sky-500/10">
                <BarChart3 className="h-4 w-4 text-sky-500" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  阶段任务进度
                </h3>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  按标准阶段分解，直观暴露瓶颈环节
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-slate-400 dark:bg-slate-600" /> 总任务
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-emerald-500" /> 已完成
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded bg-blue-500" /> 进行中
              </span>
            </div>
          </div>
          <TaskBarChart data={dashboard?.phase_progress ?? []} />
        </div>

      </main>
    </div>
  );
}
