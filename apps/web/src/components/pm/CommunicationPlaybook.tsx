"use client";

import { useState } from "react";

// 沟通场景定义
type ScenarioType = "dev" | "business" | "leader" | "medical" | "it" | "finance";

interface CommunicationScenario {
  id: ScenarioType;
  title: string;
  icon: string;
  description: string;
  situations: CommunicationSituation[];
}

interface CommunicationSituation {
  id: string;
  title: string;
  context: string;
  goal: string;
  approach: string[];
  scripts: string[];
  pitfalls: string[];
}

const COMMUNICATION_SCENARIOS: CommunicationScenario[] = [
  {
    id: "dev",
    title: "与开发沟通",
    icon: "💻",
    description: "技术可行性确认、排期协商、需求变更",
    situations: [
      {
        id: "dev-1",
        title: "确认技术可行性",
        context: "新功能需要开发团队评估是否可实现",
        goal: "获得技术方案确认和排期",
        approach: [
          "提前准备好需求背景和业务价值",
          "用原型/流程图辅助说明，而非纯文字",
          "询问技术方案建议，表现出尊重",
          "确认关键接口依赖和外部系统",
        ],
        scripts: [
          "这个功能我想先确认一下技术可行性，你看方案A和方案B哪个更合适？",
          "业务上我们希望达到XX效果，技术上有什么建议的实现方式吗？",
          "这个需求涉及HIS系统对接，你觉得最大的技术风险在哪里？",
          "如果按这个方案做，大概需要多少工作量？有没有可以简化的地方？",
        ],
        pitfalls: [
          "❌ 不要说：这个很简单吧，几天能做完？",
          "❌ 不要说：用户就要这样，技术上你们想办法",
          "❌ 不要跳过技术评估直接要排期",
        ],
      },
      {
        id: "dev-2",
        title: "需求变更协商",
        context: "业务方要求变更，需要调整开发计划",
        goal: "获得开发理解，调整排期，确保质量",
        approach: [
          "坦诚说明变更原因，不要隐瞒",
          "提供变更的优先级和业务价值",
          "询问对现有进度的影响",
          "协商是否可以分期实现",
        ],
        scripts: [
          "有个需求变更需要和你们同步，原因是XX，优先级的考虑是XX",
          "这个变更对当前迭代影响大吗？是否可以把XX功能挪到下个迭代？",
          "如果时间紧张，我们先做核心功能，周边功能二期优化可以吗？",
          "这次变更是我的责任，排期调整我会和业务方沟通，争取不压缩开发时间",
        ],
        pitfalls: [
          "❌ 不要说：就改一点点，很快吧",
          "❌ 不要频繁变更且不做优先级取舍",
          "❌ 不要把业务压力直接转嫁给开发",
        ],
      },
      {
        id: "dev-3",
        title: "推动延期项目",
        context: "项目进度落后，需要加速或调整",
        goal: "了解真实进度，协商解决方案",
        approach: [
          "先了解情况，而非指责",
          "询问具体卡点，提供资源支持",
          "协商范围裁剪或时间调整",
          "共同承担，而非单方面施压",
        ],
        scripts: [
          "我看到目前进度比计划落后，主要卡在哪里？有什么我可以协调的？",
          "如果时间确实不够，我们一起看看哪些功能可以放到二期？",
          "需要我升级给领导申请资源支持吗？",
          "延期责任我们一起承担，重点是找到解决方案",
        ],
        pitfalls: [
          "❌ 不要说：你们怎么又延期了",
          "❌ 不要只知道催，不提供支持",
          "❌ 不要把延期责任全推给开发",
        ],
      },
    ],
  },
  {
    id: "business",
    title: "与业务方沟通",
    icon: "📊",
    description: "需求澄清、预期管理、上线通知",
    situations: [
      {
        id: "biz-1",
        title: "澄清模糊需求",
        context: "业务方说'做个线上申请功能'，需求不明确",
        goal: "挖掘真实需求，明确范围",
        approach: [
          "用场景提问，而非直接问功能",
          "了解用户是谁，解决什么问题",
          "确认成功的标准是什么",
          "用原型确认理解是否一致",
        ],
        scripts: [
          "这个功能的用户是谁？他们现在是怎么做的？",
          "用户现在最大的痛点是什么？这个功能能解决吗？",
          "上线后怎么衡量成功？预期使用率是多少？",
          "我画了个简单的流程图，你看是不是这样的逻辑？",
        ],
        pitfalls: [
          "❌ 不要直接按字面意思做，不问背后原因",
          "❌ 不要承诺做不到的功能",
          "❌ 不要用技术术语和业务方沟通",
        ],
      },
      {
        id: "biz-2",
        title: "管理不切实际的预期",
        context: "业务方要求1个月上线完整功能",
        goal: "调整预期，协商分阶段交付",
        approach: [
          "先认可业务目标，表示理解",
          "用数据说明工作量",
          "提供分阶段方案",
          "强调质量和风险",
        ],
        scripts: [
          "理解你们希望尽快上线的心情，这个目标我也很认同",
          "按目前的范围评估，完整功能大概需要XX人月，一个月确实比较紧张",
          "我建议分三期：第一期先做核心流程，2周上线；第二期做优化功能；第三期做高级功能",
          "如果时间压得太紧，可能会影响质量，上线后出问题反而影响用户体验",
        ],
        pitfalls: [
          "❌ 不要直接说做不到，而不给方案",
          "❌ 不要为了讨好而承诺做不到的事",
          "❌ 不要用技术细节解释，业务方不关心",
        ],
      },
    ],
  },
  {
    id: "leader",
    title: "与领导沟通",
    icon: "👔",
    description: "进度汇报、资源申请、风险升级",
    situations: [
      {
        id: "leader-1",
        title: "定期进度汇报",
        context: "向领导汇报项目进展",
        goal: "让领导了解进展，获得支持",
        approach: [
          "先说结论，再说细节",
          "用数据说话",
          "主动暴露风险，而非隐瞒",
          "提出需要的支持",
        ],
        scripts: [
          "目前整体进度正常，按计划下周可以完成PRD评审",
          "当前完成度75%，主要进展是XX，下一步计划XX",
          "有个风险需要同步：XX，我的应对策略是XX",
          "为了按期完成，需要您帮忙协调XX资源",
        ],
        pitfalls: [
          "❌ 不要只报喜不报忧",
          "❌ 不要讲太多细节，领导没时间",
          "❌ 不要等问题爆发了才汇报",
        ],
      },
      {
        id: "leader-2",
        title: "风险升级",
        context: "遇到超出自己处理权限的问题",
        goal: "获得领导支持，推动问题解决",
        approach: [
          "说明问题的严重性和影响",
          "说明自己已经尝试过的解决方案",
          "明确提出需要领导做什么",
          "提供选项而非只抛问题",
        ],
        scripts: [
          "有个问题超出了我的处理权限，需要升级请您帮忙",
          "这个问题的背景是XX，如果不解决会导致XX后果",
          "我已经尝试了XX方法，但卡在了XX环节",
          "可能需要您出面协调XX部门，或者申请XX资源",
        ],
        pitfalls: [
          "❌ 不要一出问题就升级，要先自己尝试",
          "❌ 不要只抛问题不给方案",
          "❌ 不要过度升级小事",
        ],
      },
    ],
  },
  {
    id: "medical",
    title: "与医务科沟通",
    icon: "⚕️",
    description: "医疗合规、隐私保护、纠纷风险",
    situations: [
      {
        id: "med-1",
        title: "确认医疗合规要求",
        context: "新功能需要医务科审核合规性",
        goal: "获得合规确认，避免后期返工",
        approach: [
          "提前了解相关法规，展现专业度",
          "主动提出合规措施，而非等对方提",
          "用案例说明风险防控",
          "预留修改时间",
        ],
        scripts: [
          "这个功能涉及患者隐私，我查阅了《医疗机构管理条例》XX条，设计了XX合规措施",
          "我们的方案是XX，您看是否符合医院的合规要求？",
          "历史上是否有类似的医疗纠纷案例？我们可以怎么预防？",
          "如果方案需要调整，建议预留一周修改时间",
        ],
        pitfalls: [
          "❌ 不要说：技术上是没问题的",
          "❌ 不要等开发完了再找医务科",
          "❌ 不要对医疗法规一无所知",
        ],
      },
    ],
  },
  {
    id: "it",
    title: "与信息科沟通",
    icon: "🔧",
    description: "系统对接、安全性、故障处理",
    situations: [
      {
        id: "it-1",
        title: "申请系统对接",
        context: "需要对接HIS系统或医保系统",
        goal: "获得接口支持，明确对接方案",
        approach: [
          "提前了解对方系统架构",
          "明确对接的数据范围和频率",
          "询问安全要求",
          "协调测试环境",
        ],
        scripts: [
          "我们需要对接HIS系统的XX模块，获取XX数据，大概的调用频率是XX",
          "对接方案我们想的是XX，您看是否可行？",
          "安全方面有什么要求？需要走什么审批流程？",
          "能否提供测试环境？预计什么时候可以联调？",
        ],
        pitfalls: [
          "❌ 不要直接要账号密码",
          "❌ 不要绕过信息科直接找开发商",
          "❌ 不要低估对接复杂度",
        ],
      },
    ],
  },
  {
    id: "finance",
    title: "与财务科沟通",
    icon: "💰",
    description: "收费标准、押金管理、支付对接",
    situations: [
      {
        id: "fin-1",
        title: "确认收费和押金规则",
        context: "功能涉及收费和押金",
        goal: "明确财务规则，确保合规",
        approach: [
          "了解现有收费项目和标准",
          "明确押金收取和退还规则",
          "确认财务系统对接需求",
          "了解发票和结算流程",
        ],
        scripts: [
          "这个功能涉及切片借阅收费，目前的收费标准是什么？",
          "押金收取和退还的规则是怎样的？有什么时限要求？",
          "需要和财务系统对接吗？对接方式是什么？",
          "患者退款流程是怎样的？多久可以到账？",
        ],
        pitfalls: [
          "❌ 不要擅自定价",
          "❌ 不要忽视押金管理的合规要求",
          "❌ 不要等上线前才找财务科",
        ],
      },
    ],
  },
];

export default function CommunicationPlaybook() {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioType>("dev");
  const [selectedSituation, setSelectedSituation] = useState<string | null>(null);

  const scenario = COMMUNICATION_SCENARIOS.find((s) => s.id === selectedScenario)!;
  const situation = scenario.situations.find((s) => s.id === selectedSituation);

  return (
    <div className="space-y-4">
      {/* 场景选择 */}
      <div className="grid grid-cols-3 gap-2">
        {COMMUNICATION_SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => {
              setSelectedScenario(s.id);
              setSelectedSituation(null);
            }}
            className={`rounded-lg border p-3 text-left transition-colors ${
              selectedScenario === s.id
                ? "border-sky-500 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800"
            }`}
          >
            <div className="text-2xl">{s.icon}</div>
            <div className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
              {s.title}
            </div>
          </button>
        ))}
      </div>

      {/* 具体场景列表 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-3 font-semibold text-slate-900 dark:text-white">
          {scenario.icon} {scenario.title}
        </h3>
        <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
          {scenario.description}
        </p>

        <div className="space-y-2">
          {scenario.situations.map((sit) => (
            <button
              key={sit.id}
              onClick={() => setSelectedSituation(sit.id)}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                selectedSituation === sit.id
                  ? "border-sky-500 bg-sky-50 dark:border-sky-700 dark:bg-sky-900/20"
                  : "border-slate-200 hover:border-slate-300 dark:border-slate-700"
              }`}
            >
              <div className="font-medium text-slate-800 dark:text-slate-200">
                {sit.title}
              </div>
              <div className="mt-1 text-xs text-slate-500">{sit.context}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 详细话术 */}
      {situation && (
        <div className="space-y-4">
          {/* 目标 */}
          <div className="rounded-lg bg-sky-50 p-4 dark:bg-sky-900/20">
            <div className="text-sm font-medium text-sky-800 dark:text-sky-200">
              🎯 沟通目标
            </div>
            <div className="mt-1 text-sm text-sky-700 dark:text-sky-300">
              {situation.goal}
            </div>
          </div>

          {/* 策略 */}
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-3 font-medium text-slate-800 dark:text-slate-200">
              📋 沟通策略
            </div>
            <ul className="space-y-2">
              {situation.approach.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                  <span className="text-sky-500">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* 话术 */}
          <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-3 font-medium text-slate-800 dark:text-slate-200">
              💬 推荐话术
            </div>
            <div className="space-y-2">
              {situation.scripts.map((script, i) => (
                <div
                  key={i}
                  className="rounded bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-700/50 dark:text-slate-300"
                >
                  "{script}"
                </div>
              ))}
            </div>
          </div>

          {/* 雷区 */}
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 dark:border-rose-800 dark:bg-rose-900/20">
            <div className="mb-3 font-medium text-rose-800 dark:text-rose-200">
              ⚠️ 雷区警示
            </div>
            <ul className="space-y-1">
              {situation.pitfalls.map((pitfall, i) => (
                <li key={i} className="text-sm text-rose-700 dark:text-rose-300">
                  {pitfall}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
