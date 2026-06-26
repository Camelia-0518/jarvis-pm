"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface TrendData {
  date: string;
  completed: number;
  total: number;
}

interface Props {
  data: TrendData[];
}

function buildTrendOption(data: TrendData[], isDark: boolean): echarts.EChartsOption {
  const dates = data.map((d) => d.date);
  const completed = data.map((d) => d.completed);
  const total = data.map((d) => d.total);

  const completedArea = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "rgba(34, 197, 94, 0.25)" },
    { offset: 1, color: "rgba(34, 197, 94, 0.01)" },
  ]);

  const totalArea = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: "rgba(148, 163, 184, 0.15)" },
    { offset: 1, color: "rgba(148, 163, 184, 0.01)" },
  ]);

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: isDark ? "#1e293b" : "#fff",
      borderColor: isDark ? "#475569" : "#e2e8f0",
      textStyle: { color: isDark ? "#e2e8f0" : "#1e293b" },
      formatter: (params: any) => {
        const date = params[0]?.axisValue;
        const comp = params.find((p: any) => p.seriesName === "已完成")?.value || 0;
        const tot = params.find((p: any) => p.seriesName === "总任务")?.value || 0;
        return `<div style="font-weight:600;font-size:13px;margin-bottom:4px">${date}</div>
                <div style="font-size:12px">已完成：<b style="color:#22c55e">${comp}</b></div>
                <div style="font-size:12px">总任务：<b>${tot}</b></div>`;
      },
    },
    legend: {
      data: ["已完成", "总任务"],
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 20,
      textStyle: { color: isDark ? "#94a3b8" : "#64748b", fontSize: 12 },
    },
    grid: { top: "10%", left: "3%", right: "4%", bottom: "14%", containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: dates,
      axisLine: { lineStyle: { color: isDark ? "#334155" : "#e2e8f0" } },
      axisLabel: { color: isDark ? "#94a3b8" : "#64748b", fontSize: 12 },
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
        name: "已完成",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 8,
        data: completed,
        lineStyle: {
          color: "#22c55e",
          width: 3,
          shadowColor: "rgba(34, 197, 94, 0.3)",
          shadowBlur: 10,
          shadowOffsetY: 4,
        },
        itemStyle: {
          color: "#22c55e",
          borderColor: "#fff",
          borderWidth: 2,
        },
        areaStyle: {
          color: completedArea,
        },
        emphasis: {
          itemStyle: {
            borderColor: "#22c55e",
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: "rgba(34, 197, 94, 0.4)",
          },
        },
      },
      {
        name: "总任务",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        data: total,
        lineStyle: {
          color: isDark ? "#475569" : "#94a3b8",
          width: 2,
          type: "dashed",
        },
        itemStyle: {
          color: isDark ? "#475569" : "#94a3b8",
          borderColor: "#fff",
          borderWidth: 2,
        },
        areaStyle: {
          color: totalArea,
        },
      },
    ],
    animationEasing: "cubicOut",
    animationDuration: 1000,
  };
}

/**
 * 任务趋势折线图 — 面积渐变 + 平滑曲线 + 发光阴影
 *
 * 展示近 N 天任务完成趋势，使用：
 * 1. 平滑曲线（smooth: true）
 * 2. 面积渐变（areaStyle + LinearGradient）
 * 3. 数据点发光阴影（emphasis itemStyle）
 * 4. 总任务虚线对比
 */
export default function TaskTrendLine({ data }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    if (!chartRef.current) return;
    const isDark = document.documentElement.classList.contains("dark");
    const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instanceRef.current = chart;
    chart.setOption(buildTrendOption(data, isDark));

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
        chart.setOption(buildTrendOption(dataRef.current, isDark));
        chart.resize();
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return <div ref={chartRef} className="w-full h-72" />;
}
