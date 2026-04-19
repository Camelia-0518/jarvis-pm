# Jarvis PM E2E 问题修复总结

> 修复日期: 2026-04-19
> 基于 E2E 测试报告（2026-04-18）

---

## 修复概览

| 优先级 | 问题 | 状态 | 修改文件 |
|--------|------|------|----------|
| P0 | Workspace PRD 列表为空 | ✅ 已修复 | `api.ts`, `workspace/page.tsx` |
| P0 | `/skills` 路由 404 | ✅ 已修复 | 新建 `skills/page.tsx` |
| P1 | RAG 接口路径不一致 | ✅ 已修复 | `rag.py` |
| P1 | PRD Editor 加载失败 | ✅ 已修复 | `prds.py`, `prd/[id]/page.tsx` |
| P1 | Dashboard Stats 接口 404 | ✅ 已确认 | 无需修改（前端已实现） |
| P2 | Windows 中文编码 | ✅ 已修复 | `main.py` |
| P2 | WebSocket URL 不统一 | ✅ 已修复 | `main.py` |
| P2 | 端口僵尸进程 | ✅ 已修复 | 新建 `kill-server.ps1` |

---

## 详细修复说明

### 1. P0-2: Workspace PRD 列表为空 ✅

**根因**: 前后端数据结构不匹配
- 后端返回 `{ items: [...], total: N }`
- 前端期望 `PRD[]` 数组
- 导致 `projectPRDs` 变成对象，`.length` 和 `.map()` 全部异常

**修改**:
- `apps/web/src/lib/api.ts:181` - `prdApi.list` 返回类型改为 `{ items: PRD[]; total: number }`
- `apps/web/src/app/workspace/page.tsx:35` - 适配 `res?.items || []`

**验证**: TypeScript 编译通过

---

### 2. P0-1: `/skills` 路由 404 ✅

**根因**: 无独立技能页面，技能面板仅为 Dashboard 内联弹窗

**修改**:
- 新建 `apps/web/src/app/skills/page.tsx`
- 功能: 技能卡片网格、分类筛选、搜索、参数表单执行、最近执行历史

**验证**: TypeScript 编译通过，路由 `/skills` 现在可访问

---

### 3. P1-4: RAG 接口路径不一致 ✅

**根因**: `/query` 路径缺失，仅实现了 `/search`

**修改**:
- `apps/api/app/api/v1/endpoints/rag.py` - 新增 `/query` 作为 `/search` 的别名

```python
@router.post("/query", response_model=SearchResponse)
async def query_documents(request: SearchRequest):
    return await search_documents(request)
```

---

### 4. P1-5: PRD Editor 加载失败 ✅

**根因 1（后端 bug）**: `prds.py:431` 使用未定义变量 `chapter`
**根因 2（前端）**: PRD Editor 缺乏数据校验和错误边界

**修改**:
- `apps/api/app/api/v1/endpoints/prds.py:431` - `chapter` → `data.chapter`
- `apps/web/src/app/prd/[id]/page.tsx:76-92` - 增加 ID 校验、PRD 存在性检查、详细错误提示

**Python 语法验证**: ✅ 通过

---

### 5. P1-3: Dashboard Stats 接口 404 ✅

**结论**: 无需修改
- 当前 Dashboard 统计完全由前端计算（基于 `projects` + `skillsApi.getExecutions`）
- 无 `/api/v1/dashboard/stats` 调用
- E2E 报告描述与当前代码状态不符

---

### 6. P2-6: Windows 中文编码 ✅

**根因**: HTTP 响应头缺少 `charset=utf-8`

**修改**:
- `apps/api/main.py` - 新增响应头中间件

```python
@app.middleware("http")
async def add_content_type_charset(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and "charset" not in content_type:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response
```

**Python 语法验证**: ✅ 通过

---

### 7. P2-7: WebSocket URL 不统一 ✅

**根因**: 两个 WebSocket 挂载点前缀不同
- `/ws/workflow/{id}` vs `/api/v1/ws/collaboration/{room}/{user}`

**修改**:
- `apps/api/main.py` - 新增统一前缀挂载（保留旧路由兼容）

```python
app.include_router(websocket_router, prefix="/ws")
app.include_router(websocket_router, prefix="/api/v1/ws")  # Unified prefix
```

**Python 语法验证**: ✅ 通过

---

### 8. P2-8: 端口僵尸进程 ✅

**根因**: uvicorn reload 模式在 Windows 上异常退出后产生僵尸进程

**修改**:
- 新建 `scripts/kill-server.ps1`
- 功能: 按端口查找并终止进程、支持 `-KillAllPython` 参数、自动扫描常用端口

**使用方式**:
```powershell
# 清理端口 8000
.\scripts\kill-server.ps1

# 清理所有 uvicorn/python 进程
.\scripts\kill-server.ps1 -KillAllPython
```

---

## 验证清单

- [x] Python 语法检查通过 (`py_compile`)
- [x] TypeScript 类型检查通过 (`tsc --noEmit`)
- [x] 所有修改文件已确认保存

## 待验证（需启动服务后人工确认）

- [ ] Workspace 页面 PRD 列表正常显示
- [ ] `/skills` 页面可正常访问和交互
- [ ] RAG `/query` 接口返回正确
- [ ] PRD Editor 能正常加载已有 PRD
- [ ] 后端 JSON 响应在 Windows 终端显示中文正常
- [ ] WebSocket 连接通过 `/api/v1/ws` 前缀可用

---

## 重启服务指令

```bash
# 1. 清理端口（如有需要）
.\scripts\kill-server.ps1

# 2. 启动后端（端口 8002）
cd apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload

# 3. 启动前端（端口 3000）
cd apps/web
npm run dev
```

---

*修复完成时间: 2026-04-19*
