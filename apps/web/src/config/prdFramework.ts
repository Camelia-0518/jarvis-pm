// 医疗信息化PRD八章框架配置
// 适用于Jarvis PM - 帮助前端背景实习生产出专业级PRD

export interface PRDChapter {
  id: string;
  number: number;
  title: string;
  icon: string;
  description: string;
  sections: ChapterSection[];
  tips: string[];
  medicalNotes?: string[];
}

export interface ChapterSection {
  id: string;
  title: string;
  required: boolean;
  placeholder: string;
  aiPrompt: string;
}

export const PRD_FRAMEWORK: PRDChapter[] = [
  {
    id: "background",
    number: 1,
    title: "背景与目标",
    icon: "🎯",
    description: "阐述项目背景、痛点分析和成功指标",
    sections: [
      {
        id: "pain-points",
        title: "痛点分析",
        required: true,
        placeholder: "描述当前业务流程中的主要痛点...",
        aiPrompt: "基于用户调研结果，列出3-5个核心痛点，每个痛点需包含：现象描述、影响范围、量化数据"
      },
      {
        id: "business-value",
        title: "业务价值",
        required: true,
        placeholder: "说明本项目能为业务带来的价值...",
        aiPrompt: "说明项目解决痛点后带来的业务价值，包括效率提升、成本降低、体验改善等方面"
      },
      {
        id: "success-metrics",
        title: "成功指标",
        required: true,
        placeholder: "定义可量化的成功指标...",
        aiPrompt: "定义3-5个可量化的成功指标（KPI），遵循SMART原则，包含基线值和目标值"
      }
    ],
    tips: [
      "用数据说话，每个痛点尽量有量化支撑",
      "成功指标要可衡量、可追踪",
      "避免描述解决方案，聚焦问题本身"
    ],
    medicalNotes: [
      "如涉及患者服务，需说明对就医体验的提升",
      "如涉及医务人员，需说明对工作效率的改善"
    ]
  },
  {
    id: "user-stories",
    number: 2,
    title: "用户故事",
    icon: "👥",
    description: "定义目标用户及其需求场景",
    sections: [
      {
        id: "user-personas",
        title: "用户画像",
        required: true,
        placeholder: "描述目标用户的特征...",
        aiPrompt: "定义主要用户群体，包含：用户类型、年龄/职业特征、数字化程度、核心诉求"
      },
      {
        id: "user-stories-list",
        title: "用户故事列表",
        required: true,
        placeholder: "作为[角色]，我希望[功能]，以便[价值]...",
        aiPrompt: "生成5-8个用户故事，格式：作为[角色]，我希望[功能]，以便[价值]。每个故事需有优先级（P0/P1/P2）"
      },
      {
        id: "acceptance-criteria",
        title: "验收标准",
        required: true,
        placeholder: "定义每个用户故事的验收条件...",
        aiPrompt: "为每个P0/P1用户故事编写验收标准，格式：Given[前提]When[操作]Then[结果]"
      }
    ],
    tips: [
      "用户故事要覆盖主要业务流程",
      "验收标准要可测试、可验证",
      "避免技术术语，用业务语言描述"
    ],
    medicalNotes: [
      "需区分患者、家属、医务人员等不同角色",
      "考虑老年人等特殊群体的使用场景"
    ]
  },
  {
    id: "business-flow",
    number: 3,
    title: "业务流程",
    icon: "🔄",
    description: "描述业务主流程、分支流程和异常处理",
    sections: [
      {
        id: "main-flow",
        title: "主流程",
        required: true,
        placeholder: "描述主要业务流程...",
        aiPrompt: "用Mermaid语法绘制主业务流程图，包含正常情况下的完整流程"
      },
      {
        id: "branch-flows",
        title: "分支流程",
        required: false,
        placeholder: "描述分支业务流程...",
        aiPrompt: "列出主要的分支流程场景，如不同用户类型的差异化流程"
      },
      {
        id: "exception-handling",
        title: "异常处理",
        required: true,
        placeholder: "描述异常情况的处理方式...",
        aiPrompt: "列出可能的异常情况（如网络中断、资料不全等）及对应的处理机制"
      }
    ],
    tips: [
      "流程图要清晰展示各环节参与者",
      "标注关键决策点和等待环节",
      "异常处理要覆盖常见失败场景"
    ],
    medicalNotes: [
      "需体现医疗审核环节的特殊要求",
      "考虑紧急情况的处理流程"
    ]
  },
  {
    id: "functional-specs",
    number: 4,
    title: "功能规格",
    icon: "⚙️",
    description: "详细描述前端界面和后台功能",
    sections: [
      {
        id: "frontend-features",
        title: "前端功能",
        required: true,
        placeholder: "描述用户端功能...",
        aiPrompt: "分模块描述前端功能，每个功能包含：功能名称、功能描述、输入输出、校验规则"
      },
      {
        id: "backend-features",
        title: "后台功能",
        required: true,
        placeholder: "描述管理后台功能...",
        aiPrompt: "描述管理后台的核心功能，包括权限管理、数据管理、审核流程等"
      },
      {
        id: "interaction-design",
        title: "交互说明",
        required: false,
        placeholder: "描述关键交互逻辑...",
        aiPrompt: "描述关键页面的交互逻辑，包括页面跳转、状态变化、错误提示等"
      }
    ],
    tips: [
      "功能描述要避免技术实现细节",
      "使用表格形式呈现更清晰",
      "标注功能优先级（P0/P1/P2）"
    ],
    medicalNotes: [
      "涉及患者数据的功能需说明隐私保护措施",
      "审核类功能需说明操作留痕要求"
    ]
  },
  {
    id: "data-requirements",
    number: 5,
    title: "数据需求",
    icon: "🗄️",
    description: "定义数据实体、状态机和数据流转",
    sections: [
      {
        id: "entities",
        title: "实体定义",
        required: true,
        placeholder: "定义核心数据实体...",
        aiPrompt: "列出核心业务实体，每个实体包含：字段名称、字段类型、是否必填、业务说明"
      },
      {
        id: "state-machine",
        title: "状态机",
        required: true,
        placeholder: "描述业务状态流转...",
        aiPrompt: "绘制状态流转图，包含：所有状态、状态间的转换条件、异常状态处理"
      },
      {
        id: "data-flow",
        title: "数据流转",
        required: false,
        placeholder: "描述数据在各系统的流转...",
        aiPrompt: "描述数据在不同系统/模块间的流转关系"
      }
    ],
    tips: [
      "实体设计要考虑扩展性",
      "状态机要覆盖所有可能的状态",
      "敏感数据要特别标注"
    ],
    medicalNotes: [
      "患者敏感信息需脱敏存储",
      "操作日志需完整保留"
    ]
  },
  {
    id: "compliance",
    number: 6,
    title: "合规要求",
    icon: "⚖️",
    description: "医疗合规、等保要求、多院区适配",
    sections: [
      {
        id: "medical-compliance",
        title: "医疗合规",
        required: true,
        placeholder: "描述医疗行业合规要求...",
        aiPrompt: "列出适用的医疗法规要求，如《医疗机构管理条例》《电子病历应用管理规范》等"
      },
      {
        id: "security-level",
        title: "等保三级",
        required: true,
        placeholder: "描述等保三级要求...",
        aiPrompt: "列出等保三级相关要求，包括：身份鉴别、访问控制、安全审计、数据安全等"
      },
      {
        id: "multi-site",
        title: "多院区适配",
        required: false,
        placeholder: "描述多院区差异...",
        aiPrompt: "如有多个院区，列出各院区的差异化要求（政策、流程、收费标准等）"
      },
      {
        id: "privacy-protection",
        title: "隐私保护",
        required: true,
        placeholder: "描述患者隐私保护措施...",
        aiPrompt: "说明患者隐私保护措施，包括：数据脱敏、访问控制、授权机制等"
      }
    ],
    tips: [
      "合规要求要有法规依据",
      "安全措施要与风险等级匹配",
      "多院区差异要明确标注"
    ],
    medicalNotes: [
      "这是医疗项目最核心的章节",
      "必须得到医务科确认",
      "建议提前与合规部门沟通"
    ]
  },
  {
    id: "analytics",
    number: 7,
    title: "数据埋点",
    icon: "📈",
    description: "定义核心指标、埋点事件和数据看板",
    sections: [
      {
        id: "core-metrics",
        title: "核心指标",
        required: true,
        placeholder: "定义业务核心指标...",
        aiPrompt: "定义3-5个核心业务指标，包含：指标名称、计算公式、目标值、采集方式"
      },
      {
        id: "tracking-events",
        title: "埋点事件",
        required: true,
        placeholder: "定义埋点事件...",
        aiPrompt: "列出关键埋点事件，每个事件包含：事件名称、触发时机、事件属性"
      },
      {
        id: "dashboard",
        title: "数据看板",
        required: false,
        placeholder: "描述数据看板设计...",
        aiPrompt: "描述数据看板的指标展示方式，包括：实时指标、趋势图表、对比分析等"
      }
    ],
    tips: [
      "指标要与第1章的成功指标对应",
      "埋点要覆盖核心业务流程",
      "避免过度埋点，聚焦关键数据"
    ],
    medicalNotes: [
      "医疗数据埋点需符合隐私规范",
      "统计分析不能关联个人身份"
    ]
  },
  {
    id: "milestones",
    number: 8,
    title: "里程碑",
    icon: "🚩",
    description: "项目时间规划和分阶段交付",
    sections: [
      {
        id: "phases",
        title: "阶段划分",
        required: true,
        placeholder: "描述项目阶段...",
        aiPrompt: "将项目划分为2-4个阶段（MVP/优化/扩展），每个阶段包含：目标、功能范围、时间周期"
      },
      {
        id: "timeline",
        title: "时间计划",
        required: true,
        placeholder: "描述各阶段时间安排...",
        aiPrompt: "为每个阶段制定详细的时间计划，包含：关键任务、交付物、验收标准"
      },
      {
        id: "risks",
        title: "风险与应对",
        required: true,
        placeholder: "识别项目风险...",
        aiPrompt: "识别项目主要风险，每个风险包含：风险描述、发生概率、影响程度、应对措施"
      }
    ],
    tips: [
      "MVP阶段要聚焦核心功能",
      "预留缓冲时间应对变更",
      "风险要实际可执行"
    ],
    medicalNotes: [
      "医疗项目上线需考虑审批时间",
      "建议先小范围试点再推广"
    ]
  }
];

// 章节依赖关系
export const CHAPTER_DEPENDENCIES: Record<string, string[]> = {
  "user-stories": ["background"],
  "business-flow": ["user-stories"],
  "functional-specs": ["business-flow"],
  "data-requirements": ["functional-specs"],
  "compliance": ["functional-specs"],
  "analytics": ["background", "functional-specs"],
  "milestones": ["functional-specs", "compliance"]
};

// 章节完成检查清单
export function getChapterChecklist(chapterId: string): string[] {
  const checklists: Record<string, string[]> = {
    background: [
      "□ 痛点是否有量化数据支撑",
      "□ 成功指标是否符合SMART原则",
      "□ 是否避免了技术解决方案描述"
    ],
    "user-stories": [
      "□ 是否覆盖了主要用户角色",
      "□ 用户故事是否有明确的验收标准",
      "□ 优先级划分是否合理"
    ],
    "business-flow": [
      "□ 主流程是否完整（从起点到终点）",
      "□ 异常场景是否有处理方案",
      "□ 各环节的参与者是否明确"
    ],
    "functional-specs": [
      "□ 功能描述是否使用了业务语言（非技术语言）",
      "□ 是否标注了功能优先级",
      "□ 输入输出和校验规则是否清晰"
    ],
    "data-requirements": [
      "□ 实体字段是否完整",
      "□ 状态机是否覆盖了所有状态",
      "□ 敏感数据是否特别标注"
    ],
    compliance: [
      "□ 医疗合规是否有法规依据",
      "□ 安全措施是否与风险等级匹配",
      "□ 多院区差异是否明确标注"
    ],
    analytics: [
      "□ 指标是否与第1章成功指标对应",
      "□ 埋点是否覆盖核心业务流程",
      "□ 数据采集是否符合隐私规范"
    ],
    milestones: [
      "□ MVP阶段是否聚焦核心功能",
      "□ 时间计划是否预留了缓冲",
      "□ 风险应对措施是否可执行"
    ]
  };
  return checklists[chapterId] || [];
}

// 获取下一章建议
export function getNextChapterRecommendation(currentChapter: number): string {
  const recommendations: Record<number, string> = {
    1: "建议先完成用户调研，确保痛点分析有数据支撑",
    2: "建议与业务方确认用户画像的准确性",
    3: "建议绘制流程图辅助说明",
    4: "建议配合原型图一起评审",
    5: "建议与开发对齐实体设计",
    6: "建议提前与医务科/合规部门沟通",
    7: "建议与数据团队确认埋点方案可行性",
    8: "建议与项目管理对齐资源和时间"
  };
  return recommendations[currentChapter] || "";
}

export default PRD_FRAMEWORK;
