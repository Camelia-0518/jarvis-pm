"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface PhaseData {
  phase: string;
  total: number;
  completed: number;
  inProgress: number;
}

interface Props {
  data: PhaseData[];
}

function buildBarOption(data: PhaseData[], isDark: boolean): echarts.EChartsOption {
  const avgCompleted =
    data.length > 0
      ? Math.round(data.reduce((sum, d) => sum + d.completed, 0) / data.length)
      : 0;

  const totalGrad = isDark
    ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "#475569" },
        { offset: 1, color: "#334155" },
      ])
    : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "#cbd5e1" },
        { offset: 1, color: "#e2e8f0" },
      ]);

  const completedGrad = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "#34d399" },
    { offset: 1, color: "#22c55e" },
  ]);

  const inProgressGrad = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "#60a5fa" },
    { offset: 1, color: "#3b82f6" },
  ]);

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: isDark ? "#1e293b" : "#fff",
      borderColor: isDark ? "#475569" : "#e2e8f0",
      textStyle: { color: isDark ? "#e2e8f0" : "#1e293b" },
      formatter: (params: any) => {
        const phase = params[0]?.axisValue || "";
        const total = params.find((p: any) => p.seriesName === "总任务")?.value || 0;
        const completed = params.find((p: any) => p.seriesName === "已完成")?.value || 0;
        const inProgress = params.find((p: any) => p.seriesName === "进行中")?.value || 0;
        const rate = total > 0 ? Math.round((completed / total) * 100) : 0;
        const rateColor = rate >= 80 ? "#22c55e" : rate >= 50 ? "#eab308" : "#ef4444";
        return `<div style="font-weight:600;font-size:13px;margin-bottom:6px">${phase}</div>
                <div style="font-size:12px">总任务：${total}</div>
                <div style="font-size:12px">已完成：${completed}</div>
                <div style="font-size:12px">进行中：${inProgress}</div>
                <div style="font-size:12px;margin-top:4px">完成率：<b style="color:${rateColor}">${rate}%</b></div>`;
      },
    },
    legend: {
      data: ["总任务", "已完成", "进行中"],
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 20,
      textStyle: { color: isDark ? "#94a3b8" : "#64748b", fontSize: 12 },
    },
    grid: { top: "10%", left: "3%", right: "4%", bottom: "14%", containLabel: true },
    xAxis: {
      type: "category",
      data: data.map((d) => d.phase),
      axisLabel: {
        color: isDark ? "#94a3b8" : "#64748b",
        fontSize: 12,
        interval: 0,
        rotate: data.length > 6 ? 30 : 0,
      },
      axisLine: { lineStyle: { color: isDark ? "#334155" : "#e2e8f0" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "任务数",
      nameTextStyle: { color: isDark ? "#94a3b8" : "#64748b", fontSize: 12, fontWeight: 500 },
      axisLabel: { color: isDark ? "#94a3b8" : "#64748b" },
      splitLine: { lineStyle: { color: isDark ? "#1e293b" : "#f1f5f9", type: "dashed" } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: "总任务",
        type: "bar",
        data: data.map((d) => d.total),
        barWidth: 16,
        barGap: "30%",
        itemStyle: {
          color: totalGrad,
          borderRadius: [6, 6, 0, 0],
        },
        label: {
          show: true,
          position: "top",
          formatter: (p: any) => `${p.value}`,
          color: isDark ? "#94a3b8" : "#64748b",
          fontSize: 11,
        },
      },
      {
        name: "已完成",
        type: "bar",
        data: data.map((d) => d.completed),
        barWidth: 16,
        itemStyle: {
          color: completedGrad,
          borderRadius: [6, 6, 0, 0],
          shadowColor: "rgba(34, 197, 94, 0.3)",
          shadowBlur: 8,
          shadowOffsetY: 2,
        },
        label: {
          show: true,
          position: "inside",
          formatter: (p: any) => (p.value > 0 ? `${p.value}` : ""),
          color: "#fff",
          fontSize: 11,
          fontWeight: "bold",
        },
        emphasis: {
          itemStyle: {
            shadowColor: "rgba(34, 197, 94, 0.5)",
            shadowBlur: 16,
          },
        },
        markLine: {
          symbol: ["none", "none"],
          data: [
            {
              yAxis: avgCompleted,
              label: {
                formatter: `平均完成 ${avgCompleted} 个`,
                position: "insideEndTop",
                color: isDark ? "#94a3b8" : "#64748b",
                fontSize: 11,
                backgroundColor: isDark ? "#1e293b" : "#fff",
                padding: [4, 8],
                borderRadius: 4,
                borderColor: isDark ? "#475569" : "#e2e8f0",
                borderWidth: 1,
              },
              lineStyle: { type: "dashed", color: isDark ? "#475569" : "#94a3b8", width: 1.5 },
            },
          ],
        },
      },
      {
        name: "进行中",
        type: "bar",
        data: data.map((d) => d.inProgress),
        barWidth: 16,
        itemStyle: {
          color: inProgressGrad,
          borderRadius: [6, 6, 0, 0],
          shadowColor: "rgba(59, 130, 246, 0.3)",
          shadowBlur: 8,
          shadowOffsetY: 2,
        },
        label: {
          show: true,
          position: "inside",
          formatter: (p: any) => (p.value > 0 ? `${p.value}` : ""),
          color: "#fff",
          fontSize: 11,
          fontWeight: "bold",
        },
        emphasis: {
          itemStyle: {
            shadowColor: "rgba(59, 130, 246, 0.5)",
            shadowBlur: 16,
          },
        },
      },
    ],
    animationEasing: "elasticOut",
    animationDelay: (idx: number) => idx * 50,
  };
}

/**
 * 任务进度柱状图 — 美化版
 *
 * 升级点：
 * 1. 线性渐变柱（总任务灰渐变、已完成绿渐变、进行中蓝渐变）
 * 2. 柱顶圆角（borderRadius: 6）
 * 3. 柱体阴影（shadowBlur + shadowColor）
 * 4. hover 时阴影放大
 * 5. 平均线 markLine 带背景框标签
 * 6. 弹性动画（elasticOut）+ 交错延迟
 * 7. Tooltip 带完成率彩色标注
 */
export default function TaskBarChart({ data }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    if (!chartRef.current) return;
    const isDark = document.documentElement.classList.contains("dark");
    const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instanceRef.current = chart;
    chart.setOption(buildBarOption(data, isDark));

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
      instanceRef.current = null;
    };
  }, [data]);

  useEffect(() => {
    const observer = new MutationObserver(() => {
      const isDark = document.documentElement.classList.contains("dark");
      instanceRef.current?.dispose();
      if (chartRef.current) {
        const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
        instanceRef.current = chart;
        chart.setOption(buildBarOption(dataRef.current, isDark));
        chart.resize();
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return <div ref={chartRef} className="w-full h-80" />;
}
