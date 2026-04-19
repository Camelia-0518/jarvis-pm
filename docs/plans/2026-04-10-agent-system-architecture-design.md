# Jarvis PM Agent 系统架构设计

> 设计日期: 2026-04-10  
> 设计版本: v1.0  
> 设计状态: 已确认

---

## 1. 设计目标

构建一个以 **Kimi Coding API** 为智能核心的 AI 产品经理执行系统，支持 **50+ 专业 Agent**，能够：

- **自动编排任务链** - 智能分解用户意图，调度合适 Agent
- **调用工具执行** - Agent 不只是聊天，能搜索、分析、写文档
- **透明执行过程** - 可查看思考过程、工具调用、中间结果
- **持久化记忆** - 项目历史、知识库、个人偏好三层记忆
- **与 Obsidian 集成** - 输出自动入知识库，可回溯

---

## 2. 架构概览

### 2.1 分层架构图

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)              │
│    /execute /agents /tools /memory       │
└─────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Strategy Layer (战略层)           │
│   ┌─────────────────────────────────┐   │
│   │  Intent Classifier (意图识别)   │   │
│   │  Task Planner (任务规划器)       │   │
│   │  Agent Router (Agent路由器)     │   │
│   └─────────────────────────────────┘   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Tactical Layer (战术层)          │
│   ┌─────────────────────────────────┐   │
│   │      Task Queue (Redis)         │   │
│   │  ┌─────┐ ┌─────┐ ┌─────┐       │   │
│   │  │Task1│ │Task2│ │Task3│  ...   │   │
│   │  └─────┘ └─────┘ └─────┘       │   │
│   └─────────────────────────────────┘   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Execution Layer (执行层)         │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │Agent Pool│  │ Tool Box │            │
│  │(动态加载) │  │(插件化)  │            │
│  │          │  │          │            │
│  │•需求洞察 │  │•web_search│           │
│  │•竞品分析 │  │•crawler  │            │
│  │•PRD撰写  │  │•doc_write│            │
│  │•合规检查 │  │•compliance│           │
│  │...(50+)  │  │•...      │            │
│  └──────────┘  └──────────┘            │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │     Kimi Coding API Client      │   │
│  │   (统一封装，多模型fallback)      │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Memory Layer (记忆层)            │
│   ┌──────────┐  ┌──────────┐           │
│   │ Short-term│  │ Long-term│           │
│   │ (Redis)  │  │(Obsidian/│           │
│   │ 会话状态  │  │ Database)│           │
│   └──────────┘  └──────────┘           │
└─────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 职责 | 关键组件 |
|------|------|----------|
| **API Layer** | 对外接口，接收请求，返回结果 | FastAPI Router |
| **Strategy Layer** | 理解意图，规划任务，路由Agent | IntentClassifier, TaskPlanner, AgentRouter |
| **Tactical Layer** | 任务队列管理，状态追踪 | Redis Queue, Task State Manager |
| **Execution Layer** | Agent执行，工具调用，AI交互 | Agent Pool, Tool Box, Kimi Client |
| **Memory Layer** | 记忆存储和检索 | Redis, Obsidian API, PostgreSQL |

---

## 3. 核心组件设计

### 3.1 Agent 定义

Agent 不是 UI 角色，而是**能执行特定任务的 AI 工作单元**。

```python
class Agent:
    """Agent 定义"""
    
    # 基础信息
    id: str                    # 唯一标识
    name: str                  # 名称
    description: str           # 职责描述
    
    # 能力配置
    system_prompt: str         # 系统提示词
    tools: List[str]           # 可用工具列表
    
    # 输入输出
    input_schema: dict         # 输入参数schema
    output_schema: dict        # 输出格式schema
    
    # 协作配置
    triggers: List[str]        # 触发条件（关键词/意图）
    next_agents: List[str]     # 下游Agent
```

### 3.2 MVP Agent 列表（第一阶段：5-8个）

| Agent | 职责 | 触发条件 | 工具 |
|-------|------|----------|------|
| **IntentClassifier** | 识别用户意图，分类任务类型 | 任何用户输入 | 无 |
| **TaskPlanner** | 分解任务，生成执行计划 | IntentClassifier输出 | 无 |
| **RequirementAnalyst** | 分析需求，生成用户故事 | 需求类任务 | search_knowledge |
| **CompetitorAnalyst** | 竞品分析，提取优缺点 | 对标类任务 | web_search, web_crawler |
| **PRDWriter** | 撰写PRD文档 | PRD撰写任务 | doc_write, search_knowledge |
| **ComplianceChecker** | 合规检查，风险识别 | PRD完成后 | compliance_check |
| **ReviewPreparer** | 准备评审材料 | 评审准备任务 | doc_write |

### 3.3 工具系统

```python
class Tool:
    """工具定义"""
    
    name: str
    description: str
    parameters: dict          # 参数schema
    
    async def execute(self, **params) -> dict:
        """执行工具"""
        pass

# 核心工具
TOOL_REGISTRY = {
    # 信息获取
    "web_search": WebSearchTool,          # 网络搜索
    "web_crawler": WebCrawlerTool,        # 网页爬取
    "search_knowledge": KnowledgeQueryTool, # 查询知识库
    
    # 文档操作
    "doc_read": DocumentReadTool,         # 读取文档
    "doc_write": DocumentWriteTool,       # 写入文档
    "doc_update": DocumentUpdateTool,     # 更新文档
    
    # 医疗专用
    "compliance_check": ComplianceCheckTool,  # 合规检查
    "search_medical_reg": MedicalRegTool,     # 查询医疗法规
    
    # 分析工具
    "analyze_data": DataAnalysisTool,     # 数据分析
    "compare_versions": VersionCompareTool, # 版本对比
}
```

### 3.4 记忆系统

```python
class MemorySystem:
    """三层记忆系统"""
    
    # 1. 短期记忆 - Redis
    # 作用：当前会话上下文、任务执行状态
    # 存储：会话ID -> {messages, task_state, intermediate_results}
    # TTL：24小时
    
    # 2. 中期记忆 - PostgreSQL
    # 作用：项目级历史、Agent执行记录
    # 存储：项目ID -> {executions, outputs, decisions}
    # 保留：项目生命周期
    
    # 3. 长期记忆 - Obsidian
    # 作用：知识沉淀、最佳实践、用户偏好
    # 存储：知识库路径 -> {prd_templates, case_studies, user_preferences}
    # 保留：永久
```

---

## 4. 执行流程

### 4.1 用户请求处理流程

```
用户输入: "我要做切片借阅平台，帮我分析需求"

↓

[1] API Layer
    - 接收请求，验证参数
    - 创建会话ID

↓

[2] Strategy Layer - IntentClassifier
    - 识别意图：需求分析
    - 提取实体：产品=切片借阅平台
    - 置信度：0.95

↓

[3] Strategy Layer - TaskPlanner
    - 分解任务：
      a. 需求洞察（RequirementAnalyst）
      b. 竞品分析（CompetitorAnalyst）
      c. PRD撰写（PRDWriter）
    - 生成执行计划

↓

[4] Tactical Layer
    - 任务入队（Redis Queue）
    - 任务1：RequirementAnalyst 执行

↓

[5] Execution Layer - RequirementAnalyst
    - 调用 Kimi Coding API
    - 使用 search_knowledge 工具查询历史需求
    - 生成需求分析报告
    - 输出到中期记忆

↓

[6] Tactical Layer
    - 任务1完成，触发任务2
    - 任务2：CompetitorAnalyst 执行

↓

[7] Execution Layer - CompetitorAnalyst
    - 调用 Kimi Coding API
    - 使用 web_search 搜索竞品
    - 使用 web_crawler 获取竞品详情
    - 生成竞品分析报告

↓

[8] Tactical Layer
    - 任务2完成，触发任务3
    - 任务3：PRDWriter 执行

↓

[9] Execution Layer - PRDWriter
    - 读取任务1、2的输出（中期记忆）
    - 调用 Kimi Coding API 撰写PRD
    - 使用 doc_write 写入 Obsidian
    - 生成长期记忆

↓

[10] API Layer
    - 汇总所有Agent输出
    - 返回给用户：
      {
        "status": "completed",
        "tasks": [task1, task2, task3],
        "outputs": {
          "requirement_analysis": {...},
          "competitor_analysis": {...},
          "prd": {...}
        },
        "obsidian_link": "obsidian://..."
      }
```

### 4.2 Agent 执行详情

```python
async def execute_agent_task(agent_id: str, task_input: dict, context: dict):
    """执行单个Agent任务"""
    
    # 1. 加载Agent配置
    agent = agent_registry.get(agent_id)
    
    # 2. 准备记忆
    memory = await memory_system.get_relevant_context(
        session_id=context.session_id,
        query=task_input,
        k=3  # 最近3条相关记忆
    )
    
    # 3. 构建Prompt
    messages = [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": f"任务：{task_input}\n相关上下文：{memory}"}
    ]
    
    # 4. 调用Kimi API
    response = await kimi_client.chat(
        messages=messages,
        model="kimi-k2.5",
        tools=agent.tools
    )
    
    # 5. 处理工具调用（如果有）
    if response.tool_calls:
        for tool_call in response.tool_calls:
            tool_result = await tool_registry.execute(tool_call)
            messages.append({"role": "tool", "content": tool_result})
        
        # 再次调用获取最终结果
        response = await kimi_client.chat(messages=messages)
    
    # 6. 保存结果
    await memory_system.save_execution(
        session_id=context.session_id,
        agent_id=agent_id,
        input=task_input,
        output=response.content,
        tools_used=response.tool_calls
    )
    
    return response.content
```

---

## 5. 与现有系统集成

### 5.1 与 Jarvis PM 前端集成

```
前端页面（已有）          后端API（新）
┌─────────────────┐       ┌─────────────────┐
│ ChatInterface   │  ──▶  │ POST /execute   │
│（改造为Agent模式）│  ◀──  │ WebSocket状态推送│
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ Agent可视化面板  │  ◀──  │ GET /agents/status│
│（新增组件）      │       │ WebSocket实时更新│
└─────────────────┘       └─────────────────┘
```

### 5.2 与 Obsidian 集成

```python
class ObsidianIntegration:
    """Obsidian 知识库集成"""
    
    # 方案1: Obsidian API（如果可用）
    async def write_to_vault_api(self, content: str, path: str):
        """通过Obsidian REST API写入"""
        pass
    
    # 方案2: 文件系统直接写入
    async def write_to_filesystem(self, content: str, path: str):
        """直接写入Vault目录"""
        vault_path = "C:/Users/13400/Documents/Obsidian/MyVault"
        full_path = f"{vault_path}/{path}"
        # 写入文件
        
    # 方案3: 数据库存储 + Obsidian插件读取
    async def write_to_database(self, content: str, metadata: dict):
        """存入数据库，Obsidian插件同步"""
        pass
```

### 5.3 与 Kimi Coding API 集成

```python
class KimiCodingClient:
    """Kimi Coding API 客户端"""
    
    def __init__(self):
        self.api_key = settings.KIMI_API_KEY
        self.base_url = "https://api.kimi.com/coding"
        self.model = "kimi-k2.5"
    
    async def chat(
        self,
        messages: List[dict],
        tools: List[str] = None,
        stream: bool = False
    ):
        """调用Kimi Coding API"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": stream
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload
            )
            return response.json()
```

---

## 6. MVP 范围

### 6.1 第一阶段（2-3周）

**目标**：验证架构可行性，跑通完整流程

**必须实现：**
- [ ] Agent 执行引擎框架
- [ ] IntentClassifier + TaskPlanner（基础版）
- [ ] 3个核心Agent：RequirementAnalyst, CompetitorAnalyst, PRDWriter
- [ ] 3个核心工具：web_search, doc_write, search_knowledge
- [ ] 记忆系统：Redis短期记忆 + 文件系统长期记忆
- [ ] 基础API：/execute, /agents, /tasks

**验证标准：**
```
用户输入: "我要做切片借阅平台"
系统输出:
  - 需求分析报告（自动生成）
  - 竞品分析报告（自动生成）
  - PRD文档（自动生成，保存到指定目录）
  - 执行过程可见（Agent调用链、工具使用）
```

### 6.2 第二阶段（2-3周）

**目标**：完善Agent能力，增加协作功能

**增加：**
- [ ] ComplianceChecker Agent（医疗合规检查）
- [ ] ReviewPreparer Agent（评审准备）
- [ ] 工具扩展：web_crawler, compliance_check
- [ ] 记忆系统：Obsidian集成（或数据库）
- [ ] WebSocket实时状态推送
- [ ] Agent可视化面板（前端）

### 6.3 第三阶段（2-3周）

**目标**：扩展到50+ Agent，个性化学习

**增加：**
- [ ] 批量Agent实现（使用模板生成）
- [ ] 用户偏好学习（基于历史执行记录）
- [ ] 工作流模板（预设常见任务链）
- [ ] 与现有Jarvis PM前端深度整合

---

## 7. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| **后端框架** | FastAPI（已有） | 保持现有技术栈 |
| **任务队列** | Redis + RQ / Celery | 简单可靠，已有Redis |
| **数据库** | PostgreSQL（已有） | 保持现有技术栈 |
| **AI API** | Kimi Coding API | 用户指定，代码理解能力强 |
| **记忆存储** | Redis(短期) + Obsidian/PostgreSQL(长期) | 需求指定 |
| **消息格式** | JSON + Pydantic | 类型安全，易于验证 |

---

## 8. 风险与应对

| 风险 | 可能性 | 应对策略 |
|------|--------|----------|
| Kimi API 响应慢 | 中 | 添加超时处理、流式输出、异步队列 |
| Agent 输出质量不稳定 | 高 | Prompt工程优化、添加验证层、人工干预机制 |
| Obsidian 集成困难 | 中 | 备选方案：文件系统写入或数据库 |
| 任务链过长导致失败 | 中 | 添加断点续传、失败重试、子任务独立执行 |
| 50+ Agent 维护困难 | 中 | 使用模板生成Agent、分阶段实现 |

---

## 9. 成功标准

### 9.1 技术成功标准

- [ ] Agent 执行成功率 > 90%
- [ ] 端到端任务完成时间 < 5分钟（简单任务）
- [ ] API 响应时间 < 2秒（非流式）
- [ ] 支持并发执行 > 5个任务

### 9.2 业务成功标准

- [ ] 用户输入需求后，系统自动完成分析→对标→PRD生成
- [ ] PRD质量达到可直接评审水平（无需重写）
- [ ] 执行过程透明，用户可追溯每个Agent的输出
- [ ] 输出自动保存到知识库，可长期复用

---

## 10. 下一步行动

1. **确认本设计文档** - 用户审核并确认
2. **制定实现计划** - 使用 writing-plans skill 制定详细开发计划
3. **开始开发** - 按MVP范围逐步实现

---

**设计确认：**

| 角色 | 确认人 | 日期 | 备注 |
|------|--------|------|------|
| 产品设计 | 用户 | 待确认 | - |
| 技术评审 | Claude | 2026-04-10 | - |

---

*文档版本: v1.0*  
*最后更新: 2026-04-10*
