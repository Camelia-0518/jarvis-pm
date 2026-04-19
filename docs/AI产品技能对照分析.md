---
title: Jarvis PM - AI产品经理7项技能对照分析
date: 2026-04-12
type: analysis
project: jarvis-pm
---

# Jarvis PM - AI产品经理7项技能对照分析

> 📊 **分析目的**：对照「林木聊AI」提出的AI产品经理7项核心技能，评估Jarvis PM项目的覆盖度，找出优势和改进空间。

---

## 📈 总体评估雷达图

```
                    需求判断 (7/10)
                         ▲
                        /|\
                       / | \
                      /  |  \
         评测能力 ◄───●───┼───●───► 上下文设计
           (4/10)      \  |  /      (7/10)
                        \ | /
                         \|/
          ┌───────────────┼───────────────┐
          │      RAG策略 (5/10)          │
          └───────────────┼───────────────┘
                         /|\
                        / | \
                       /  |  \
         Agent设计 ◄──●───┼───●───► 产品方案
           (9/10)       \ | /        (8/10)
                        \|/
                         ▼
                    Web Coding (9/10)
```

**平均分**: 7.0/10

---

## 📋 逐项对照分析

### 1️⃣ 需求判断能力 (7/10) ⭐⭐⭐⭐

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| 问题识别 | 精准定位PRD撰写痛点 | ✅ 优秀 |
| AI适用性判断 | 明确用AI解决文档生成场景 | ✅ 合理 |
| 场景边界 | 专注PM专属场景，回避通用项目管理 | ✅ 清晰 |
| 竞品差异化 | 与Notion/飞书形成差异化 | ✅ 明确 |

**优势**:
- ✅ **痛点抓得准**：PRD撰写2-3天 → 10分钟，量化价值清晰
- ✅ **场景边界清晰**：不做通用项目管理，专注PM专属场景
- ✅ **差异化明确**：AI-First设计 vs 传统工具的AI附加功能

**改进建议**:
```diff
+ 增加「需求复杂度评估」功能
  - 用户输入需求后，AI判断复杂度（简单/中等/复杂）
  - 根据复杂度推荐不同的生成策略
  - 示例：简单需求用单轮生成，复杂需求用多轮对话

+ 增加「AI适用性提醒」
  - 当用户描述的需求不适合AI生成时，给出提示
  - 示例：过于创新的0-1产品，建议先人工梳理核心价值
```

---

### 2️⃣ 评测能力 (4/10) ⚠️ 重点补强

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| 评测数据集 | ❌ 未提及 | 缺失 |
| 评测指标 | ⚠️ 基础质量检查规则 | 初级 |
| 人工评测流程 | ❌ 未设计 | 缺失 |
| A/B测试 | ❌ 未设计 | 缺失 |
| 持续监控 | ⚠️ 用户采纳率统计 | 基础 |

**核心问题**:
> AI生成质量不稳定是AI产品的最大风险，但当前评测体系薄弱。

**改进方案** (高优先级):

#### 2.1 建立PRD生成质量评测集
```yaml
# 评测数据集结构
evaluation_sets:
  - name: "医疗PRD评测集"
    cases: 50
    scenarios:
      - 简单功能：病案复印申请
      - 复杂流程：多院区预约系统
      - 合规重点：涉及患者隐私的功能
      - 边界情况：极端复杂的业务流程
    
  - name: "电商PRD评测集"
    cases: 30
    
  - name: "SaaS PRD评测集"
    cases: 30
```

#### 2.2 定义评测指标体系
```typescript
// PRD生成质量评分维度
interface PRDQualityMetrics {
  // 1. 完整性 (30%)
  completeness: {
    hasBackground: boolean;      // 是否有背景说明
    hasUserStories: boolean;     // 是否有用户故事
    hasAcceptanceCriteria: boolean; // 是否有验收标准
    hasSuccessMetrics: boolean;  // 是否有成功指标
    score: number; // 0-100
  };
  
  // 2. 准确性 (25%)
  accuracy: {
    requirementUnderstanding: number; // 需求理解准确度
    logicConsistency: number;         // 逻辑一致性
    industryTerminology: number;      // 行业术语准确性
    score: number;
  };
  
  // 3. 可用性 (25%)
  usability: {
    clarity: number;           // 清晰度
    actionability: number;     // 可执行性
    developerFriendly: number; // 开发友好度
    score: number;
  };
  
  // 4. 合规性 (20%) - 医疗行业
  compliance: {
    privacyProtection: boolean; // 隐私保护
    dataSecurity: boolean;      // 数据安全
    medicalRegulations: boolean; // 医疗规范
    score: number;
  };
  
  overallScore: number; // 加权总分
}
```

#### 2.3 设计A/B测试机制
```typescript
// A/B测试：不同Prompt策略的效果对比
interface PromptABTest {
  testId: string;
  hypothesis: string; // 假设：新Prompt能提升用户故事质量
  
  variantA: {
    name: "Control";
    promptTemplate: string;
  };
  
  variantB: {
    name: "Treatment";
    promptTemplate: string; // 优化后的模板
  };
  
  metrics: {
    primary: "userStoryQualityScore"; // 主要指标
    secondary: ["completionRate", "editCount", "timeSpent"];
  };
  
  sampleSize: number; // 每组100个PRD
  duration: "2_weeks";
}
```

#### 2.4 用户反馈闭环
```typescript
// 用户反馈收集
interface UserFeedback {
  prdId: string;
  ratings: {
    overall: 1-5;           // 整体满意度
    accuracy: 1-5;          // 准确度
    usefulness: 1-5;        // 有用性
  };
  
  // 具体反馈
  feedback: {
    whatWorked: string;     // 哪些部分好用
    whatFailed: string;     // 哪些部分不对
    suggestions: string;    // 改进建议
  };
  
  // 自动关联
  generatedBy: string;      // 使用的模型版本
  promptVersion: string;    // Prompt版本
  timestamp: Date;
}
```

---

### 3️⃣ 上下文设计能力 (7/10) ⭐⭐⭐⭐

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| Prompt优化层 | ✅ 有设计 | 优秀 |
| 意图识别 | ✅ 有设计 | 良好 |
| 上下文加载 | ✅ 有Context Manager | 良好 |
| 多轮对话记忆 | ⚠️ 基础设计 | 待完善 |

**优势**:
- ✅ **Prompt Optimizer**：将口语化输入转为结构化Prompt
- ✅ **Context Manager**：加载项目上下文、历史对话
- ✅ **意图识别**：识别写PRD/准备评审/生成报告等不同意图

**改进建议**:
```diff
+ 增强多轮对话上下文管理
  - 长对话自动压缩（20轮后保留决策+待办+问题）
  - 对话分支管理（支持"回到刚才那个方案"）
  
+ 项目DNA继承
  - 新项目自动继承历史项目的优秀PRD风格
  - 个人写作风格学习（用户常用表达方式）
  
+ 上下文窗口优化
  - 自动选择最相关的历史PRD片段
  - 向量检索相似需求作为参考
```

---

### 4️⃣ RAG策略能力 (5/10) ⭐⭐⭐

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| 知识库构建 | ⚠️ 提及与Obsidian集成 | 初级 |
| 检索策略 | ❌ 未详细设计 | 缺失 |
| 向量化存储 | ❌ 未提及 | 缺失 |
| 检索增强生成 | ⚠️ 模板匹配 | 基础 |

**核心问题**:
> 当前主要靠模板匹配，缺乏真正的RAG能力。

**改进方案**:

#### 4.1 构建产品知识库
```yaml
# 知识库架构
knowledge_base:
  # 1. 行业知识
  industry_knowledge:
    - 医疗信息化术语库
    - 等保三级合规要求
    - 多院区管理规范
    
  # 2. 项目历史
  project_history:
    - 历史PRD文档（向量化存储）
    - 评审反馈记录
    - 成功案例拆解
    
  # 3. 用户偏好
  user_preferences:
    - 个人写作风格
    - 常用表达方式
    - 关注重点（偏技术/偏业务）
    
  # 4. 最佳实践
  best_practices:
    - PRD优秀范例
    - 用户故事模板
    - 验收标准写法
```

#### 4.2 检索策略设计
```typescript
// RAG检索流程
interface RAGPipeline {
  // Step 1: 查询理解
  queryUnderstanding: {
    extractKeywords: string[];      // 提取关键词
    identifyIntent: string;         // 识别意图
    detectIndustry: string;         // 检测行业
  };
  
  // Step 2: 多路召回
  retrieval: {
    // 向量检索：找语义相似的PRD
    semanticSearch: {
      index: "prd_embeddings";
      topK: 5;
    };
    
    // 关键词检索：找包含特定术语的文档
    keywordSearch: {
      fields: ["title", "content", "tags"];
      topK: 5;
    };
    
    // 模板匹配：找适用的模板
    templateMatch: {
      industry: string;
      complexity: string;
    };
  };
  
  // Step 3: 重排序
  reranking: {
    // 综合考虑相关性、时效性、用户偏好
    factors: {
      semanticRelevance: 0.4;
      keywordMatch: 0.3;
      userPreference: 0.2;
      recency: 0.1;
    };
  };
  
  // Step 4: 上下文组装
  contextAssembly: {
    maxTokens: 2000;
    priorityOrder: ["模板", "相似PRD", "行业知识"];
  };
}
```

---

### 5️⃣ Agent设计与任务编排 (9/10) ⭐⭐⭐⭐⭐

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| Agent角色设计 | ✅ 5个AI角色 | 优秀 |
| 可视化编排 | ✅ React Flow画布 | 优秀 |
| 决策透明 | ✅ 决策日志、置信度 | 优秀 |
| 冲突检测 | ✅ Agent间分歧识别 | 良好 |
| 任务路由 | ✅ Intent Classifier | 良好 |

**优势** (这是项目的核心竞争力):
- ✅ **Multi-Agent架构**：CEO/Designer/Eng Manager/QA Engineer/Orchestrator
- ✅ **可视化编排**：React Flow拖拽式工作流画布
- ✅ **决策透明**：Agent决策日志、置信度评分
- ✅ **冲突检测**：自动识别Agent间分歧

**微调建议**:
```diff
+ 增加Agent协作反馈机制
  - Agent生成内容后，其他Agent自动Review
  - 模拟评审会议，提前发现风险
  
+ 自定义Agent角色
  - 允许用户创建自己的Agent（如"医疗合规专家"）
  - Agent市场，分享优秀Agent配置
```

---

### 6️⃣ 产品方案能力 (8/10) ⭐⭐⭐⭐

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| 需求到落地 | ✅ 完整PRD结构 | 优秀 |
| 全流程覆盖 | ✅ 从撰写到评审到站会 | 优秀 |
| 行业适配 | ✅ 医疗/电商/SaaS模板 | 良好 |
| 成功指标 | ✅ 定义清晰 | 良好 |
| 风险评估 | ✅ 有风险评估章节 | 良好 |

**优势**:
- ✅ **完整PRD结构**：8章标准结构，覆盖完整
- ✅ **全流程覆盖**：撰写 → 评审 → 站会，全链路
- ✅ **行业模板**：医疗/电商/SaaS差异化支持
- ✅ **成功指标**：用户指标/产品指标/技术指标三层

**改进建议**:
```diff
+ 增加需求验证环节
  - PRD生成后，自动推荐验证方式（用户访谈/原型测试）
  - 提供MVP建议（哪些功能可以砍到MVP）
  
+ 增加技术可行性评估
  - AI评估技术实现难度
  - 推荐技术方案和估算工期
  
+ 增加ROI计算
  - 基于功能点自动估算开发成本
  - 结合预期收益计算ROI
```

---

### 7️⃣ Web Coding能力 (9/10) ⭐⭐⭐⭐⭐

**现状评估**:
| 维度 | 项目表现 | 评分 |
|:-----|:---------|:----:|
| 技术选型 | ✅ Next.js + FastAPI + PostgreSQL | 优秀 |
| 架构设计 | ✅ 前后端分离，微服务思想 | 优秀 |
| 快速验证 | ✅ 项目已启动，有原型 | 优秀 |
| AI集成 | ✅ Claude/Kimi API集成 | 良好 |
| 实时协作 | ✅ WebSocket设计 | 良好 |

**优势**:
- ✅ **技术栈成熟**：Next.js 15 + React 19 + FastAPI + PostgreSQL
- ✅ **AI原生**：深度集成Claude API和Kimi API
- ✅ **实时协作**：WebSocket实现多用户实时编辑
- ✅ **已落地**：不是停留在PRD，已有可运行的代码

**改进建议**:
```diff
+ 增加快速原型导出
  - 根据PRD自动生成可点击的原型（HTML/Markdown）
  - 支持直接部署到Vercel预览
  
+ 增加代码生成能力
  - 根据PRD生成前端组件代码（React/Vue）
  - 生成API接口定义（OpenAPI/Swagger）
```

---

## 🎯 优先级改进路线图

### 立即执行 (P0) - 评测能力建设
```
Week 1-2: 建立评测数据集
  - 收集50个医疗PRD案例
  - 定义质量评分标准
  - 建立人工标注流程

Week 3-4: 实现评测系统
  - 开发自动评分功能
  - 集成到AI生成流程
  - 低质量内容自动标记

Week 5-6: 用户反馈闭环
  - 增加PRD满意度评分
  - 收集具体改进建议
  - 建立反馈驱动的优化机制
```

### 短期优化 (P1) - RAG能力增强
```
Week 7-10: 构建知识库
  - 历史PRD向量化存储
  - 行业知识库建设
  - 检索策略优化

Week 11-12: 上下文优化
  - 多轮对话压缩
  - 项目DNA继承
  - 个人风格学习
```

### 中期增强 (P2) - 产品完整性
```
Month 4-6: 方案能力增强
  - 需求验证建议
  - 技术可行性评估
  - ROI自动计算
  
Month 7-9: 生态建设
  - Agent市场
  - 模板市场
  - 最佳实践库
```

---

## 📊 改进前后对比

| 维度 | 当前 | 目标 | 提升 |
|:-----|:----:|:----:|:----:|
| 需求判断 | 7/10 | 8/10 | +1 |
| 评测能力 | 4/10 | 8/10 | +4 ⭐ |
| 上下文设计 | 7/10 | 9/10 | +2 |
| RAG策略 | 5/10 | 8/10 | +3 ⭐ |
| Agent设计 | 9/10 | 9/10 | 0 |
| 产品方案 | 8/10 | 9/10 | +1 |
| Web Coding | 9/10 | 9/10 | 0 |
| **平均分** | **7.0** | **8.6** | **+1.6** |

---

## 💡 关键洞察

### 1. 评测能力是最大短板
> AI产品最大的风险是「质量不稳定」，但当前缺乏系统的评测机制。
> 
> **建议**：把评测能力建设放在最高优先级，建立从数据集到A/B测试的完整体系。

### 2. RAG能力决定上限
> 当前的模板匹配方式限制了生成质量的 ceiling。
> 
> **建议**：构建真正的RAG系统，让AI能学习和参考历史优秀PRD。

### 3. Agent设计是核心竞争力
> Multi-Agent架构已经领先大部分竞品，要持续保持优势。
> 
> **建议**：建立Agent市场，让用户能自定义和分享Agent。

### 4. 从「能用」到「好用」
> 当前实现了基础功能，但要做到行业领先还需要在评测和RAG上投入。
> 
> **建议**：不要急于增加功能，先做好生成质量的稳定性和一致性。

---

## 🔗 关联文档

- [[AI产品经理7项核心技能]] - 技能标准原文
- [[A-PRD设计]] - 项目PRD文档
- [[C-竞品分析]] - 竞品分析报告
- [[技术架构]] - 技术实现细节

---

*分析日期: 2026-04-12*
*分析师: AI助手*
*版本: v1.0*
