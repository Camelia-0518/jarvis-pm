# Jarvis PM

> AI-Native Product & Delivery Management Platform
>
> 从需求到交付：PRD 生成 10 分钟，交付计划自动生成，风险矩阵 AI 驱动。
> 专为医疗信息化项目（HIS/EMR/互联互通）优化。

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js_14-000?logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?logo=python)](https://python.org)

---

## Demo Preview

> 本地运行效果截图，展示核心功能界面。

| 项目健康度仪表盘 | 交付中心看板 |
|:--|:--|
| `/health` — 双 Gauge 仪表盘 + 风险矩阵 + 趋势图 + 环形饼图 + KPI 卡片 | `/delivery` — 甘特图 + WBS 看板 + RACI 矩阵 |
| *(启动后截图替换)* | *(启动后截图替换)* |

---

## Overview

Jarvis PM 是一个 AI 原生的产品与交付管理平台。它用 **10 个专业 AI Agent** 协同工作，覆盖从需求收集、PRD 生成、合规检查，到**交付计划、风险分析、干系人管理**的完整生命周期。

### 双角色覆盖

| 角色 | 核心能力 | 传统耗时 | Jarvis PM |
|:------|:---------|:---------|:----------|
| **产品 PM** | PRD 生成、竞品分析、评审准备 | 2-3 天 | ~10 min |
| **交付 PM** | WBS、里程碑、风险矩阵、RACI | 1-2 天 | ~5 min |

---

## Architecture

### Multi-Agent System (10 Specialized Agents)

```
User Input
    │
    ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Intent          │────▶│ Task            │────▶│ Requirement     │
│ Classifier      │     │ Planner         │     │ Analyzer        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
    ┌─────────────────┐     ┌─────────────────┐          │
    │ Review          │◀────│ Compliance      │◀─────────┘
    │ Preparer        │     │ Checker         │
    └─────────────────┘     └─────────────────┘
                                    ▲
    ┌─────────────────┐             │
    │ PRD             │◀────────────┘
    │ Generator       │◀────┌─────────────────┐
    └─────────────────┘     │ Competitor      │
                            │ Analyst         │
                            └─────────────────┘

    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │ Delivery        │     │ Risk            │     │ Stakeholder     │
    │ Planner         │     │ Manager         │     │ Coordinator     │
    └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 新增：交付管理 Agent（v2.0）

| Agent | Responsibility |
|:------|:---------------|
| **Delivery Planner** | 从PRD自动生成WBS、里程碑计划、资源估算、甘特图 |
| **Risk Manager** | 风险识别、概率/影响矩阵、应对策略、预警机制 |
| **Stakeholder Coordinator** | RACI矩阵、干系人分析、分层沟通计划、状态报告模板 |

### 医疗行业深度适配

- HIS 系统上线标准阶段（需求→设计→开发→互联互通测评→医保对接→测试→部署→培训→运维）
- EMR 电子病历评级要求（4-6级功能规范）
- 互联互通标准化成熟度测评（数据集/CDA/共享文档）
- 等保三级安全合规要求
- 多院区部署模式
- 医务科/信息科/临床科室/医保办/供应商 多方干系人模型

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Frontend** | Next.js 14 App Router, React 18, TypeScript, Tailwind CSS v4, Zustand |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Alembic |
| **Database** | SQLite (dev) / PostgreSQL (prod), Redis (cache) |
| **AI Models** | DeepSeek V4 (primary), Kimi k2.6, Claude 3.5 Sonnet, GPT-4 |
| **Testing** | Vitest (frontend), pytest (backend), Playwright (E2E) |
| **Deployment** | Vercel (frontend) + Railway (backend) |

---

## Project Structure

```
jarvis-pm/
├── apps/
│   ├── web/                    # Next.js 14 frontend
│   │   ├── src/app/            # App Router (dashboard, delivery, PRD editor)
│   │   │   ├── dashboard/      # 工作台
│   │   │   ├── delivery/       # 🆕 交付中心（看板/甘特图/风险矩阵）
│   │   │   └── prd/            # PRD 编辑
│   │   ├── src/components/
│   │   │   └── delivery/       # 🆕 KanbanBoard, GanttChart, RiskMatrix, StakeholderPanel
│   │   └── src/stores/         # Zustand stores (prdStore, deliveryStore)
│   │
│   └── api/                    # FastAPI backend
│       ├── app/agents/         # 10 agents (7 product + 3 delivery)
│       │   └── agents/
│       │       ├── delivery_planner.py    # 🆕 WBS+里程碑+甘特图
│       │       ├── risk_manager.py        # 🆕 风险矩阵+应对策略
│       │       └── stakeholder_coordinator.py  # 🆕 RACI+沟通计划
│       ├── app/api/v1/endpoints/
│       │   └── delivery.py      # 🆕 交付管理 API
│       ├── app/models/
│       │   └── delivery_plan.py # 🆕 交付计划数据模型
│       ├── app/services/
│       │   └── delivery_service.py # 🆕 交付服务编排
│       └── tests/               # 40+ test modules (pytest)
│
├── packages/shared/            # Shared types and utilities
└── e2e_test.py                 # End-to-end test suite
```

---

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- (Optional) Redis

### Backend

```bash
cd apps/api

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env: set DEEPSEEK_API_KEY or KIMI_API_KEY

python main.py
```

API Docs: http://localhost:8000/docs

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000

---

## Core Features

### 1. AI PRD Generator

- 8-chapter structured PRD with industry-aware templates
- Healthcare, e-commerce, SaaS domain-specific compliance rules
- Auto-evaluation with LLM-as-a-Judge quality assessment

### 2. AI Delivery Planner 🆕

- **WBS 自动生成**：从PRD/需求提取功能模块，分解为可执行任务
- **里程碑计划**：含 HIS 上线/互联互通测评/医保对接等医疗专属阶段
- **资源估算**：人天计算 + 20% 风险缓冲，角色自动分配
- **甘特图可视化**：交互式时间线，依赖关系展示

### 3. AI Risk Manager 🆕

- **16 条医疗行业风险知识库**：需求/技术/合规/干系人/进度/资源/业务 7 大类
- **概率×影响矩阵**：5×5 网格热力图，自动分级（极高/高/中/低）
- **三级应对策略**：预防措施 + 应急方案 + 触发条件
- **责任人自动分配**：按风险类别指派负责人

### 4. AI Stakeholder Coordinator 🆕

- **12 角色医疗干系人模型**：院领导→医务科→信息科→临床科室→供应商→测评机构
- **RACI 矩阵**：18 项活动 × 12 角色责任分配
- **6 类会议节奏**：日站会/周会/双周需求评审/月度汇报/里程碑评审/接口联调会
- **4 级报告体系**：日报/周报/月报/风险专报 + 问题升级路径

### 5. 交付中心看板 🆕

- **项目健康仪表盘**：交付健康度 + 风险健康度（绿/黄/红三色预警）
- **WBS 看板视图**：按阶段分列的任务卡片，含优先级/工期/角色
- **甘特图时间线**：可视化项目周期，颜色区分阶段
- **风险矩阵热力图**：交互式 5×5 网格，钻取到具体风险
- **RACI 矩阵视图**：彩色标记 R/A/C/I 责任分配

### 6. Medical Compliance

- 等保三级 (Classified Protection Level 3)
- Patient data privacy (HIPAA-like)
- Audit trail requirements
- Multi-hospital deployment patterns

### 7. Export

- Markdown, PDF, Feishu (Lark), GitHub Issues/PRs

---

## Testing

```bash
# Backend
pytest --co -q
pytest -x

# Frontend
npm run test

# E2E
python e2e_test.py
python smoke_test.py
```

---

## Environment Variables

```env
# Database (SQLite for zero-config local dev)
DATABASE_URL=sqlite+aiosqlite:///./jarvis_pm.db

# AI Providers (at least one required)
DEEPSEEK_API_KEY=sk-...
KIMI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# JWT
SECRET_KEY=your-secret-key
```

See `apps/api/.env.example` for full configuration.

---

## License

MIT
