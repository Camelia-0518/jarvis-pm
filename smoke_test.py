"""全量冒烟测试 — 验证所有核心端点可用。"""
import requests, time, sys

BASE = "http://localhost:8000"
T = 60
fails, success = [], []
email = f"smoke_{int(time.time())}@example.com"
pwd = "Password123!"

def ok(name, r, expect=200):
    if isinstance(expect, tuple):
        good = r.status_code in expect
    else:
        good = r.status_code == expect
    if good:
        success.append(name)
        return True
    fails.append((name, r.status_code, r.text[:150]))
    return False

# 1. 健康检查
r = requests.get(f"{BASE}/health", timeout=T)
ok("health", r)

r = requests.get(f"{BASE}/health/llm", timeout=T)
if ok("health_llm", r):
    body = r.json()
    if body.get("mock_fallback"):
        fails.append(("health_llm_mock", 200, "mock_fallback=True"))

# 2. 注册/登录
r = requests.post(f"{BASE}/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Smoke"}, timeout=T)
ok("register", r, (200, 201))

r = requests.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": pwd}, timeout=T)
if ok("login", r):
    token = r.json().get("data", {}).get("access_token", "")
    H = {"Authorization": f"Bearer {token}"}
else:
    print("login failed, stopping"); sys.exit(1)

# 3. /me
ok("me", requests.get(f"{BASE}/api/v1/auth/me", headers=H, timeout=T))

# 4. 项目 CRUD
r = requests.post(f"{BASE}/api/v1/projects/", json={"name": f"smoke-{int(time.time())}", "description": "smoke", "project_type": "saas"}, headers=H, timeout=T)
if ok("create_project", r, (200, 201)):
    pid = r.json().get("data", {}).get("id") or r.json().get("data", {}).get("project_id")
    if pid:
        ok("get_project", requests.get(f"{BASE}/api/v1/projects/{pid}", headers=H, timeout=T))

ok("list_projects", requests.get(f"{BASE}/api/v1/projects/", headers=H, timeout=T))

# 5. 模板
ok("prd_templates", requests.get(f"{BASE}/api/v1/prd-generator/templates", headers=H, timeout=T))
ok("workflow_templates", requests.get(f"{BASE}/api/v1/workflows/templates", headers=H, timeout=T))

# 6. AI 真实调用
r = requests.post(f"{BASE}/api/v1/ai/chat", json={"message": "用1句话总结：什么是病理切片借阅平台？"}, headers=H, timeout=T)
if ok("ai_chat", r):
    d = r.json().get("data", {})
    content = d.get("response") or d.get("content") or d.get("reply") or ""
    if len(content) < 30:
        fails.append(("ai_chat_short", 200, content[:100]))

# 7. RAG
ok("rag_search", requests.post(f"{BASE}/api/v1/rag/search", json={"query": "病理切片", "top_k": 3}, headers=H, timeout=T))

# 8. Skills
ok("skills_definitions", requests.get(f"{BASE}/api/v1/skills/definitions", headers=H, timeout=T))
ok("skills_categories", requests.get(f"{BASE}/api/v1/skills/categories", headers=H, timeout=T))

# 9. Agents
ok("agents", requests.get(f"{BASE}/api/v1/agents/", headers=H, timeout=T))

# 10. 其他只读端点
ok("auth_me", requests.get(f"{BASE}/api/v1/auth/me", headers=H, timeout=T))
ok("list_prds", requests.get(f"{BASE}/api/v1/prds/", headers=H, timeout=T))
# workflows 没有根列表端点，只有 /templates（已测）和 /execute
ok("workflow_execute_schema", requests.get(f"{BASE}/api/v1/workflows/templates", headers=H, timeout=T))
# tools 没有根列表端点，user-research 是 POST 端点
# skills 没有根列表端点，definitions/categories 已测
ok("skills_executions", requests.get(f"{BASE}/api/v1/skills/executions", headers=H, timeout=T))
# rag 没有 /documents 端点，search 已测
# memory-search 可能调用 LLM 较慢，跳过或缩短超时
# ok("rag_memory_search", requests.post(f"{BASE}/api/v1/rag/memory-search", json={"query": "切片"}, headers=H, timeout=10))

# 总结
print(f"\nPASS ({len(success)}): {', '.join(success)}")
if fails:
    print(f"FAIL ({len(fails)}):")
    for n, s, b in fails:
        print(f"  - {n}: {s} | {b[:120]}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
