"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface DonutSegment {
  value: number;
  color: string;
}

interface Props {
  segments: DonutSegment[];
  /** 0-1 completion ratio — draws a semi-circle gauge instead of donut when set */
  completion?: number;
  /** Total count or percentage string shown in center */
  centerLabel?: string;
  centerSub?: string;
  size?: number; // px, default 72
}

/**
 * 迷你 ECharts 图表 — 支持 donut 环形图和 semi-circle 进度表
 *
 * 用于统计卡片内嵌展示，自动适配 dark mode。
 * - 传入 segments 显示环形分布图（如风险比例）
 * - 传入 completion 显示半圆进度（如完成率）
 */
export default function SparkDonut({
  segments,
  completion,
  centerLabel,
  centerSub,
  size = 72,
}: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const el = chartRef.current;
    const isDark = document.documentElement.classList.contains("dark");
    const chart = echarts.init(el, isDark ? "dark" : undefined, { renderer: "canvas" });
    instanceRef.current = chart;

    const textColor = isDark ? "#94a3b8" : "#64748b";
    const titleColor = isDark ? "#e2e8f0" : "#1e293b";

    if (completion !== undefined) {
      // Semi-circle gauge mode
      chart.setOption({
        backgroundColor: "transparent",
        series: [
          {
            type: "pie",
            radius: ["65%", "85%"],
            center: ["50%", "70%"],
            startAngle: 180,
            endAngle: 0,
            silent: true,
            label: { show: false },
            emphasis: { disabled: true },
            data: [
              { value: completion * 100, itemStyle: { color: segments[0]?.color ?? "#22c55e" } },
              { value: 100 - completion * 100, itemStyle: { color: isDark ? "#1e293b" : "#f1f5f9" } },
            ],
          },
        ],
        graphic: [
          {
            type: "text",
            left: "center",
            top: "52%",
            style: {
              text: centerLabel ?? `${Math.round(completion * 100)}%`,
              textAlign: "center",
              fontSize: 14,
              fontWeight: "bold",
              fill: titleColor,
            },
          },
          centerSub
            ? {
                type: "text",
                left: "center",
                top: "68%",
                style: {
                  text: centerSub,
                  textAlign: "center",
                  fontSize: 9,
                  fill: textColor,
                },
              }
            : { type: "text", left: "-9999", top: "-9999", style: { text: "" } },
        ],
      });
    } else {
      // Donut mode
      chart.setOption({
        backgroundColor: "transparent",
        series: [
          {
            type: "pie",
            radius: ["58%", "82%"],
            center: ["50%", "50%"],
            silent: true,
            label: { show: false },
            emphasis: { disabled: true },
            data: segments.map((s) => ({
              value: s.value,
              itemStyle: { color: s.color, borderRadius: 2 },
            })),
          },
        ],
        graphic: [
          {
            type: "text",
            left: "center",
            top: "center",
            style: {
              text: centerLabel ?? "",
              textAlign: "center",
              fontSize: 13,
              fontWeight: "bold",
              fill: titleColor,
            },
          },
          centerSub
            ? {
                type: "text",
                left: "center",
                top: "62%",
                style: {
                  text: centerSub,
                  textAlign: "center",
                  fontSize: 9,
                  fill: textColor,
                },
              }
            : { type: "text", left: "-9999", top: "-9999", style: { text: "" } },
        ],
      });
    }

    chart.resize();

    return () => {
      chart.dispose();
      instanceRef.current = null;
    };
  }, [segments, completion, centerLabel, centerSub]);

  // Dark mode
  useEffect(() => {
    const observer = new MutationObserver(() => {
      instanceRef.current?.dispose();
      if (chartRef.current) {
        const isDark = document.documentElement.classList.contains("dark");
        const chart = echarts.init(chartRef.current, isDark ? "dark" : undefined, {
          renderer: "canvas",
        });
        instanceRef.current = chart;
        // Re-run the same logic by triggering main effect... simplest: re-read from DOM
        // We just re-create — the main effect deps won't change so we re-apply inline
        const textColor = isDark ? "#94a3b8" : "#64748b";
        const titleColor = isDark ? "#e2e8f0" : "#1e293b";

        if (completion !== undefined) {
          chart.setOption({
            backgroundColor: "transparent",
            series: [
              {
                type: "pie",
                radius: ["65%", "85%"],
                center: ["50%", "70%"],
                startAngle: 180,
                endAngle: 0,
                silent: true,
                label: { show: false },
                emphasis: { disabled: true },
                data: [
                  {
                    value: completion * 100,
                    itemStyle: { color: segments[0]?.color ?? "#22c55e" },
                  },
                  {
                    value: 100 - completion * 100,
                    itemStyle: { color: isDark ? "#1e293b" : "#f1f5f9" },
                  },
                ],
              },
            ],
            graphic: [
              {
                type: "text",
                left: "center",
                top: "52%",
                style: {
                  text: centerLabel ?? `${Math.round(completion * 100)}%`,
                  textAlign: "center",
                  fontSize: 14,
                  fontWeight: "bold",
                  fill: titleColor,
                },
              },
              centerSub
                ? {
                    type: "text",
                    left: "center",
                    top: "68%",
                    style: {
                      text: centerSub,
                      textAlign: "center",
                      fontSize: 9,
                      fill: textColor,
                    },
                  }
                : { type: "text", left: "-9999", top: "-9999", style: { text: "" } },
            ],
          });
        } else {
          chart.setOption({
            backgroundColor: "transparent",
            series: [
              {
                type: "pie",
                radius: ["58%", "82%"],
                center: ["50%", "50%"],
                silent: true,
                label: { show: false },
                emphasis: { disabled: true },
                data: segments.map((s) => ({
                  value: s.value,
                  itemStyle: { color: s.color, borderRadius: 2 },
                })),
              },
            ],
            graphic: [
              {
                type: "text",
                left: "center",
                top: "center",
                style: {
                  text: centerLabel ?? "",
                  textAlign: "center",
                  fontSize: 13,
                  fontWeight: "bold",
                  fill: titleColor,
                },
              },
              centerSub
                ? {
                    type: "text",
                    left: "center",
                    top: "62%",
                    style: {
                      text: centerSub,
                      textAlign: "center",
                      fontSize: 9,
                      fill: textColor,
                    },
                  }
                : { type: "text", left: "-9999", top: "-9999", style: { text: "" } },
            ],
          });
        }
        chart.resize();
      }
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      ref={chartRef}
      style={{ width: size, height: size, flexShrink: 0 }}
    />
  );
}
