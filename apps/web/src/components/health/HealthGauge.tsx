"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface Props {
  score: number; // 0-100
  title: string;
  color: string;
}

function buildGaugeOption(
  score: number,
  title: string,
  color: string,
  isDark: boolean,
): echarts.EChartsOption {
  const bgColor = isDark ? "#1e293b" : "#f8fafc";
  const textColor = isDark ? "#e2e8f0" : "#1e293b";
  const subTextColor = isDark ? "#94a3b8" : "#64748b";

  return {
    backgroundColor: "transparent",
    series: [
      {
        // 外圈装饰环
        type: "gauge",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        radius: "95%",
        center: ["50%", "55%"],
        axisLine: {
          lineStyle: {
            width: 2,
            color: [[1, isDark ? "#334155" : "#e2e8f0"]],
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        detail: { show: false },
      },
      {
        // 主仪表盘
        type: "gauge",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        radius: "85%",
        center: ["50%", "55%"],
        splitNumber: 5,
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: 22,
            color: [
              [0.3, new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: "#22c55e" },
                { offset: 1, color: "#4ade80" },
              ])] as any,
              [0.6, new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: "#eab308" },
                { offset: 1, color: "#facc15" },
              ])] as any,
              [1, new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: "#f87171" },
                { offset: 1, color: "#ef4444" },
              ])] as any,
            ] as any,
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "60%",
          width: 12,
          offsetCenter: [0, "-8%"],
          itemStyle: {
            color: color,
            shadowColor: color + "80",
            shadowBlur: 12,
            shadowOffsetY: 2,
          },
        },
        axisTick: {
          distance: -28,
          length: 6,
          lineStyle: { color: isDark ? "#475569" : "#fff", width: 1 },
        },
        splitLine: {
          distance: -32,
          length: 12,
          lineStyle: { color: isDark ? "#475569" : "#fff", width: 2 },
        },
        axisLabel: {
          distance: -8,
          color: subTextColor,
          fontSize: 10,
          formatter: "{value}",
        },
        detail: {
          valueAnimation: true,
          formatter: "{value}",
          color: textColor,
          fontSize: 32,
          fontWeight: "bold",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
          offsetCenter: [0, "35%"],
          rich: {
            unit: {
              fontSize: 14,
              color: subTextColor,
              fontWeight: "normal",
              padding: [0, 0, 0, 4],
            },
          },
        },
        title: {
          offsetCenter: [0, "72%"],
          fontSize: 13,
          color: subTextColor,
          fontWeight: 500,
        },
        data: [{ value: score, name: title }],
      },
      {
        // 内圈背景
        type: "gauge",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        radius: "55%",
        center: ["50%", "55%"],
        axisLine: {
          lineStyle: {
            width: 60,
            color: [[1, bgColor]],
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        detail: { show: false },
      },
    ],
  };
}

/**
 * 项目健康度仪表盘 — 美化版 Gauge
 *
 * 特性：
 * 1. 渐变色轴（绿→黄→红），roundCap 圆角端点
 * 2. 指针发光阴影（shadowBlur）
 * 3. 内圈背景环增加层次感
 * 4. 外圈装饰细线
 * 5. Dark mode 自适应
 * 6. 数字跳动动画（valueAnimation）
 */
export default function HealthGauge({ score, title, color }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const propsRef = useRef({ score, title, color });
  propsRef.current = { score, title, color };

  useEffect(() => {
    if (!chartRef.current) return;
    const el = chartRef.current;
    const isDark = document.documentElement.classList.contains("dark");

    const chart = echarts.init(el, undefined, { renderer: "canvas" });
    instanceRef.current = chart;
    chart.setOption(buildGaugeOption(score, title, color, isDark));

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
      instanceRef.current = null;
    };
  }, [score, title, color]);

  // Dark mode toggle
  useEffect(() => {
    const observer = new MutationObserver(() => {
      const isDark = document.documentElement.classList.contains("dark");
      instanceRef.current?.dispose();
      if (chartRef.current) {
        const { score: s, title: t, color: c } = propsRef.current;
        const chart = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
        instanceRef.current = chart;
        chart.setOption(buildGaugeOption(s, t, c, isDark));
        chart.resize();
      }
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return <div ref={chartRef} className="w-full h-56" />;
}
