"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface StatusData {
  name: string;
  value: number;
  color: string;
}

interface Props {
  data: StatusData[];
}

function buildPieOption(data: StatusData[], isDark: boolean): echarts.EChartsOption {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: isDark ? "#1e293b" : "#fff",
      borderColor: isDark ? "#475569" : "#e2e8f0",
      textStyle: { color: isDark ? "#e2e8f0" : "#1e293b" },
      formatter: (params: any) => {
        const pct = total > 0 ? Math.round((params.value / total) * 100) : 0;
        return `<div style="font-weight:600">${params.name}</div>
                <div style="font-size:12px">${params.value} 项 (${pct}%)</div>`;
      },
    },
    legend: {
      orient: "vertical",
      right: "5%",
      top: "center",
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 16,
      textStyle: { color: isDark ? "#94a3b8" : "#64748b", fontSize: 12 },
      formatter: (name: string) => {
        const item = data.find((d) => d.name === name);
        const pct = total > 0 && item ? Math.round((item.value / total) * 100) : 0;
        return `${name}  ${pct}%`;
      },
    },
    series: [
      {
        name: "任务状态",
        type: "pie",
        radius: ["45%", "70%"],
        center: ["40%", "50%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: isDark ? "#1e293b" : "#fff",
          borderWidth: 3,
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: "bold",
            color: isDark ? "#e2e8f0" : "#1e293b",
            formatter: "{b}\n{d}%",
          },
          itemStyle: {
            shadowBlur: 20,
            shadowOffsetX: 0,
            shadowColor: "rgba(0, 0, 0, 0.2)",
          },
          scale: true,
          scaleSize: 10,
        },
        labelLine: { show: false },
        data: data.map((d) => ({
          value: d.value,
          name: d.name,
          itemStyle: { color: d.color },
        })),
      },
      {
        // 中心文字
        type: "pie",
        radius: ["0%", "35%"],
        center: ["40%", "50%"],
        silent: true,
        label: {
          show: true,
          position: "center",
          formatter: `{total|${total}}\n{label|总任务}`,
          rich: {
            total: {
              fontSize: 28,
              fontWeight: "bold",
              color: isDark ? "#e2e8f0" : "#1e293b",
              lineHeight: 36,
            },
            label: {
              fontSize: 12,
              color: isDark ? "#94a3b8" : "#64748b",
            },
          },
        },
        data: [{ value: 1, name: "" }],
        itemStyle: { color: "transparent" },
      },
    ],
    animationType: "scale",
    animationEasing: "elasticOut",
    animationDelay: () => Math.random() * 200,
  };
}

/**
 * 任务状态环形饼图 — 带中心文字 + 交互放大
 *
 * 特性：
 * 1. 环形图（radius: ["45%", "70%"]）
 * 2. 中心显示总任务数
 * 3. hover 时扇区放大 + 显示百分比
 * 4. 圆角扇区（borderRadius: 8）
 * 5. 弹性动画（elasticOut）+ 随机交错延迟
 */
export default function TaskStatusPie({ data }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    if (!chartRef.current) return;
    const isDark = document.documentElement.classList.contains("dark");
    const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instanceRef.current = chart;
    chart.setOption(buildPieOption(data, isDark));

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
        chart.setOption(buildPieOption(dataRef.current, isDark));
        chart.resize();
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return <div ref={chartRef} className="w-full h-72" />;
}
