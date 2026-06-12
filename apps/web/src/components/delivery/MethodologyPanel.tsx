"use client";

import { useState, useEffect } from "react";
import { methodologyApi, retrospectiveApi, type MethodologyTemplate, type RetroLessons } from "@/lib/api";
import { devError } from "@/utils/logger";
import { toast } from "sonner";

const STAGE_GATE_SEED = {
  name: "医疗信息化交付方法论",
  description: "基于 Stage-Gate 模型的医疗数字化项目标准化交付路径，覆盖从立项到运营的全生命周期。适配 HIS/EMR/互联互通平台等项目类型。",
  industry: "medical",
  stages: [
    {
      name: "Gate 0: 项目立项",
      description: "完成需求调研与可行性分析，输出 PRD 文档并通过评审",
      entry_criteria: ["客户意向确认", "初步需求调研完成", "商务合同签署"],
      exit_criteria: ["PRD 通过评审", "项目章程签署", "资源预算获批"],
      deliverables: ["PRD 文档", "项目章程", "资源计划", "风险评估报告"],
      duration_days: 10,
    },
    {
      name: "Gate 1: 方案设计",
      description: "完成技术方案与 UI/UX 设计，输出详细设计文档并通过设计评审",
      entry_criteria: ["Gate 0 评审通过", "核心干系人确认"],
      exit_criteria: ["技术方案评审通过", "UI 评审通过", "数据迁移方案确认"],
      deliverables: ["技术方案文档", "UI 设计稿", "接口规范", "数据迁移方案"],
      duration_days: 15,
    },
    {
      name: "Gate 2: 开发实施",
      description: "核心功能开发与单元测试，持续集成与代码审查",
      entry_criteria: ["Gate 1 评审通过", "开发环境就绪", "接口文档冻结"],
      exit_criteria: ["单元测试覆盖率 ≥ 80%", "集成测试通过", "代码审查完成"],
      deliverables: ["可部署版本", "测试报告", "部署手册", "API 文档"],
      duration_days: 30,
    },
    {
      name: "Gate 3: 测试验证",
      description: "集成测试、UAT 测试、性能测试与安全测试",
      entry_criteria: ["Gate 2 评审通过", "测试环境就绪", "测试用例评审完成"],
      exit_criteria: ["无 P0/P1 阻塞缺陷", "UAT 签字确认", "安全扫描通过"],
      deliverables: ["测试报告", "UAT 签收单", "安全评估报告", "上线检查清单"],
      duration_days: 15,
    },
    {
      name: "Gate 4: 上线部署",
      description: "灰度发布、全量上线与上线监控",
      entry_criteria: ["Gate 3 评审通过", "上线方案评审通过", "回滚方案就绪"],
      exit_criteria: ["灰度验证通过", "核心指标无异常", "监控告警配置完成"],
      deliverables: ["上线报告", "运维手册", "培训材料", "应急预案"],
      duration_days: 7,
    },
    {
      name: "Gate 5: 运营优化",
      description: "上线后 30 天运营监控，用户反馈收集与持续优化",
      entry_criteria: ["Gate 4 评审通过", "运营团队就位"],
      exit_criteria: ["30 天运营数据达标", "用户满意度 ≥ 目标值", "遗留问题清零"],
      deliverables: ["运营月报", "优化清单", "经验总结", "标准化交付模板"],
      duration_days: 30,
    },
  ],
  best_practices: [
    "每个 Gate 评审必须由项目负责人、技术负责人、业务方三方签字确认",
    "PRD 阶段即引入安全合规审查（等保三级 / HIPAA），避免后期返工",
    "建立 WBS 看板每日站会机制，15 分钟内同步进度与阻塞",
    "使用 RACI 矩阵明确各阶段干系人职责，避免推诿",
    "上线前必须完成回滚演练，确保 30 分钟内可回退",
  ],
  pitfalls: [
    "需求范围蔓延：Gate 0 后禁止新增需求，统一走变更流程",
    "接口联调延期：提前 2 周冻结接口文档，每日同步联调进度",
    "测试环境不稳定：配置专人维护测试环境，每日自动巡检",
    "干系人决策延迟：提前约定各 Gate 评审时间窗口，超时自动升级",
  ],
  templates: [
    { name: "PRD 文档模板", type: "prd" },
    { name: "WBS 任务分解模板", type: "wbs" },
    { name: "风险矩阵模板", type: "risk_matrix" },
    { name: "上线检查清单", type: "checklist" },
  ],
};

export default function MethodologyPanel() {
  const [methodologies, setMethodologies] = useState<MethodologyTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [retroLessons, setRetroLessons] = useState<RetroLessons[]>([]);
  const [showLessons, setShowLessons] = useState(false);

  useEffect(() => {
    methodologyApi.list({ limit: 20 })
      .then((res) => {
        const items = res?.items || [];
        setMethodologies(items);
      })
      .catch((err: unknown) => { devError("Failed to load methodologies", err); })
      .finally(() => setLoading(false));

    // Fetch retrospective lessons for methodology aggregation
    retrospectiveApi.list({ limit: 20 })
      .then(({ items = [] }) => {
        setRetroLessons(items.filter((r: RetroLessons) => r.lessons?.length > 0));
      })
      .catch((err: unknown) => { devError("Failed to load retrospectives", err); });
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const created = await methodologyApi.create(STAGE_GATE_SEED);
      setMethodologies((prev) => [created, ...prev]);
      toast.success("交付方法论模板已创建");
    } catch {
      toast.error("创建失败");
    } finally {
      setSeeding(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">交付方法论</h2>
        <div className="animate-pulse h-20 rounded-lg bg-slate-100 dark:bg-slate-700" />
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm dark:bg-slate-800">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          交付方法论
        </h2>
        {methodologies.length === 0 && (
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {seeding ? "创建中..." : "+ 初始化模板"}
          </button>
        )}
      </div>

      {/* Retrospective Lessons */}
      {retroLessons.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowLessons(!showLessons)}
            className="flex items-center gap-2 text-sm font-medium text-sky-600 hover:text-sky-700 dark:text-sky-400"
          >
            <span>{showLessons ? "▼" : "▶"}</span>
            项目经验沉淀（{retroLessons.length} 条复盘记录）
          </button>
          {showLessons && (
            <div className="mt-3 space-y-3">
              {retroLessons.map((retro) => (
                <div key={retro.id} className="rounded-lg border border-sky-200 bg-sky-50 p-3 dark:border-sky-800 dark:bg-sky-900/20">
                  <h4 className="text-sm font-semibold text-sky-800 dark:text-sky-300 mb-2">
                    {retro.title}
                  </h4>
                  {retro.lessons.map((lesson) => (
                    <div key={lesson.id} className="mb-2 flex items-start gap-2 text-xs">
                      <span className={`mt-0.5 h-2 w-2 rounded-full flex-shrink-0 ${
                        lesson.impact === "高" ? "bg-red-500" :
                        lesson.impact === "中" ? "bg-amber-500" : "bg-slate-400"
                      }`} />
                      <div>
                        <span className="text-slate-700 dark:text-slate-300 font-medium">
                          {lesson.lesson}:
                        </span>
                        <span className="text-slate-500 dark:text-slate-400 ml-1">
                          {lesson.action_item}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {methodologies.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <div className="text-3xl mb-2">📋</div>
          <p className="text-sm">暂无交付方法论模板</p>
          <p className="text-xs mt-1">点击&ldquo;初始化模板&rdquo;创建 Stage-Gate 标准交付路径</p>
        </div>
      ) : (
        <div className="space-y-4">
          {methodologies.map((m) => (
            <div key={m.id} className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
              <button
                onClick={() => setExpanded(expanded === m.id ? null : m.id)}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50"
              >
                <div>
                  <h3 className="font-medium text-slate-900 dark:text-white">{m.name}</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{m.description.slice(0, 80)}...</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                    {m.stages?.length || 0} 阶段
                  </span>
                  <span className="text-slate-400">{expanded === m.id ? "▼" : "▶"}</span>
                </div>
              </button>

              {expanded === m.id && (
                <div className="border-t border-slate-200 dark:border-slate-700 p-4 space-y-4">
                  {/* Stages */}
                  {m.stages?.map((stage, idx) => (
                    <div key={idx} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-700/30">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                          {stage.name}
                        </h4>
                        <span className="text-xs text-slate-500">{stage.duration_days} 天</span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                        {stage.description}
                      </p>
                      <div className="grid gap-2 text-xs md:grid-cols-2">
                        <div>
                          <span className="font-medium text-emerald-600 dark:text-emerald-400">进入条件:</span>
                          <ul className="list-disc list-inside text-slate-600 dark:text-slate-400 mt-1">
                            {stage.entry_criteria?.map((c, i) => <li key={i}>{c}</li>)}
                          </ul>
                        </div>
                        <div>
                          <span className="font-medium text-amber-600 dark:text-amber-400">完成条件:</span>
                          <ul className="list-disc list-inside text-slate-600 dark:text-slate-400 mt-1">
                            {stage.exit_criteria?.map((c, i) => <li key={i}>{c}</li>)}
                          </ul>
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className="text-xs font-medium text-sky-600 dark:text-sky-400">交付物: </span>
                        <span className="text-xs text-slate-600 dark:text-slate-400">
                          {stage.deliverables?.join(" · ")}
                        </span>
                      </div>
                    </div>
                  ))}

                  {/* Best practices */}
                  {m.best_practices?.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-emerald-700 dark:text-emerald-400 mb-2">
                        最佳实践
                      </h4>
                      <ul className="list-disc list-inside text-xs text-slate-600 dark:text-slate-400 space-y-1">
                        {m.best_practices.map((bp, i) => <li key={i}>{bp}</li>)}
                      </ul>
                    </div>
                  )}

                  {/* Pitfalls */}
                  {m.pitfalls?.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-rose-700 dark:text-rose-400 mb-2">
                        常见陷阱
                      </h4>
                      <ul className="list-disc list-inside text-xs text-slate-600 dark:text-slate-400 space-y-1">
                        {m.pitfalls.map((p, i) => <li key={i}>{p}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
