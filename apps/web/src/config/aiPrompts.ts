// AI 交互话术配置
// 将"AI感"的交互转换为"方法论感"的专业表达

export interface AIPrompt {
  id: string;
  original: string;
  optimized: string;
  context: string;
  usage: string;
}

// 生成场景话术
export const GENERATION_PROMPTS: AIPrompt[] = [
  {
    id: "gen-1",
    original: "🤖 AI助手：正在为您生成用户故事...",
    optimized: "📋 需求分析框架：正在基于您的调研输入，按医疗信息化标准生成用户故事...",
    context: "生成用户故事时",
    usage: "loading状态"
  },
  {
    id: "gen-2",
    original: "AI建议：您可以这样写...",
    optimized: "标准框架建议：根据医疗信息化最佳实践，建议采用以下结构...",
    context: "提供生成内容时",
    usage: "suggestion"
  },
  {
    id: "gen-3",
    original: "重新生成",
    optimized: "调整框架参数",
    context: "用户要求重新生成",
    usage: "button"
  },
  {
    id: "gen-4",
    original: "AI生成完成",
    optimized: "框架内容已生成",
    context: "生成完成",
    usage: "success"
  },
  {
    id: "gen-5",
    original: "AI认为这个需求...",
    optimized: "从医疗业务角度分析，该需求...",
    context: "分析需求时",
    usage: "analysis"
  }
];

// 检查场景话术
export const CHECK_PROMPTS: AIPrompt[] = [
  {
    id: "check-1",
    original: "⚠️ AI检测到问题",
    optimized: "⚠️ 框架完整性检查",
    context: "发现问题时",
    usage: "warning"
  },
  {
    id: "check-2",
    original: "AI建议补充以下内容",
    optimized: "根据医疗信息化标准要求，建议补充以下要素",
    context: "建议补充时",
    usage: "suggestion"
  },
  {
    id: "check-3",
    original: "检查通过",
    optimized: "框架完整性检查通过",
    context: "检查通过",
    usage: "success"
  },
  {
    id: "check-4",
    original: "AI发现技术术语",
    optimized: "检测到技术实现语言，建议转换为业务描述",
    context: "检测到技术术语",
    usage: "warning"
  }
];

// 评审场景话术
export const REVIEW_PROMPTS: AIPrompt[] = [
  {
    id: "review-1",
    original: "准备评审材料",
    optimized: "生成评审会议材料包",
    context: "评审准备",
    usage: "action"
  },
  {
    id: "review-2",
    original: "AI生成评审问题",
    optimized: "基于利益相关方分析，预设可能提出的关键问题",
    context: "生成Q&A",
    usage: "description"
  },
  {
    id: "review-3",
    original: "预测风险",
    optimized: "基于医疗项目经验，识别潜在风险点",
    context: "风险识别",
    usage: "analysis"
  }
];

// 通用话术映射
export const UI_LABELS: Record<string, string> = {
  // 按钮文字
  "重新生成": "调整参数重试",
  "AI生成": "框架生成",
  "AI建议": "框架建议",
  "确认": "确认并继续",
  "取消": "返回修改",

  // 状态提示
  "生成中...": "分析中...",
  "AI思考中": "框架处理中",
  "AI已完成": "处理完成",

  // 功能区标题
  "AI助手": "PRD框架",
  "AI建议区": "标准框架建议",
  "智能生成": "标准化生成",

  // 帮助提示
  "让AI帮你写": "使用标准化框架生成",
  "AI正在分析": "框架正在分析您的输入",
  "AI推荐": "框架推荐"
};

// 章节专属话术
export const CHAPTER_PROMPTS: Record<string, { title: string; description: string; tip: string }> = {
  background: {
    title: "第1章：背景与目标",
    description: "阐述项目背景、痛点分析和成功指标",
    tip: "建议先完成用户调研，确保痛点有数据支撑"
  },
  "user-stories": {
    title: "第2章：用户故事",
    description: "定义目标用户及其需求场景",
    tip: "用户故事要覆盖主要业务流程，验收标准要可测试"
  },
  "business-flow": {
    title: "第3章：业务流程",
    description: "描述业务主流程、分支流程和异常处理",
    tip: "建议配合流程图一起评审"
  },
  "functional-specs": {
    title: "第4章：功能规格",
    description: "详细描述前端界面和后台功能",
    tip: "使用业务语言，避免技术实现细节"
  },
  "data-requirements": {
    title: "第5章：数据需求",
    description: "定义数据实体、状态机和数据流转",
    tip: "与开发对齐实体设计"
  },
  compliance: {
    title: "第6章：合规要求 ⭐",
    description: "医疗合规、等保要求、多院区适配",
    tip: "这是医疗项目最核心的章节，建议提前与医务科沟通"
  },
  analytics: {
    title: "第7章：数据埋点",
    description: "定义核心指标、埋点事件和数据看板",
    tip: "指标要与第1章的成功指标对应"
  },
  milestones: {
    title: "第8章：里程碑",
    description: "项目时间规划和分阶段交付",
    tip: "MVP阶段要聚焦核心功能，预留缓冲时间"
  }
};

// 开场白话术
export const OPENING_SPEECHES = {
  prd: `我将使用医疗产品需求标准化工作法帮您完成这份PRD。

这套框架专为医疗信息化场景设计，包含八章结构：
1. 背景与目标 - 建立项目价值共识
2. 用户故事 - 明确为谁解决问题
3. 业务流程 - 清晰描述业务运转
4. 功能规格 - 详细定义功能范围
5. 数据需求 - 定义数据实体和流转
6. 合规要求 - 确保医疗合规（核心章节）
7. 数据埋点 - 定义成功衡量标准
8. 里程碑 - 规划分阶段落地

我们从第1章开始，请描述一下这个项目的背景和要解决的痛点。`,

  review: `评审材料已按标准化框架生成，包含：

📋 评审议程 - 90分钟高效会议流程
✓ 决策清单 - 4个关键决策点及建议方案
⚠️ 风险预案 - 4个主要风险及应对措施
💬 预设Q&A - 各科室可能提出的问题及答复

建议提前1天将PRD发送给参会人，会前与关键相关方做一轮预沟通，确保评审高效通过。`,

  compliance: `医疗合规检查已启动，正在按以下维度扫描：

🔒 数据安全 - 加密存储、传输加密、权限控制
👤 隐私保护 - 患者授权、数据最小化、保留期限
📊 审计追溯 - 操作日志、日志留存、异常告警
⚕️ 业务合规 - 借阅资质、收费标准、退款流程
🔧 系统安全 - 身份认证、登录锁定、会话超时

这是医疗项目的核心章节，所有必选项必须通过检查。`,
};

// 导出完整话术配置
export const ALL_PROMPTS = {
  generation: GENERATION_PROMPTS,
  check: CHECK_PROMPTS,
  review: REVIEW_PROMPTS,
  ui: UI_LABELS,
  chapters: CHAPTER_PROMPTS,
  openings: OPENING_SPEECHES
};

export default ALL_PROMPTS;
