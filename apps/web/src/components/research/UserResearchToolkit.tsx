"use client";

import { useState } from "react";

// 医疗场景用户访谈提纲模板
const INTERVIEW_TEMPLATES = {
  patient: {
    title: "患者访谈提纲",
    icon: "👤",
    questions: [
      { id: "p1", question: "您最近一次去医院是什么时候？做了什么？", purpose: "了解用户行为背景" },
      { id: "p2", question: "在借阅病理切片的过程中，您遇到了什么困难？", purpose: "挖掘痛点" },
      { id: "p3", question: "您通常提前多久规划去医院？", purpose: "了解时间规划习惯" },
      { id: "p4", question: "如果您可以在家完成切片借阅申请，您愿意尝试吗？", purpose: "验证需求强度" },
      { id: "p5", question: "在申请过程中，您最担心什么问题？", purpose: "识别顾虑和障碍" },
    ],
  },
  pathology: {
    title: "病理科访谈提纲",
    icon: "🔬",
    questions: [
      { id: "pa1", question: "目前每天大概有多少切片借阅申请？", purpose: "了解业务量" },
      { id: "pa2", question: "借阅流程中哪个环节最耗时？", purpose: "识别效率瓶颈" },
      { id: "pa3", question: "审核借阅申请时，您主要关注哪些信息？", purpose: "明确审核标准" },
      { id: "pa4", question: "目前流程中容易出现问题的环节是？", purpose: "识别风险点" },
      { id: "pa5", question: "如果系统自动核验部分信息，能节省您多少时间？", purpose: "量化改进价值" },
    ],
  },
  medical: {
    title: "医务科访谈提纲",
    icon: "⚕️",
    questions: [
      { id: "m1", question: "目前切片借阅在合规方面有什么要求？", purpose: "了解合规要求" },
      { id: "m2", question: "历史上有过借阅相关的医疗纠纷吗？", purpose: "识别风险历史" },
      { id: "m3", question: "线上化后，您认为最大的风险点是什么？", purpose: "预判潜在问题" },
      { id: "m4", question: "需要哪些审批环节才能上线？", purpose: "明确流程要求" },
    ],
  },
  finance: {
    title: "财务科访谈提纲",
    icon: "💰",
    questions: [
      { id: "f1", question: "目前切片借阅的收费标准是什么？", purpose: "了解收费现状" },
      { id: "f2", question: "押金管理的流程和要求是？", purpose: "明确财务流程" },
      { id: "f3", question: "线上支付和退款，财务系统需要对接什么？", purpose: "识别系统对接需求" },
    ],
  },
};

// RICE评分计算器
interface RICEScore {
  reach: number; // 影响用户数/月
  impact: number; // 影响程度 3=大 2=中 1=小
  confidence: number; // 信心度 100%=1 80%=0.8
  effort: number; // 人月
}

function calculateRICE(score: RICEScore): number {
  return (score.reach * score.impact * score.confidence) / score.effort;
}

// 痛点量化分析
interface PainPoint {
  id: string;
  description: string;
  frequency: number; // 频率 1-5
  intensity: number; // 强度 1-5
  impact: number; // 影响 1-5
}

function calculatePainScore(pain: Omit<PainPoint, "id">): number {
  return (pain.frequency + pain.intensity + pain.impact) / 3;
}

export default function UserResearchToolkit() {
  const [selectedTemplate, setSelectedTemplate] = useState<string>("patient");
  const [riceScores, setRiceScores] = useState<RICEScore[]>([]);
  const [painPoints, setPainPoints] = useState<PainPoint[]>([
    { id: "1", description: "需要到现场排队申请", frequency: 5, intensity: 4, impact: 4 },
    { id: "2", description: "审核周期长，需要多次往返", frequency: 4, intensity: 5, impact: 5 },
  ]);

  const currentTemplate = INTERVIEW_TEMPLATES[selectedTemplate as keyof typeof INTERVIEW_TEMPLATES];

  return (
    <div className="space-y-6">
      {/* 访谈提纲生成器 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          🎤 用户访谈提纲生成器
        </h3>

        {/* 角色选择 */}
        <div className="mb-4 flex flex-wrap gap-2">
          {Object.entries(INTERVIEW_TEMPLATES).map(([key, template]) => (
            <button
              key={key}
              onClick={() => setSelectedTemplate(key)}
              className={`rounded-full px-3 py-1.5 text-sm ${
                selectedTemplate === key
                  ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-400"
              }`}
            >
              {template.icon} {template.title}
            </button>
          ))}
        </div>

        {/* 问题列表 */}
        <div className="space-y-3">
          {currentTemplate.questions.map((q, index) => (
            <div
              key={q.id}
              className="flex items-start gap-3 rounded-lg bg-slate-50 p-3 dark:bg-slate-700/50"
            >
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-sky-100 text-xs font-medium text-sky-700 dark:bg-sky-900/30">
                {index + 1}
              </span>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {q.question}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  目的: {q.purpose}
                </p>
              </div>
            </div>
          ))}
        </div>

        <button className="mt-4 w-full rounded-lg border border-slate-300 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-400">
          📋 导出访谈提纲
        </button>
      </div>

      {/* 痛点量化分析 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          😣 痛点量化分析
        </h3>

        <div className="space-y-3">
          {painPoints.map((pain) => (
            <div
              key={pain.id}
              className="rounded-lg bg-slate-50 p-3 dark:bg-slate-700/50"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {pain.description}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  calculatePainScore(pain) >= 4
                    ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30"
                    : calculatePainScore(pain) >= 3
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30"
                    : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30"
                }`}>
                  优先级 {calculatePainScore(pain).toFixed(1)}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="text-center">
                  <div className="text-slate-500">频率</div>
                  <div className="font-medium">{pain.frequency}/5</div>
                </div>
                <div className="text-center">
                  <div className="text-slate-500">强度</div>
                  <div className="font-medium">{pain.intensity}/5</div>
                </div>
                <div className="text-center">
                  <div className="text-slate-500">影响</div>
                  <div className="font-medium">{pain.impact}/5</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <button className="mt-3 flex items-center gap-2 text-sm text-sky-600 hover:text-sky-700">
          <span>+</span> 添加痛点
        </button>
      </div>

      {/* RICE评分器 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          📊 RICE 需求优先级评估
        </h3>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label className="mb-1 block text-slate-600">影响用户数/月</label>
              <input
                type="number"
                className="w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700"
                placeholder="例如: 500"
              />
            </div>
            <div>
              <label className="mb-1 block text-slate-600">影响程度 (1-3)</label>
              <select className="w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700">
                <option value={3}>3 - 大 (显著提升)</option>
                <option value={2}>2 - 中 (适度提升)</option>
                <option value={1}>1 - 小 (轻微提升)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-slate-600">信心度 (%)</label>
              <select className="w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700">
                <option value={1}>100% - 有数据支撑</option>
                <option value={0.8}>80% - 有用户反馈</option>
                <option value={0.5}>50% - 假设推测</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-slate-600">工作量 (人月)</label>
              <input
                type="number"
                step="0.5"
                className="w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-600 dark:bg-slate-700"
                placeholder="例如: 2"
              />
            </div>
          </div>

          <div className="rounded-lg bg-sky-50 p-3 text-center dark:bg-sky-900/20">
            <div className="text-sm text-slate-600 dark:text-slate-400">RICE 得分</div>
            <div className="text-2xl font-bold text-sky-600">--</div>
          </div>
        </div>
      </div>

      {/* 用户旅程地图 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-4 font-semibold text-slate-900 dark:text-white">
          🗺️ 用户旅程地图
        </h3>

        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {["发现需求", "了解流程", "准备材料", "现场申请", "等待审核", "领取切片"].map(
            (stage, index) => (
              <div key={stage} className="flex items-center">
                <div className="min-w-[100px] rounded-lg bg-slate-100 p-3 text-center dark:bg-slate-700">
                  <div className="mb-1 text-lg">
                    {index === 0 && "🔍"}
                    {index === 1 && "📋"}
                    {index === 2 && "📄"}
                    {index === 3 && "🏥"}
                    {index === 4 && "⏳"}
                    {index === 5 && "✅"}
                  </div>
                  <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    {stage}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    情绪: {index === 3 || index === 4 ? "😤" : "😐"}
                  </div>
                </div>
                {index < 5 && (
                  <span className="mx-1 text-slate-400">→</span>
                )}
              </div>
            )
          )}
        </div>

        <div className="mt-4 rounded-lg bg-rose-50 p-3 dark:bg-rose-900/20">
          <div className="text-sm font-medium text-rose-800 dark:text-rose-200">
            ⚠️ 关键痛点
          </div>
          <ul className="mt-1 list-inside list-disc text-xs text-rose-700 dark:text-rose-300">
            <li>现场申请: 需请假到医院，排队时间长</li>
            <li>等待审核: 状态不透明，需多次电话询问</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
