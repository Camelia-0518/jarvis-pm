# Jarvis PM

AI 驱动的产品管理协作平台

> 用对话方式 10 分钟完成原本需要 2 天的 PRD 撰写和评审准备

---

## 🔄 最新更新 (2026-04-10)

**项目整合完成** - 融合了 `ai-pm-assistant` 的精华组件

### 新增能力
- 🤝 **实时协作** - 多用户实时编辑和光标同步
- 🌿 **版本控制** - 分支对比、合并、版本历史
- 📝 **评审工作流** - 完整的 PRD 评审流程管理
- 💬 **AI 对话界面** - 对话式 PRD 生成
- 📚 **知识库** - 与 Obsidian 深度集成
- 📤 **导出面板** - 支持 Markdown/PDF/飞书等多格式导出

查看 [INTEGRATION.md](./INTEGRATION.md) 了解整合详情。

---

---

## 项目概述

Jarvis PM 是一个专为产品经理打造的 AI 原生工作平台，通过深度集成 Claude API 和 Kimi API，实现从需求输入到 PRD 生成、从评审准备到站会报告的全流程 AI 辅助。

### 核心价值

| 工作流 | 传统方式 | Jarvis PM | 效率提升 |
|:-------|:---------|:----------|:---------|
| PRD 撰写 | 2-3 天 | 10 分钟 | 90% |
| 评审准备 | 1 天 | 5 分钟 | 95% |
| 站会报告 | 15 分钟 | 1 分钟 | 93% |

### 技术栈

- **前端**: Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **后端**: FastAPI + Python 3.11
- **数据库**: PostgreSQL + Redis
- **AI**: Claude API / Kimi API
- **部署**: Vercel (前端) + Railway (后端)

---

## 项目结构

```
jarvis-pm/
├── apps/
│   ├── web/                 # Next.js 前端应用
│   │   ├── src/
│   │   │   ├── app/        # App Router 页面
│   │   │   │   ├── page.tsx           # 首页
│   │   │   │   ├── dashboard/         # 工作台
│   │   │   │   └── prd/[id]/          # PRD 编辑器
│   │   │   └── ...
│   │   └── package.json
│   │
│   └── api/                # FastAPI 后端服务
│       ├── app/
│       │   ├── api/v1/     # API 路由
│       │   │   ├── endpoints/
│       │   │   │   ├── auth.py        # 认证
│       │   │   │   ├── projects.py    # 项目
│       │   │   │   ├── prds.py        # PRD
│       │   │   │   └── ai.py          # AI 接口
│       │   │   └── router.py
│       │   ├── core/       # 核心配置
│       │   ├── models/     # 数据库模型
│       │   └── services/   # 业务逻辑
│       ├── main.py
│       └── requirements.txt
│
├── docs/                   # 文档
│   ├── C-竞品分析.md
│   └── A-PRD设计.md
│
└── README.md
```

---

## 快速开始

### 前端

```bash
cd apps/web
npm install
npm run dev
```

访问 http://localhost:3000

### 后端

```bash
cd apps/api

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 ANTHROPIC_API_KEY

# 启动服务
python main.py
```

API 文档: http://localhost:8000/docs

---

## 核心功能

### 1. AI PRD 生成器

### 6. 代码生成功能 (新增)

从 PRD 自动生成可运行的代码：

- **原型生成**: 从 PRD 提取 UI 需求，生成 HTML + Tailwind CSS 原型
- **API 生成**: 生成 OpenAPI 3.0 规范和 FastAPI CRUD 代码
- **组件生成**: 识别 UI 组件需求，生成 React + TypeScript 组件
- **一键导出**: 支持 HTML/ZIP/JSON 多格式导出

**API 端点**:
```
POST /api/v1/code/prototype      # 生成原型
POST /api/v1/code/api-spec       # 生成 API 规范
POST /api/v1/code/components     # 生成组件
POST /api/v1/code/generate-all   # 生成所有代码
POST /api/v1/code/export         # 导出代码
```

### 1. AI PRD 生成器

- **对话式撰写**: 通过多轮对话收集需求
- **智能大纲**: AI 自动生成 8 章标准 PRD 结构
- **行业模板**: 医疗/电商/SaaS 等行业定制
- **实时预览**: Markdown 编辑 + 渲染预览

### 2. Multi-Agent 协作系统

- **5个AI角色**: CEO(产品战略)、Designer(体验设计)、Eng Manager(工程经理)、QA Engineer(质量保证)、Orchestrator(任务协调)
- **可视化编排**: React Flow 拖拽式工作流画布
- **决策透明**: Agent 决策日志、置信度评分
- **冲突检测**: 自动识别 Agent 间分歧

### 3. 实时协作

- **多用户编辑**: WebSocket 实时同步
- **光标同步**: 查看其他用户位置和选择
- **评论系统**: @提及、评论回复、解决状态
- **在线用户**: 实时显示协作者列表

### 4. 评审助手

- **材料自动生成**: 议程/Q&A/风险预案/决策点
- **利益相关方分析**: 自动识别医务科/信息科/财务科关注点
- **合规检查**: 医疗等保自动扫描
- **决策日志**: Agent 思考过程可视化

### 5. 项目管理

- **PRD 版本管理**: 历史对比、变更追踪
- **版本关联**: PRD ↔ Design ↔ Code 版本映射
- **工作空间**: 多项目隔离、权限管理
- **站会报告**: 自动生成日报
- **一键导出**: Markdown/PDF/飞书/GitHub

---

## 开发阶段

### Phase C: 竞品分析 ✅

已完成对 Notion、飞书项目、Jira、Linear、语雀的深度分析，提取设计模式和差异化机会。

### Phase A: PRD 设计 ✅

已完成产品需求文档，包括：
- 用户画像和用户故事
- 核心功能列表 (P0/P1/P2)
- 技术架构设计
- 数据模型定义
- UI/UX 原型

### Phase B: 开发中 🚧

已建立项目基础：
- ✅ Next.js + Tailwind 前端项目
- ✅ FastAPI 后端项目
- ✅ 首页和 Dashboard 页面
- ✅ PRD 编辑器原型
- ✅ AI 服务接口

下一步：
- [x] Multi-Agent 角色系统
- [x] 可视化工作流画布
- [x] 实时协作功能
- [ ] 数据库迁移和模型实现
- [ ] 认证系统
- [ ] AI 生成流程完善
- [ ] WebSocket 后端实现

---

## 环境变量

### 后端 (.env)

```env
# App
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jarvis_pm

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key

# AI
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

---

## 贡献

欢迎提交 Issue 和 PR！

---

## 许可证

MIT
