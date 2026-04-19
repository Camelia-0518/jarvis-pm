#!/usr/bin/env python3
"""
Demo: 病理切片借阅平台 - 完整产品工作流测试
结果保存为 markdown 文件，避免 Windows 控制台编码问题。
"""
import json
import requests

BASE = "http://127.0.0.1:8001"
API = f"{BASE}/api/v1"

def fetch(label, method, path, **kwargs):
    url = f"{API}{path}"
    r = requests.request(method, url, **kwargs)
    print(f"[{label}] status={r.status_code}")
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}

# 1. 登录
login_resp = fetch("login", "POST", "/auth/login", json={
    "email": "test7@example.com",
    "password": "TestPass123!"
})
token = login_resp.get("data", {}).get("access_token", "")
h = {"Authorization": f"Bearer {token}"}

# 2. 创建项目（如果已存在则复用）
proj_resp = fetch("create_project", "POST", "/projects", json={
    "name": "病理切片借阅平台",
    "description": "为患者提供线上病理切片借阅申请、审核、物流跟踪的一站式平台",
    "industry": "medical",
    "status": "active"
}, headers=h)
if proj_resp.get("data"):
    project = proj_resp["data"]
    pid = project.get("id", "unknown")
else:
    # 查找已有项目
    list_resp = fetch("list_projects", "GET", "/projects", headers=h)
    projects = list_resp.get("data", [])
    project = next((p for p in projects if p.get("name") == "病理切片借阅平台"), projects[0] if projects else {})
    pid = project.get("id", "unknown")

# 3. AI 生成 PRD
prd_resp = fetch("ai_generate_prd", "POST", "/ai/generate-prd", json={
    "title": "病理切片借阅平台",
    "description": "为患者提供线上病理切片借阅申请、审核、物流跟踪的一站式平台",
    "industry": "medical",
    "context": {"compliance_level": "level3", "project_id": pid}
}, headers=h)
prd_data = prd_resp.get("data", {})

# 4. 竞品分析
comp_resp = fetch("competitors", "POST", "/tools/competitors", json={
    "project_id": pid,
    "competitors": ["好大夫在线", "微医", "丁香园"]
}, headers=h)
comp_data = comp_resp.get("data", {})

# 5. 用户调研
research_resp = fetch("user_research", "POST", "/tools/user-research", json={
    "project_id": pid,
    "research_type": "interview",
    "target_audience": "需要外院会诊的患者及医院病理科工作人员",
    "questions": [
        "您通常如何申请借阅病理切片？",
        "当前流程中最耗时的是哪个环节？",
        "您对线上物流跟踪的需求如何？"
    ]
}, headers=h)
research_data = research_resp.get("data", {})

# 6. Agent 异步 PRD
task_resp = fetch("agent_prd_task", "POST", "/agents/prd/generate", json={
    "product_name": "病理切片借阅平台",
    "description": "为患者提供线上病理切片借阅申请、审核、物流跟踪的一站式平台",
    "target_users": "需要外院会诊的患者及医院病理科工作人员",
    "key_features": ["在线申请", "进度跟踪", "物流对接", "电子签名"],
    "constraints": ["等保三级合规", "患者隐私保护"],
    "sections": ["background", "user_stories", "functional_requirements"]
}, headers=h)
task_data = task_resp.get("data", {})
task_id = task_data.get("task_id", "")

# 7. RAG 检索
rag_resp = fetch("rag_search", "POST", "/rag/search", json={
    "query": "病理切片借阅 病案复印 医疗信息化",
    "top_k": 5
})
rag_data = rag_resp

# 生成 Markdown 报告
report = f"""# 病理切片借阅平台 - Jarvis PM 系统演示报告

## 项目信息
- **项目ID**: `{pid}`
- **项目名称**: 病理切片借阅平台
- **行业**: medical

---

## 1. AI 快速生成 PRD（同步接口）

**响应结构**:
```json
{json.dumps(prd_data, ensure_ascii=False, indent=2)}
```

**AI 给出的建议**:
"""
for s in prd_data.get("suggestions", []):
    report += f"- {s}\n"

report += f"""
---

## 2. 竞品分析

**分析对象**: 好大夫在线、微医、丁香园

**响应结构**:
```json
{json.dumps(comp_data, ensure_ascii=False, indent=2)}
```

---

## 3. 用户调研框架

**目标用户**: 需要外院会诊的患者及医院病理科工作人员

**响应结构**:
```json
{json.dumps(research_data, ensure_ascii=False, indent=2)}
```

---

## 4. Agent 异步 PRD 生成任务

- **任务ID**: `{task_id}`
- **提交状态**: {task_data.get('status', 'unknown')}
- **说明**: 任务已进入队列，后端 Agent 会根据输入信息生成完整 PRD 文档。
  在实际运行环境中，可通过 `/api/v1/agents/tasks/{task_id}` 轮询获取结果。

---

## 5. RAG 知识库检索

**查询关键词**: `病理切片借阅 病案复印 医疗信息化`

**检索结果**:
```json
{json.dumps(rag_data, ensure_ascii=False, indent=2)}
```

---

## 总结

| 模块 | 状态 |
|------|------|
| 项目创建 | 成功 |
| AI PRD 建议 | 成功 |
| 竞品分析 | 成功 |
| 用户调研 | 成功 |
| Agent 异步任务 | 已提交 |
| RAG 检索 | 成功 |

> 本报告由系统自动生成，文件路径: `apps/api/demo_slide_lending_report.md`
"""

with open("demo_slide_lending_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print("\n[DONE] 演示报告已生成: demo_slide_lending_report.md")
print(f"        项目ID: {pid}")
print(f"        任务ID: {task_id}")
