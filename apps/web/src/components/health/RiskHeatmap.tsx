"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface RiskItem {
  probability: number;
  impact: number;
  count: number;
}

interface Props {
  data: RiskItem[];
}

function buildHeatmapOption(
  heatmapData: [number, number, number][],
  maxVal: number,
  isDark: boolean,
): echarts.EChartsOption {
  const labels = ["极低", "低", "中", "高", "极高"];

  return {
    backgroundColor: "transparent",
    tooltip: {
      position: "top",
      backgroundColor: isDark ? "#1e293b" : "#fff",
      borderColor: isDark ? "#475569" : "#e2e8f0",
      textStyle: { color: isDark ? "#e2e8f0" : "#1e293b" },
      formatter: (params: any) => {
        const impact = labels[params.data[0]];
        const prob = labels[4 - params.data[1]]; // reverse because y-axis is reversed
        const count = params.data[2];
        return `<div style="font-weight:600;font-size:13px;margin-bottom:4px">${impact} × ${prob}</div>
                <div style="font-size:12px">风险项：<b style="color:#ef4444">${count}</b> 个</div>`;
      },
    },
    grid: { top: "8%", bottom: "18%", left: "14%", right: "10%" },
    xAxis: {
      type: "category",
      data: labels,
      name: "影响程度",
      nameLocation: "middle",
      nameGap: 32,
      nameTextStyle: {
        color: isDark ? "#94a3b8" : "#64748b",
        fontSize: 12,
        fontWeight: 500,
      },
      axisLabel: {
        color: isDark ? "#94a3b8" : "#64748b",
        fontSize: 12,
      },
      axisLine: { lineStyle: { color: isDark ? "#334155" : "#e2e8f0" } },
      splitArea: {
        show: true,
        areaStyle: {
          color: [isDark ? "#1e293b" : "#fff", isDark ? "#0f172a" : "#f8fafc"],
        },
      },
    },
    yAxis: {
      type: "category",
      data: [...labels].reverse(),
      name: "发生概率",
      nameLocation: "middle",
      nameGap: 48,
      nameTextStyle: {
        color: isDark ? "#94a3b8" : "#64748b",
        fontSize: 12,
        fontWeight: 500,
      },
      axisLabel: {
        color: isDark ? "#94a3b8" : "#64748b",
        fontSize: 12,
      },
      axisLine: { lineStyle: { color: isDark ? "#334155" : "#e2e8f0" } },
      splitArea: {
        show: true,
        areaStyle: {
          color: [isDark ? "#1e293b" : "#fff", isDark ? "#0f172a" : "#f8fafc"],
        },
      },
    },
    visualMap: {
      min: 0,
      max: maxVal,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: "2%",
      itemWidth: 14,
      itemHeight: 140,
      inRange: {
        color: [
          "#eff6ff", // blue-50
          "#bfdbfe", // blue-200
          "#fcd34d", // amber-300
          "#fb923c", // orange-400
          "#ef4444", // red-500
          "#991b1b", // red-800
        ],
      },
      textStyle: {
        color: isDark ? "#94a3b8" : "#64748b",
        fontSize: 11,
      },
      outOfRange: { color: ["#94a3b8"] },
    },
    series: [
      {
        name: "风险分布",
        type: "heatmap",
        data: heatmapData,
        label: {
          show: true,
          formatter: (params: any) => {
            const count = params.data[2];
            return count > 0 ? `{a|${count}}` : "";
          },
          rich: {
            a: {
              fontSize: 13,
              fontWeight: "bold",
              color: "#fff",
              textShadowColor: "rgba(0,0,0,0.3)",
              textShadowBlur: 3,
            },
          },
        },
        itemStyle: {
          borderColor: isDark ? "#1e293b" : "#fff",
          borderWidth: 2,
          borderRadius: 6,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 20,
            shadowColor: "rgba(0,0,0,0.25)",
            borderColor: isDark ? "#60a5fa" : "#3b82f6",
            borderWidth: 3,
          },
          label: {
            show: true,
            fontSize: 16,
            fontWeight: "bold",
          },
        },
      },
    ],
  };
}

/**
 * 风险分布热力图 — 美化版
 *
 * 升级点：
 * 1. 更专业的颜色映射（蓝→黄→橙→红）
 * 2. 单元格大圆角（borderRadius: 6）
 * 3. hover 时放大 + 阴影 + 边框高亮
 * 4. 数据标签带文字阴影，白底更醒目
 * 5. 棋盘格背景交替色增加层次感
 * 6. Tooltip 自定义深色风格
 */
export default function RiskHeatmap({ data }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const heatmapDataRef = useRef<{
    heatmapData: [number, number, number][];
    maxVal: number;
  }>({ heatmapData: [], maxVal: 1 });

  const matrix: number[][] = Array.from({ length: 5 }, () => Array(5).fill(0));
  data.forEach((item) => {
    const y = item.probability - 1;
    const x = item.impact - 1;
    if (y >= 0 && y < 5 && x >= 0 && x < 5) {
      matrix[y][x] += item.count;
    }
  });

  const hd: [number, number, number][] = [];
  for (let y = 0; y < 5; y++) {
    for (let x = 0; x < 5; x++) {
      hd.push([x, 4 - y, matrix[y][x]]); // y-axis reversed for display
    }
  }
  const maxVal = Math.max(...matrix.flat(), 1);
  heatmapDataRef.current = { heatmapData: hd, maxVal };

  useEffect(() => {
    if (!chartRef.current) return;
    const isDark = document.documentElement.classList.contains("dark");
    const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instanceRef.current = chart;
    chart.setOption(buildHeatmapOption(hd, maxVal, isDark));

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
        const { heatmapData, maxVal: mv } = heatmapDataRef.current;
        const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
        instanceRef.current = chart;
        chart.setOption(buildHeatmapOption(heatmapData, mv, isDark));
        chart.resize();
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return <div ref={chartRef} className="w-full h-80" />;
}
