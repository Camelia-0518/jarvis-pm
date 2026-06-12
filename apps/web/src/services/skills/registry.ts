// 技能注册表
// 注册所有可用的技能定义

import type {
  SkillDefinition,
  SkillId,
  SkillFilterOptions,
  RequirementAnalysisOutput,
  PRDOutput,
  TechArchitectureOutput,
  UXDesignOutput,
  BusinessModelOutput,
  MilestonePlanOutput,
  MedicalReviewOutput,
  ComplianceCheckOutput,
  MultiBranchAnalysisOutput,
} from '@/types/skill';
import type { AgentRole } from '@/types/agent';

// 所有技能定义
export const SKILL_DEFINITIONS: SkillDefinition[] = [
  // ========== PM 技能 ==========
  {
    id: 'requirement-analysis',
    name: '需求分析',
    description: '深度分析产品需求，输出用户画像、功能列表、用户故事和成功指标',
    agentRole: 'ceo',
    category: 'analysis',
    icon: '🔍',
    tags: ['需求', '分析', '产品'],
    parameters: [
      {
        name: 'idea',
        label: '产品想法',
        type: 'textarea',
        description: '描述你的产品想法，包括要解决什么问题、目标用户是谁',
        required: true,
        placeholder: '例如：一个帮助医院患者在线申请病历复印的系统...',
      },
      {
        name: 'targetUsers',
        label: '目标用户',
        type: 'string',
        description: '目标用户群体描述',
        required: true,
        placeholder: '例如：医院患者、病案室工作人员',
      },
      {
        name: 'industry',
        label: '所属行业',
        type: 'select',
        description: '产品所属行业',
        required: true,
        options: [
          { label: '医疗信息化', value: 'medical' },
          { label: '金融科技', value: 'fintech' },
          { label: '电子商务', value: 'ecommerce' },
          { label: '教育科技', value: 'edtech' },
          { label: '企业服务', value: 'enterprise' },
          { label: '其他', value: 'other' },
        ],
        defaultValue: 'medical',
      },
      {
        name: 'constraints',
        label: '约束条件',
        type: 'textarea',
        description: '任何已知的约束条件（预算、时间、技术限制等）',
        required: false,
        placeholder: '例如：需要在3个月内上线，预算50万...',
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        productOneLiner: { type: 'string' },
        userPersona: {
          type: 'object',
          properties: {
            who: { type: 'string' },
            painPoints: { type: 'string' },
            currentSolutions: { type: 'string' },
            whyNewProduct: { type: 'string' },
          },
        },
        featureList: {
          type: 'object',
          properties: {
            p0: { type: 'array', items: { type: 'string' } },
            p1: { type: 'array', items: { type: 'string' } },
            p2: { type: 'array', items: { type: 'string' } },
          },
        },
        userStories: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'string' },
              role: { type: 'string' },
              action: { type: 'string' },
              benefit: { type: 'string' },
              priority: { type: 'string', enum: ['high', 'medium', 'low'] },
            },
          },
        },
        successMetrics: {
          type: 'object',
          properties: {
            northStar: { type: 'string' },
            metrics: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  name: { type: 'string' },
                  target: { type: 'string' },
                  timeFrame: { type: 'string' },
                },
              },
            },
          },
        },
      },
      required: ['productOneLiner', 'userPersona', 'featureList', 'userStories', 'successMetrics'],
    },
    examples: [
      {
        id: 'medical-record-copy',
        name: '病案复印系统',
        description: '医院病历在线申请复印系统',
        inputs: {
          idea: '一个帮助患者在线申请病历复印并快递到家的系统',
          targetUsers: '医院患者、病案室工作人员',
          industry: 'medical',
        },
        outputPreview: '产品一句话描述：一个帮助患者在线申请病案复印并快递到家的医疗服务平台...',
      },
    ],
  },

  {
    id: 'write-prd',
    name: '撰写 PRD',
    description: '根据需求分析结果生成完整的产品需求文档',
    agentRole: 'ceo',
    category: 'design',
    icon: '📝',
    tags: ['PRD', '文档', '需求'],
    parameters: [
      {
        name: 'requirementAnalysis',
        label: '需求分析结果',
        type: 'textarea',
        description: '需求分析的输出内容（JSON格式或文本描述）',
        required: true,
        placeholder: '粘贴需求分析的完整输出...',
      },
      {
        name: 'template',
        label: 'PRD 模板',
        type: 'select',
        description: '选择PRD模板风格',
        required: true,
        options: [
          { label: '标准PRD', value: 'standard' },
          { label: '敏捷用户故事', value: 'agile' },
          { label: '医疗行业专用', value: 'medical' },
        ],
        defaultValue: 'standard',
      },
      {
        name: 'detailLevel',
        label: '详细程度',
        type: 'select',
        description: 'PRD 的详细程度',
        required: true,
        options: [
          { label: '精简版', value: 'concise' },
          { label: '标准版', value: 'standard' },
          { label: '详细版', value: 'detailed' },
        ],
        defaultValue: 'standard',
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        title: { type: 'string' },
        overview: { type: 'string' },
        goals: { type: 'array', items: { type: 'string' } },
        userPersonas: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              description: { type: 'string' },
              needs: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        features: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'string' },
              name: { type: 'string' },
              description: { type: 'string' },
              priority: { type: 'string', enum: ['p0', 'p1', 'p2'] },
              acceptanceCriteria: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        userStories: { type: 'array', items: { type: 'string' } },
        nonFunctionalRequirements: {
          type: 'object',
          properties: {
            performance: { type: 'array', items: { type: 'string' } },
            security: { type: 'array', items: { type: 'string' } },
            compliance: { type: 'array', items: { type: 'string' } },
          },
        },
        timeline: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              phase: { type: 'string' },
              duration: { type: 'string' },
              deliverables: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },

  // ========== 工程经理技能 ==========
  {
    id: 'tech-architecture',
    name: '技术架构设计',
    description: '根据PRD生成完整的技术架构方案，包括技术栈、组件设计、数据模型、API设计',
    agentRole: 'engManager',
    category: 'development',
    icon: '🏗️',
    tags: ['架构', '技术', '设计'],
    parameters: [
      {
        name: 'prd',
        label: 'PRD 文档',
        type: 'textarea',
        description: '产品需求文档内容',
        required: true,
        placeholder: '粘贴PRD的完整内容...',
      },
      {
        name: 'techStackPreference',
        label: '技术栈偏好',
        type: 'select',
        description: '偏好的技术栈',
        required: false,
        options: [
          { label: 'React + Node.js', value: 'react-node' },
          { label: 'Vue + Spring Boot', value: 'vue-java' },
          { label: 'Next.js + Python', value: 'next-python' },
          { label: 'Angular + .NET', value: 'angular-dotnet' },
          { label: '不限', value: 'flexible' },
        ],
        defaultValue: 'flexible',
      },
      {
        name: 'scalability',
        label: '可扩展性要求',
        type: 'select',
        description: '系统的可扩展性要求',
        required: true,
        options: [
          { label: '小规模（<1000用户）', value: 'small' },
          { label: '中等规模（1万-10万用户）', value: 'medium' },
          { label: '大规模（>10万用户）', value: 'large' },
          { label: '企业级', value: 'enterprise' },
        ],
        defaultValue: 'medium',
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        overview: { type: 'string' },
        architectureDiagram: { type: 'string' },
        techStack: {
          type: 'object',
          properties: {
            frontend: { type: 'array', items: { type: 'string' } },
            backend: { type: 'array', items: { type: 'string' } },
            database: { type: 'array', items: { type: 'string' } },
            infrastructure: { type: 'array', items: { type: 'string' } },
          },
        },
        components: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              description: { type: 'string' },
              responsibilities: { type: 'array', items: { type: 'string' } },
              dependencies: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        dataModel: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              entity: { type: 'string' },
              fields: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    name: { type: 'string' },
                    type: { type: 'string' },
                    description: { type: 'string' },
                  },
                },
              },
            },
          },
        },
        apiDesign: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              endpoint: { type: 'string' },
              method: { type: 'string' },
              description: { type: 'string' },
              request: { type: 'object' },
              response: { type: 'object' },
            },
          },
        },
        securityConsiderations: { type: 'array', items: { type: 'string' } },
      },
    },
  },

  {
    id: 'milestone-plan',
    name: '里程碑规划',
    description: '根据PRD和技术架构制定详细的项目里程碑计划',
    agentRole: 'engManager',
    category: 'planning',
    icon: '📅',
    tags: ['规划', '里程碑', '项目管理'],
    parameters: [
      {
        name: 'prd',
        label: 'PRD 文档',
        type: 'textarea',
        description: '产品需求文档',
        required: true,
      },
      {
        name: 'architecture',
        label: '技术架构',
        type: 'textarea',
        description: '技术架构设计文档（可选）',
        required: false,
      },
      {
        name: 'teamSize',
        label: '团队规模',
        type: 'select',
        description: '项目团队规模',
        required: true,
        options: [
          { label: '小型团队（2-3人）', value: 'small' },
          { label: '中型团队（4-7人）', value: 'medium' },
          { label: '大型团队（8-15人）', value: 'large' },
          { label: '超大型团队（>15人）', value: 'xlarge' },
        ],
        defaultValue: 'medium',
      },
      {
        name: 'deadline',
        label: '目标截止日期',
        type: 'string',
        description: '项目目标截止日期（如：2026-06-30）',
        required: false,
        placeholder: '2026-06-30',
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        overview: { type: 'string' },
        phases: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              duration: { type: 'string' },
              startDate: { type: 'string' },
              endDate: { type: 'string' },
              goals: { type: 'array', items: { type: 'string' } },
              deliverables: { type: 'array', items: { type: 'string' } },
              dependencies: { type: 'array', items: { type: 'string' } },
              risks: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    risk: { type: 'string' },
                    mitigation: { type: 'string' },
                  },
                },
              },
            },
          },
        },
        resources: {
          type: 'object',
          properties: {
            team: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  role: { type: 'string' },
                  count: { type: 'number' },
                  responsibilities: { type: 'array', items: { type: 'string' } },
                },
              },
            },
            tools: { type: 'array', items: { type: 'string' } },
            budget: { type: 'string' },
          },
        },
        criticalPath: { type: 'array', items: { type: 'string' } },
        milestones: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              date: { type: 'string' },
              criteria: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },

  // ========== 设计师技能 ==========
  {
    id: 'ux-design',
    name: 'UX 设计',
    description: '生成完整的UX设计方案，包括用户流程、线框图、设计系统和交互模式',
    agentRole: 'designer',
    category: 'design',
    icon: '🎨',
    tags: ['UX', '设计', '用户体验'],
    parameters: [
      {
        name: 'prd',
        label: 'PRD 文档',
        type: 'textarea',
        description: '产品需求文档',
        required: true,
      },
      {
        name: 'platform',
        label: '目标平台',
        type: 'select',
        description: '设计的目标平台',
        required: true,
        options: [
          { label: 'Web 应用', value: 'web' },
          { label: '移动端 App', value: 'mobile-app' },
          { label: '响应式 Web', value: 'responsive' },
          { label: '小程序', value: 'miniprogram' },
          { label: '桌面应用', value: 'desktop' },
        ],
        defaultValue: 'web',
      },
      {
        name: 'designStyle',
        label: '设计风格',
        type: 'select',
        description: 'UI设计风格偏好',
        required: false,
        options: [
          { label: '简洁现代', value: 'modern' },
          { label: '专业商务', value: 'professional' },
          { label: '活泼友好', value: 'friendly' },
          { label: '医疗专业', value: 'medical' },
          { label: '深色主题', value: 'dark' },
        ],
        defaultValue: 'modern',
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        overview: { type: 'string' },
        userFlows: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              steps: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    step: { type: 'number' },
                    screen: { type: 'string' },
                    action: { type: 'string' },
                    outcome: { type: 'string' },
                  },
                },
              },
            },
          },
        },
        wireframes: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              description: { type: 'string' },
              layout: { type: 'string' },
              keyElements: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        designSystem: {
          type: 'object',
          properties: {
            colors: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  name: { type: 'string' },
                  value: { type: 'string' },
                  usage: { type: 'string' },
                },
              },
            },
            typography: {
              type: 'array',
              items: {
                type: 'object',
                properties: {
                  name: { type: 'string' },
                  specs: { type: 'string' },
                },
              },
            },
            components: { type: 'array', items: { type: 'string' } },
          },
        },
        interactionPatterns: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              description: { type: 'string' },
              behavior: { type: 'string' },
            },
          },
        },
      },
    },
  },

  // ========== 商业模式技能 ==========
  {
    id: 'business-model',
    name: '商业模式设计',
    description: '分析并设计产品的商业模式，包括价值主张、收入来源、成本结构等',
    agentRole: 'ceo',
    category: 'analysis',
    icon: '💼',
    tags: ['商业', '模式', '战略'],
    parameters: [
      {
        name: 'productDescription',
        label: '产品描述',
        type: 'textarea',
        description: '产品或服务的详细描述',
        required: true,
      },
      {
        name: 'market',
        label: '目标市场',
        type: 'string',
        description: '目标市场描述',
        required: true,
        placeholder: '例如：国内三甲医院信息化市场',
      },
      {
        name: 'competitors',
        label: '主要竞争对手',
        type: 'textarea',
        description: '主要竞争对手及其优劣势',
        required: false,
        placeholder: '例如：卫宁健康（市场份额大，但价格高）...',
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        valueProposition: { type: 'string' },
        customerSegments: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              segment: { type: 'string' },
              description: { type: 'string' },
              needs: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        revenueStreams: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              stream: { type: 'string' },
              description: { type: 'string' },
              pricing: { type: 'string' },
              projectedRevenue: { type: 'string' },
            },
          },
        },
        costStructure: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              category: { type: 'string' },
              items: { type: 'array', items: { type: 'string' } },
              estimatedCost: { type: 'string' },
            },
          },
        },
        channels: { type: 'array', items: { type: 'string' } },
        keyMetrics: { type: 'array', items: { type: 'string' } },
        competitiveAdvantage: { type: 'string' },
      },
    },
  },

  // ========== 医疗行业专用技能 ==========
  {
    id: 'medical-review',
    name: '医疗业务评审',
    description: '从医疗业务角度评审需求的合理性、合规性和可行性',
    agentRole: 'medical-officer',
    category: 'medical',
    icon: '🏥',
    tags: ['医疗', '评审', '业务'],
    parameters: [
      {
        name: 'requirement',
        label: '需求内容',
        type: 'textarea',
        description: '需求标题和详细描述',
        required: true,
        placeholder: '需求标题：病案复印在线申请\n需求描述：...',
      },
      {
        name: 'featureType',
        label: '功能类型',
        type: 'select',
        description: '医疗功能类型',
        required: true,
        options: [
          { label: '病案管理', value: 'medical-record' },
          { label: '预约挂号', value: 'appointment' },
          { label: '门诊缴费', value: 'payment' },
          { label: '检查检验', value: 'lab' },
          { label: '处方管理', value: 'prescription' },
          { label: '消息推送', value: 'notification' },
          { label: '其他', value: 'other' },
        ],
        defaultValue: 'other',
      },
      {
        name: 'patientData',
        label: '是否涉及患者数据',
        type: 'boolean',
        description: '功能是否涉及患者隐私数据',
        required: true,
        defaultValue: true,
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        summary: { type: 'string' },
        medicalRationality: {
          type: 'object',
          properties: {
            score: { type: 'number' },
            assessment: { type: 'string' },
            concerns: { type: 'array', items: { type: 'string' } },
            recommendations: { type: 'array', items: { type: 'string' } },
          },
        },
        complianceAnalysis: {
          type: 'object',
          properties: {
            applicableRegulations: { type: 'array', items: { type: 'string' } },
            complianceStatus: { type: 'string', enum: ['compliant', 'partial', 'non-compliant'] },
            gaps: { type: 'array', items: { type: 'string' } },
            actions: { type: 'array', items: { type: 'string' } },
          },
        },
        riskAssessment: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              risk: { type: 'string' },
              level: { type: 'string', enum: ['high', 'medium', 'low'] },
              impact: { type: 'string' },
              mitigation: { type: 'string' },
            },
          },
        },
        approvalRecommendation: { type: 'string', enum: ['approve', 'approve-with-conditions', 'reject'] },
        conditions: { type: 'array', items: { type: 'string' } },
      },
    },
  },

  {
    id: 'compliance-check',
    name: '合规检查',
    description: '检查产品设计是否符合医疗行业法规和合规要求（等保三级、数据安全等）',
    agentRole: 'compliance-officer',
    category: 'medical',
    icon: '✅',
    tags: ['合规', '法规', '安全'],
    parameters: [
      {
        name: 'prd',
        label: 'PRD 文档',
        type: 'textarea',
        description: '产品需求文档',
        required: true,
      },
      {
        name: 'complianceLevel',
        label: '合规等级要求',
        type: 'select',
        description: '需要满足的合规等级',
        required: true,
        options: [
          { label: '等保二级', value: 'level2' },
          { label: '等保三级', value: 'level3' },
          { label: '等保四级', value: 'level4' },
          { label: '三甲医院标准', value: 'class3-hospital' },
          { label: '通用合规', value: 'general' },
        ],
        defaultValue: 'level3',
      },
      {
        name: 'dataTypes',
        label: '涉及数据类型',
        type: 'array',
        description: '产品涉及的数据类型',
        required: true,
        defaultValue: [],
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        summary: { type: 'string' },
        overallStatus: { type: 'string', enum: ['pass', 'fail', 'partial'] },
        score: { type: 'number' },
        categories: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              status: { type: 'string', enum: ['pass', 'fail', 'partial'] },
              items: {
                type: 'array',
                items: {
                  type: 'object',
                  properties: {
                    requirement: { type: 'string' },
                    status: { type: 'string', enum: ['pass', 'fail', 'na'] },
                    evidence: { type: 'string' },
                    remediation: { type: 'string' },
                  },
                },
              },
            },
          },
        },
        criticalIssues: { type: 'array', items: { type: 'string' } },
        recommendations: { type: 'array', items: { type: 'string' } },
        checklist: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              item: { type: 'string' },
              checked: { type: 'boolean' },
              category: { type: 'string' },
            },
          },
        },
      },
    },
  },

  {
    id: 'multi-branch-analysis',
    name: '多院区需求分析',
    description: '分析多院区场景下的需求适配性，识别标准功能和分院特性',
    agentRole: 'multi-branch-pm',
    category: 'medical',
    icon: '🏢',
    tags: ['多院区', '适配', '分析'],
    parameters: [
      {
        name: 'requirement',
        label: '需求内容',
        type: 'textarea',
        description: '需求详细描述',
        required: true,
      },
      {
        name: 'branches',
        label: '涉及院区',
        type: 'textarea',
        description: '涉及的院区列表及其地区',
        required: true,
        placeholder: '例如：\n- 江西妇幼保健院（南昌）\n- 临夏妇幼保健院（甘肃）',
      },
      {
        name: 'standardFeatures',
        label: '预期标准功能',
        type: 'textarea',
        description: '预期作为标准功能的部分',
        required: false,
      },
    ],
    outputSchema: {
      type: 'object',
      properties: {
        summary: { type: 'string' },
        standardFeatures: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              feature: { type: 'string' },
              description: { type: 'string' },
              applicableBranches: { type: 'array', items: { type: 'string' } },
            },
          },
        },
        branchSpecificRequirements: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              branch: { type: 'string' },
              location: { type: 'string' },
              specificPolicies: { type: 'array', items: { type: 'string' } },
              requiredAdaptations: { type: 'array', items: { type: 'string' } },
              estimatedEffort: { type: 'string' },
            },
          },
        },
        dataSynchronization: {
          type: 'object',
          properties: {
            strategy: { type: 'string' },
            syncFrequency: { type: 'string' },
            conflictResolution: { type: 'string' },
          },
        },
        deploymentStrategy: { type: 'string' },
        riskAssessment: { type: 'array', items: { type: 'string' } },
      },
    },
  },
];

// 技能注册表类
class SkillRegistry {
  private skills: Map<string, SkillDefinition> = new Map();

  constructor() {
    // 初始化注册所有技能
    SKILL_DEFINITIONS.forEach((skill) => {
      this.skills.set(skill.id, skill);
    });
  }

  // 动态设置技能（从后端加载后使用）
  setSkills(skills: SkillDefinition[]) {
    this.skills.clear();
    skills.forEach((skill) => {
      this.skills.set(skill.id, skill);
    });
  }

  // 获取所有技能
  getAllSkills(): SkillDefinition[] {
    return Array.from(this.skills.values());
  }

  // 根据ID获取技能
  getSkillById(id: SkillId | string): SkillDefinition | undefined {
    return this.skills.get(id);
  }

  // 根据Agent角色获取技能
  getSkillsByRole(role: AgentRole | string): SkillDefinition[] {
    return this.getAllSkills().filter((skill) => skill.agentRole === role);
  }

  // 根据分类获取技能
  getSkillsByCategory(category: SkillDefinition['category']): SkillDefinition[] {
    return this.getAllSkills().filter((skill) => skill.category === category);
  }

  // 搜索技能
  searchSkills(query: string): SkillDefinition[] {
    const lowerQuery = query.toLowerCase();
    return this.getAllSkills().filter(
      (skill) =>
        skill.name.toLowerCase().includes(lowerQuery) ||
        skill.description.toLowerCase().includes(lowerQuery) ||
        skill.tags?.some((tag) => tag.toLowerCase().includes(lowerQuery))
    );
  }

  // 筛选技能
  filterSkills(options: SkillFilterOptions): SkillDefinition[] {
    let result = this.getAllSkills();

    if (options.category) {
      result = result.filter((skill) => skill.category === options.category);
    }

    if (options.agentRole) {
      result = result.filter((skill) => skill.agentRole === options.agentRole);
    }

    if (options.searchQuery) {
      const lowerQuery = options.searchQuery.toLowerCase();
      result = result.filter(
        (skill) =>
          skill.name.toLowerCase().includes(lowerQuery) ||
          skill.description.toLowerCase().includes(lowerQuery)
      );
    }

    if (options.tags && options.tags.length > 0) {
      result = result.filter((skill) =>
        options.tags!.some((tag) => skill.tags?.includes(tag))
      );
    }

    return result;
  }

  // 获取技能的输出类型（用于类型推断）
  getSkillOutputType<T extends SkillId>(skillId: T): SkillOutputMap[T] | undefined {
    const skill = this.getSkillById(skillId);
    if (!skill) return undefined;

    // 这里返回类型信息，实际使用时由后端返回具体数据
    return undefined as unknown as SkillOutputMap[T];
  }

  // 验证技能输入
  validateSkillInput(skillId: string, inputs: Record<string, unknown>): { valid: boolean; errors: string[] } {
    const skill = this.getSkillById(skillId);
    if (!skill) {
      return { valid: false, errors: [`技能 ${skillId} 不存在`] };
    }

    const errors: string[] = [];

    for (const param of skill.parameters) {
      if (param.required && (inputs[param.name] === undefined || inputs[param.name] === '')) {
        errors.push(`参数 "${param.label}" 是必填项`);
      }
    }

    return { valid: errors.length === 0, errors };
  }

  // 获取技能的默认输入值
  getDefaultInputs(skillId: string): Record<string, unknown> {
    const skill = this.getSkillById(skillId);
    if (!skill) return {};

    const defaults: Record<string, unknown> = {};
    for (const param of skill.parameters) {
      if (param.defaultValue !== undefined) {
        defaults[param.name] = param.defaultValue;
      }
    }

    return defaults;
  }
}

// 技能输出类型映射（用于类型安全）
interface SkillOutputMap {
  'requirement-analysis': RequirementAnalysisOutput;
  'write-prd': PRDOutput;
  'tech-architecture': TechArchitectureOutput;
  'ux-design': UXDesignOutput;
  'business-model': BusinessModelOutput;
  'milestone-plan': MilestonePlanOutput;
  'medical-review': MedicalReviewOutput;
  'compliance-check': ComplianceCheckOutput;
  'multi-branch-analysis': MultiBranchAnalysisOutput;
}

// 从后端加载技能定义，消除前后端重复
export async function loadSkillDefinitionsFromBackend(): Promise<boolean> {
  try {
    const { skillsApi } = await import("@/lib/api");
    const result = await skillsApi.getAll();
    const skills = (result?.skills || []) as unknown as SkillDefinition[];
    if (skills.length > 0) {
      skillRegistry.setSkills(skills);
      return true;
    }
    return false;
  } catch (e) {
    console.error('Failed to load skill definitions from backend:', e);
    return false;
  }
}

// 导出单例实例
export const skillRegistry = new SkillRegistry();

// 导出便捷函数
export const getAllSkills = () => skillRegistry.getAllSkills();
export const getSkillById = (id: SkillId | string) => skillRegistry.getSkillById(id);
export const getSkillsByRole = (role: AgentRole | string) => skillRegistry.getSkillsByRole(role);
export const getSkillsByCategory = (category: SkillDefinition['category']) =>
  skillRegistry.getSkillsByCategory(category);
export const searchSkills = (query: string) => skillRegistry.searchSkills(query);
export const filterSkills = (options: SkillFilterOptions) => skillRegistry.filterSkills(options);
export const validateSkillInput = (skillId: string, inputs: Record<string, unknown>) =>
  skillRegistry.validateSkillInput(skillId, inputs);
export const getDefaultInputs = (skillId: string) => skillRegistry.getDefaultInputs(skillId);

// 技能分类标签
export const SKILL_CATEGORIES: { value: SkillDefinition['category']; label: string; icon: string }[] = [
  { value: 'analysis', label: '分析', icon: '🔍' },
  { value: 'design', label: '设计', icon: '🎨' },
  { value: 'development', label: '开发', icon: '💻' },
  { value: 'review', label: '评审', icon: '👀' },
  { value: 'medical', label: '医疗', icon: '🏥' },
  { value: 'planning', label: '规划', icon: '📅' },
];

// Agent 角色到技能映射
export const AGENT_SKILL_MAP: Record<AgentRole | string, string[]> = {
  ceo: ['requirement-analysis', 'write-prd', 'business-model'],
  designer: ['ux-design'],
  engManager: ['tech-architecture', 'milestone-plan'],
  qaEngineer: [],
  orchestrator: [],
  'medical-officer': ['medical-review'],
  'compliance-officer': ['compliance-check'],
  'multi-branch-pm': ['multi-branch-analysis'],
};
