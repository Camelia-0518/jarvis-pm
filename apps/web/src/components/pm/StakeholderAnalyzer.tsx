"use client";

import { useState } from "react";

// 利益相关方定义
interface Stakeholder {
  id: string;
  name: string;
  icon: string;
  color: string;
  role: string;
  concerns: string[];
  painPoints: string[];
  successCriteria: string[];
  communicationStrategy: string;
  involvement: "high" | "medium" | "low";
  influence: "high" | "medium" | "low";
}

const STAKEHOLDERS: Stakeholder[] = [
  {
    id: "medical",
    name: "医务科",
    icon: "⚕️",
    color: "bg-rose-100 text-rose-700",
    role: "医疗质量与合规监管",
    concerns: [
      "医疗规范符合性",
      "患者隐私保护",
      "医疗纠纷风险",
      "医疗事故责任界定",
    ],
    painPoints: [
      "线上流程难以把控医疗风险",
      "患者投诉增加处理压力",
      "合规审查工作量大",
    ],
    successCriteria: [
      "零医疗纠纷",
      "100%合规审查通过",
      "患者投诉率低于1%",
    ],
    communicationStrategy: "提前介入，PRD阶段就征求合规意见；提供完整的合规说明章节",
    involvement: "high",
    influence: "high",
  },
  {
    id: "it",
    name: "信息科",
    icon: "🔧",
    color: "bg-sky-100 text-sky-700",
    role: "系统对接与技术支持",
    concerns: [
      "系统稳定性",
      "数据安全性",
      "与HIS系统对接复杂度",
      "运维成本",
    ],
    painPoints: [
      "接口对接工作量大",
      "第三方系统依赖风险",
      "历史系统兼容性问题",
    ],
    successCriteria: [
      "系统可用性99.9%",
      "接口响应时间<500ms",
      "零数据安全事故",
    ],
    communicationStrategy: "技术方案提前沟通；明确接口需求和对接计划；提供测试环境支持",
    involvement: "high",
    influence: "medium",
  },
  {
    id: "finance",
    name: "财务科",
    icon: "💰",
    color: "bg-emerald-100 text-emerald-700",
    role: "收费管理与财务合规",
    concerns: [
      "收费合规性",
      "押金管理安全",
      "退款流程规范",
      "财务对账准确",
    ],
    painPoints: [
      "线上支付对账复杂",
      "退款纠纷处理",
      "发票管理混乱",
    ],
    successCriteria: [
      "收费准确率100%",
      "退款处理时间<7天",
      "财务对账差异为0",
    ],
    communicationStrategy: "明确收费标准和流程；提供完整的财务流程说明；定期同步收费数据",
    involvement: "medium",
    influence: "medium",
  },
  {
    id: "pathology",
    name: "病理科",
    icon: "🔬",
    color: "bg-purple-100 text-purple-700",
    role: "切片管理与审核执行",
    concerns: [
      "审核工作量增加",
      "切片管理责任",
      "患者咨询压力",
      "工作流改变适应",
    ],
    painPoints: [
      "线上申请增加审核工作",
      "患者电话咨询增多",
      "系统操作学习成本",
    ],
    successCriteria: [
      "审核效率提升30%",
      "患者满意度>90%",
      "系统操作培训通过率100%",
    ],
    communicationStrategy: "强调效率提升价值；提供充分的培训支持；听取一线操作反馈",
    involvement: "high",
    influence: "high",
  },
  {
    id: "leader",
    name: "院领导",
    icon: "👔",
    color: "bg-amber-100 text-amber-700",
    role: "战略决策与资源审批",
    concerns: [
      "投入产出比",
      "项目成功率",
      "医院声誉影响",
      "政策合规性",
    ],
    painPoints: [
      "信息化项目失败风险",
      "预算超支压力",
      "各部门协调困难",
    ],
    successCriteria: [
      "项目按期交付",
      "预算控制在±10%",
      "患者满意度提升",
    ],
    communicationStrategy: "定期汇报关键里程碑；用数据说话；提前暴露风险",
    involvement: "medium",
    influence: "high",
  },
];

// 预设Q&A
interface QA {
  stakeholder: string;
  question: string;
  answer: string;
  category: string;
}

const PRESET_QA: QA[] = [
  {
    stakeholder: "医务科",
    question: "线上化后如何确保医疗合规？",
    answer: "系统设置了多重合规检查：①申请时自动核验患者身份和病历信息；②审核流程设置双人复核机制；③所有操作留痕可追溯；④接入医务科审核节点，关键环节人工确认。",
    category: "合规",
  },
  {
    stakeholder: "医务科",
    question: "患者隐私如何保护？",
    answer: "①敏感数据加密存储和传输；②前端展示脱敏处理；③严格权限控制，仅授权人员可见；④操作日志完整记录；⑤定期安全审计。符合《个人信息保护法》和等保三级要求。",
    category: "安全",
  },
  {
    stakeholder: "信息科",
    question: "HIS系统对接复杂吗？需要什么支持？",
    answer: "对接相对简单，主要需要：①患者基本信息查询接口；②病历信息查询接口。预计2周完成对接开发，需要信息科提供接口文档和测试环境支持。",
    category: "技术",
  },
  {
    stakeholder: "信息科",
    question: "系统安全性如何保证？",
    answer: "①等保三级标准建设；②HTTPS传输加密；③数据库加密存储；④身份认证+权限控制；⑤操作日志审计；⑥定期漏洞扫描。可以满足医院信息安全要求。",
    category: "安全",
  },
  {
    stakeholder: "财务科",
    question: "押金怎么管理？能原路退回吗？",
    answer: "押金进入医院财务指定账户，不经过第三方。支持原路退回，退款申请后7个工作日内退回原支付账户。财务科可随时查看押金明细报表。",
    category: "财务",
  },
  {
    stakeholder: "财务科",
    question: "收费合规吗？有依据吗？",
    answer: "严格按照XX省医疗服务价格标准执行，病理切片借阅费XX元/片，有明确的收费依据。系统内置收费标准，不得擅自修改。",
    category: "合规",
  },
  {
    stakeholder: "病理科",
    question: "线上化会增加我们工作量吗？",
    answer: "短期内需要适应新流程，但长期看会减轻工作量：①系统自动核验信息，减少人工核对；②患者可自助查询进度，减少电话咨询；③电子申请单自动归档，减少纸质材料整理。预计审核效率可提升30%。",
    category: "效率",
  },
  {
    stakeholder: "病理科",
    question: "我们不会用系统怎么办？",
    answer: "①上线前提供完整培训，确保人人过关；②设置试运行期，有问题及时调整；③提供操作手册和在线帮助；④设置客服热线，随时答疑。我们会确保大家熟练掌握。",
    category: "培训",
  },
  {
    stakeholder: "院领导",
    question: "这个项目投入产出比如何？",
    answer: "投入：开发成本XX万，年运维成本XX万。产出：①患者满意度提升，减少投诉；②病理科审核效率提升30%；③提升医院信息化水平。预期1.5年收回成本，后续每年节省人力成本XX万。",
    category: "收益",
  },
  {
    stakeholder: "院领导",
    question: "项目风险有哪些？怎么应对？",
    answer: "主要风险：①HIS对接延期（应对：提前启动对接，预留缓冲时间）；②用户接受度低（应对：保留线下渠道并行，逐步引导）。详细风险清单和应对措施见PRD第8章。",
    category: "风险",
  },
];

export default function StakeholderAnalyzer() {
  const [selectedStakeholder, setSelectedStakeholder] = useState<Stakeholder | null>(null);
  const [activeTab, setActiveTab] = useState<"stakeholders" | "qa">("stakeholders");
  const [selectedCategory, setSelectedCategory] = useState<string>("全部");

  const categories = ["全部", ...Array.from(new Set(PRESET_QA.map(q => q.category)))];
  const filteredQA = selectedCategory === "全部"
    ? PRESET_QA
    : PRESET_QA.filter(q => q.category === selectedCategory);

  return (
    <div className="space-y-6">
      {/* 标签切换 */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab("stakeholders")}
          className={`flex items-center gap-1 px-4 py-2 text-sm font-medium ${
            activeTab === "stakeholders"
              ? "border-b-2 border-sky-500 text-sky-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          👥 利益相关方
        </button>
        <button
          onClick={() => setActiveTab("qa")}
          className={`flex items-center gap-1 px-4 py-2 text-sm font-medium ${
            activeTab === "qa"
              ? "border-b-2 border-sky-500 text-sky-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          💬 预设Q&A
        </button>
      </div>

      {/* 利益相关方分析 */}
      {activeTab === "stakeholders" && (
        <div className="grid grid-cols-1 gap-4">
          {/* 相关方列表 */}
          <div className="grid grid-cols-2 gap-3">
            {STAKEHOLDERS.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedStakeholder(s)}
                className={`rounded-lg border p-3 text-left transition-colors ${
                  selectedStakeholder?.id === s.id
                    ? "border-sky-500 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                    : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{s.icon}</span>
                  <div>
                    <div className="font-medium text-slate-800 dark:text-slate-200">
                      {s.name}
                    </div>
                    <div className="text-xs text-slate-500">{s.role}</div>
                  </div>
                </div>
                <div className="mt-2 flex gap-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    s.involvement === "high" ? "bg-rose-100 text-rose-700" :
                    s.involvement === "medium" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                  }`}>
                    参与度: {s.involvement === "high" ? "高" : s.involvement === "medium" ? "中" : "低"}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    s.influence === "high" ? "bg-rose-100 text-rose-700" :
                    s.influence === "medium" ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                  }`}>
                    影响力: {s.influence === "high" ? "高" : s.influence === "medium" ? "中" : "低"}
                  </span>
                </div>
              </button>
            ))}
          </div>

          {/* 详情面板 */}
          {selectedStakeholder && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-3xl">{selectedStakeholder.icon}</span>
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-white">
                      {selectedStakeholder.name}
                    </h3>
                    <p className="text-sm text-slate-500">{selectedStakeholder.role}</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedStakeholder(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <div className="mt-4 space-y-4">
                {/* 关注点 */}
                <div>
                  <h4 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                    🔍 核心关注点
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedStakeholder.concerns.map((c, i) => (
                      <span key={i} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-700">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>

                {/* 痛点 */}
                <div>
                  <h4 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                    😣 痛点
                  </h4>
                  <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
                    {selectedStakeholder.painPoints.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>

                {/* 成功标准 */}
                <div>
                  <h4 className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                    ✅ 成功标准
                  </h4>
                  <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
                    {selectedStakeholder.successCriteria.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>

                {/* 沟通策略 */}
                <div className="rounded-lg bg-sky-50 p-3 dark:bg-sky-900/20">
                  <h4 className="mb-1 text-sm font-medium text-sky-800 dark:text-sky-200">
                    💡 沟通策略
                  </h4>
                  <p className="text-sm text-sky-700 dark:text-sky-300">
                    {selectedStakeholder.communicationStrategy}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 预设Q&A */}
      {activeTab === "qa" && (
        <div className="space-y-4">
          {/* 分类筛选 */}
          <div className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-full px-3 py-1 text-xs ${
                  selectedCategory === cat
                    ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30"
                    : "bg-slate-100 text-slate-600 dark:bg-slate-700"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Q&A列表 */}
          <div className="space-y-3">
            {filteredQA.map((qa, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800"
              >
                <div className="flex items-center gap-2">
                  <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700">
                    {qa.stakeholder}
                  </span>
                  <span className="text-xs text-slate-400">{qa.category}</span>
                </div>
                <div className="mt-2 font-medium text-slate-800 dark:text-slate-200">
                  Q: {qa.question}
                </div>
                <div className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  A: {qa.answer}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
