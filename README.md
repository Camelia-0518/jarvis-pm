# Jarvis PM

> AI-Native Product Management Collaboration Platform
> 
> Reduce PRD writing from 2-3 days to ~10 minutes through multi-agent collaboration.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js_14-000?logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?logo=python)](https://python.org)

---

## Overview

Jarvis PM is an AI-native collaboration platform built for product managers. It replaces fragmented tools (Notion, Jira, Excel) with a unified system where **7 specialized AI agents** collaborate to handle the entire product design workflow — from requirement collection to PRD generation, compliance checking, and review preparation.

### Efficiency Gains

| Workflow | Traditional | Jarvis PM | Improvement |
|:---------|:------------|:----------|:------------|
| PRD Writing | 2-3 days | 10 min | **90%** |
| Competitor Analysis | 4-6 hours | 5 min | **95%** |
| Review Preparation | 1 day | 5 min | **95%** |
| Standup Report | 15 min | 1 min | **93%** |

---

## Architecture

### Multi-Agent System (7 Specialized Agents)

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
```

| Agent | Responsibility |
|:------|:---------------|
| **Intent Classifier** | Hybrid rule + LLM routing to appropriate agents |
| **Task Planner** | Decomposes intent into executable task chains with dependency resolution |
| **Requirement Analyzer** | Extracts user stories, pain points, feature priorities |
| **Competitor Analyst** | Web search + LLM inference; supports candidate confirmation mode |
| **PRD Generator** | 8-chapter structured PRD with industry-aware templates; auto-quality evaluation |
| **Compliance Checker** | Medical industry compliance (等保三级, patient privacy, audit trails) |
| **Review Preparer** | Generates agendas, Q&A prep, risk analysis, stakeholder-specific materials |

### Dual Workflow Engine

- **AgentOrchestrator** (low-level): Sequential, parallel, conditional, and merge chain execution
- **WorkflowEngine** (high-level): Pre-defined skill chains:
  - `from-scratch`: Brainstorm → PRD → Review Prep
  - `security-review`: Risk Identification → Compliance Check → Report
  - `prd-package`: PRD + Review Materials + Standup Template

### LLM Client Architecture

Multi-provider fallback with automatic failover:

```
Kimi (Primary) → OpenAI → Anthropic
     │                │         │
     └────────────────┴─────────┘
              │
              ▼
     Retry (3 attempts, exponential backoff 1s/2s)
              │
              ▼
     Response Cache (SHA256-based, TTL 5min, max 500 entries)
```

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| **Frontend** | Next.js 14 App Router, React 18, TypeScript, Tailwind CSS v4, Zustand |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Alembic |
| **Database** | SQLite (dev) / PostgreSQL (prod), Redis (cache) |
| **AI Models** | Kimi k2.6-code-preview (primary), Claude 3.5 Sonnet, GPT-4 |
| **Real-time** | WebSocket multi-room collaboration with cursor sync |
| **Testing** | Vitest (frontend), pytest (backend), Playwright (E2E) |
| **Deployment** | Vercel (frontend) + Railway (backend) |

---

## Project Structure

```
jarvis-pm/
├── apps/
│   ├── web/                    # Next.js 14 frontend
│   │   ├── src/app/            # App Router (dashboard, workspace, PRD editor)
│   │   ├── src/components/     # Reusable UI components
│   │   └── src/stores/         # Zustand state management
│   │
│   └── api/                    # FastAPI backend
│       ├── app/agents/         # Multi-agent system core (7 agents + orchestrator)
│       ├── app/api/v1/         # 20+ REST API routers
│       ├── app/services/       # Workflow engine, skill processor
│       ├── app/websocket/      # Real-time collaboration manager
│       └── tests/              # 40+ test modules (pytest)
│
├── packages/shared/            # Shared types and utilities
├── e2e_test.py                 # End-to-end test suite
└── smoke_test.py               # Smoke tests
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
# Edit .env: set KIMI_API_KEY or ANTHROPIC_API_KEY

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

- **Conversational collection**: Multi-turn dialogue gathers requirements
- **8-chapter structure**: Executive summary, user stories, functional requirements, non-functional requirements, architecture, UI/UX, roadmap, appendices
- **Industry templates**: Healthcare, e-commerce, SaaS with domain-specific compliance rules
- **Auto-evaluation**: LLM-as-a-Judge quality assessment with rewrite triggers

### 2. Real-time Collaboration

- WebSocket-based multi-user PRD editing
- Cursor position sync, text changes, annotations
- Presence detection (join/leave)

### 3. Medical Compliance

Built-in healthcare industry checks:
- 等保三级 (Classified Protection Level 3)
- Patient data privacy (HIPAA-like)
- Audit trail requirements
- Multi-hospital deployment patterns

### 4. Review Assistant

Auto-generates:
- Meeting agenda with time-boxed sections
- Q&A preparation (anticipated questions + suggested answers)
- Risk analysis with mitigation strategies
- Stakeholder-specific materials (医务科/信息科/财务科 perspectives)

### 5. Export

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
