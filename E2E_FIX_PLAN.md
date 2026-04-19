# Jarvis PM E2E 问题修复计划

> 基于 E2E 测试报告（2026-04-18）的深度分析与修复方案
> 计划生成时间: 2026-04-19

---

## 问题总览

| 优先级 | 问题 | 根因定位 | 预估工作量 |
|--------|------|----------|-----------|
| P0 | `/skills` 路由 404 | 无独立页面，只有内联面板 | 2h |
| P0 | Workspace PRD 列表为空 | 前后端数据结构不匹配 | 1h |
| P1 | Dashboard Stats 接口 404 | 报告描述与实际代码不符 | 0.5h（确认） |
| P1 | RAG 接口路径不一致 | `/query` 缺失 | 0.5h |
| P1 | PRD Editor 加载失败 | 数据解析潜在问题 | 1-2h |
| P2 | Windows 中文编码 | 响应头缺 charset | 0.5h |
| P2 | WebSocket URL 不统一 | 路由前缀不一致 | 1h |
| P2 | 端口僵尸进程 | 环境问题，非代码问题 | 0.5h |

---

## 详细修复方案

### P0-1: `/skills` 路由 404

**现状分析**
- Dashboard 页面中没有 `/skills` 导航链接
- "技能面板"是内联弹窗（`showSkillPanel` state），非独立页面
- 但 `/skills/definitions` 等 API 端点均存在且正常
- E2E 测试中访问 `/skills` 返回 404，因为 `app/skills/page.tsx` 不存在

**根因**
- 项目早期规划了独立技能页面，但实际实现为 Dashboard 内联面板
- E2E 测试脚本可能按旧设计访问了 `/skills`

**修复方案（推荐方案 A：创建独立页面）**

**涉及文件：**
1. `apps/web/src/app/skills/page.tsx` （新建）

**实现要点：**
```tsx
// 新建 skills 页面，复用现有能力：
// - useSkillStore 获取技能定义
// - skillsApi.getAll() / skillsApi.getCategories()
// - 技能卡片网格展示（分类筛选 + 搜索）
// - 点击技能弹出执行面板（复用 Dashboard 中的技能面板逻辑）
// - 展示最近执行历史（skillsApi.getExecutions）
```

**页面结构：**
- 顶部：搜索框 + 分类标签筛选
- 主体：技能卡片网格（icon + name + description + category badge）
- 右侧/底部：最近执行历史
- 点击卡片：展开执行参数表单 → 调用 execute → 展示结果

**替代方案 B（快速修复）：**
- 在 Dashboard 导航中明确技能面板就是入口，无需独立页面
- 修改 E2E 测试脚本，将 `/skills` 测试改为验证 Dashboard 技能面板

**建议：** 采用方案 A，因为技能系统内容丰富（6 大分类、多角色、执行历史），独立页面体验更好。

---

### P0-2: Workspace PRD 列表为空

**现状分析**
- `workspace/page.tsx:24` 读取 URL 参数 `id`
- `workspace/page.tsx:35` 调用 `prdApi.list(projectId)`
- 后端 `prds.py:186-215` 正确支持 `project_id` 过滤

**根因（已确认）**

前后端数据结构不匹配：

```
后端返回（经 ResponseBuilder 包装）:
{
  success: true,
  data: {               <-- 这里是关键！
    items: [...],
    total: N
  }
}

前端 request() 解包后返回:
{ items: [...], total: N }   <-- 这是一个对象，不是数组！

但前端 prdApi.list 期望:
PRD[]   <-- 数组

Workspace 中:
setProjectPRDs(res || [])  // res 是 { items, total }，不是数组
// 导致 projectPRDs 变成对象，后续 .length 和 .map() 全部异常
```

**涉及文件：**
1. `apps/web/src/lib/api.ts` （修改 `prdApi.list` 返回类型和解包逻辑）
2. `apps/web/src/app/workspace/page.tsx` （适配新数据结构）

**修复方案（推荐修改前端适配）：**

**修改 1: `api.ts` 第 179-183 行**

```typescript
// 修改前
export const prdApi = {
  list: async (projectId?: string) => {
    const query = projectId ? `?project_id=${projectId}` : '';
    return request<PRD[]>(`/prds${query}`);  // 错误：期望数组
  },
```

```typescript
// 修改后
export const prdApi = {
  list: async (projectId?: string) => {
    const query = projectId ? `?project_id=${projectId}` : '';
    return request<{ items: PRD[]; total: number }>(`/prds${query}`);
  },
```

**修改 2: `workspace/page.tsx` 第 30-35 行**

```typescript
// 修改前
const [projectPRDs, setProjectPRDs] = useState<PRDSummary[]>([]);
// ...
prdApi.list(projectId).then((res) => setProjectPRDs(res || [])).catch(() => setProjectPRDs([]));
```

```typescript
// 修改后
const [projectPRDs, setProjectPRDs] = useState<PRDSummary[]>([]);
// ...
prdApi.list(projectId).then((res) => setProjectPRDs(res?.items || [])).catch(() => setProjectPRDs([]));
```

**替代方案（修改后端）：**
- 修改 `prds.py:212` 直接返回数组：`return ResponseBuilder.success(items)`
- 但会破坏现有 API 契约，且其他 list 接口（如 executions）也使用包装格式
- 不推荐

---

### P1-3: Dashboard Stats 接口 404

**现状分析**
- 仔细阅读 `dashboard/page.tsx` 全部代码
- 统计卡片数据完全由前端计算，没有任何 `fetch('/api/v1/dashboard/stats')` 调用

```typescript
// dashboard/page.tsx:67-106
// 统计基于：projects.reduce(...) + skillsApi.getExecutions()
// 无后端 stats 接口调用
```

**根因**
- E2E 测试报告描述与当前代码状态不符
- 可能早期版本有该接口，后改为前端计算
- 当前实现是合理的：Dashboard 统计不需要后端聚合

**修复方案**
- **无需修改代码**
- 在 E2E 测试报告中标记为"已前端化实现，非问题"
- 如需增强：可考虑将复杂统计（如跨时间段的趋势）放到后端

---

### P1-4: RAG 接口路径不一致

**现状分析**
- `apps/api/app/api/v1/endpoints/rag.py` 只有 `/search` endpoint
- 文档/前端可能引用了 `/query`

**根因**
- API 实现时只创建了 `/search`，未创建 `/query` 别名
- 文档与实现不同步

**涉及文件：**
1. `apps/api/app/api/v1/endpoints/rag.py` （添加 `/query` 别名）

**修复方案：**

在 `rag.py` 第 32 行后添加：

```python
@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """在 Obsidian 知识库中检索相关文档"""
    # ... 现有实现

# 添加 /query 作为 /search 的别名
@router.post("/query", response_model=SearchResponse)
async def query_documents(request: SearchRequest):
    """在 Obsidian 知识库中检索相关文档（/search 的别名）"""
    return await search_documents(request)
```

---

### P1-5: PRD Editor 页面加载失败

**现状分析**
- `prd/[id]/page.tsx:76-92` 加载逻辑看起来正确
- `prdApi.get` 解包后的数据结构匹配
- 但后端 `prds.py:404-449` 存在一个明显 bug

**根因 1: 后端变量名错误（导致章节生成失败）**

`prds.py:431`:
```python
content["chapters"][chapter] = {   # BUG: chapter 未定义！
    "title": ...,
}
```
应为 `data.chapter`。

**根因 2: 潜在的数据解析问题**
- 前端 `PRD` 类型中 `content` 字段是 `{ chapters: {...}, template: string, industry: string }`
- 后端返回的 `content` 可能为 `None`（老数据或异常数据）
- PRD Editor 未处理 `content` 为 `null` 的情况

**根因 3: `params.id` 的潜在问题**
- Next.js 14 App Router 中，客户端组件的 `params` 应该是同步的
- 但如果路由匹配失败或 ID 格式非法，可能导致异常

**涉及文件：**
1. `apps/api/app/api/v1/endpoints/prds.py` （修复 `chapter` 变量）
2. `apps/web/src/app/prd/[id]/page.tsx` （增强错误边界）

**修复方案：**

**修改 1: `prds.py` 第 431 行**
```python
# 修改前
content["chapters"][chapter] = {
# 修改后
content["chapters"][data.chapter] = {
```

**修改 2: `prd/[id]/page.tsx` 增强错误处理**

```typescript
// 修改前（第76-92行）
useEffect(() => {
  async function loadPRD() {
    try {
      const prd = await prdApi.get(params.id);
      setDocumentTitle(prd.title || "未命名 PRD");
      setContent(prd.markdown || "");
      // ...
    } catch (err) {
      setAiMessage("加载 PRD 失败: " + ...);
    } finally {
      setIsLoading(false);
    }
  }
  loadPRD();
}, [params.id]);
```

```typescript
// 修改后：增加数据校验和更详细的错误提示
useEffect(() => {
  async function loadPRD() {
    try {
      if (!params.id || typeof params.id !== 'string') {
        throw new Error('无效的 PRD ID');
      }
      const prd = await prdApi.get(params.id);
      if (!prd || !prd.id) {
        throw new Error('PRD 不存在或已被删除');
      }
      setDocumentTitle(prd.title || "未命名 PRD");
      setContent(prd.markdown || "");
      setStatus(prd.status || "draft");
      setProjectId(prd.project_id || null);
      setAiMessage("PRD 加载完成，可直接编辑、导出或继续生成章节。");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "未知错误";
      setAiMessage("加载 PRD 失败: " + message);
      setContent("");
    } finally {
      setIsLoading(false);
    }
  }
  loadPRD();
}, [params.id]);
```

**修改 3: 增加 Loading 和 Error 状态展示**

在编辑器区域增加：
```typescript
{isLoading && (
  <div className="flex items-center justify-center h-full">
    <div className="text-slate-400">加载中...</div>
  </div>
)}
{!isLoading && aiMessage.includes("失败") && (
  <div className="p-4 bg-red-50 text-red-700 rounded-lg m-4">
    {aiMessage}
    <button onClick={() => router.push('/dashboard')} className="mt-2 text-sm underline">
      返回工作台
    </button>
  </div>
)}
```

---

### P2-6: Windows 终端中文编码乱码

**现状分析**
- 后端响应 JSON 中文字段在 Windows 终端显示为 Unicode 转义（如 `\u95c7`）
- `websocket/router.py` 已设置 `PYTHONIOENCODING=utf-8`
- 但 HTTP 响应头缺少 `charset=utf-8`

**涉及文件：**
1. `apps/api/main.py` （添加响应编码中间件）

**修复方案：**

在 `main.py` 中新增响应头中间件：

```python
@app.middleware("http")
async def add_content_type_header(request: Request, call_next):
    """Ensure JSON responses have UTF-8 charset"""
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and "charset" not in content_type:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response
```

同时确保 `json.dumps` 使用 `ensure_ascii=False`（检查 prds.py 已正确使用）。

---

### P2-7: WebSocket URL 不统一

**现状分析**
- 协作 WebSocket: `/api/v1/ws/collaboration/{room}/{user}`（在 api_router 下）
- 工作流 WebSocket: `/ws/workflow/{id}`（独立 router，prefix=/ws）
- 前端需要维护两个不同的 WebSocket URL

**涉及文件：**
1. `apps/api/main.py` （统一挂载点）
2. `apps/api/app/api/v1/endpoints/websocket.py` （可能需要调整路径）
3. 前端 `.env.local` 配置

**修复方案（推荐保持兼容性的渐进方案）：**

**步骤 1: 将 workflow websocket 也挂载到 `/api/v1/ws`**

修改 `main.py`：
```python
# 保留现有 /ws 路由（向后兼容）
app.include_router(websocket_router, prefix="/ws")

# 新增统一前缀路由
app.include_router(websocket_router, prefix="/api/v1/ws")
```

**步骤 2: 前端统一使用 `NEXT_PUBLIC_WS_URL`**

```
# .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8002/api/v1/ws
```

**步骤 3: 文档更新**
- 所有 WebSocket 统一使用 `/api/v1/ws/*` 前缀
- 旧 `/ws/*` 保留但标记为 deprecated

---

### P2-8: 端口 8000 僵尸进程

**现状分析**
- uvicorn reload 模式在 Windows 上异常退出后产生僵尸进程
- 这是 uvicorn + Windows 的已知问题

**涉及文件：**
1. `scripts/kill-server.ps1` （新建）

**修复方案：**

创建 PowerShell 清理脚本：

```powershell
# scripts/kill-server.ps1
# 强制清理 Python/uvicorn 进程

Write-Host "正在查找并终止 uvicorn/python 进程..."

# 方法 1: 通过端口查找
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $port8000 | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "已终止端口 8000 进程 (PID: $($_.OwningProcess))"
    }
}

# 方法 2: 通过进程名查找
Get-Process -Name python, python3, python3.11 -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*main:app*"
} | ForEach-Object {
    Stop-Process -Id $_.Id -Force
    Write-Host "已终止进程 $($_.ProcessName) (PID: $($_.Id))"
}

Write-Host "清理完成。"
```

**同时建议：**
- 开发环境默认使用端口 8002（避免与系统服务冲突）
- 检查 `apps/api/app/core/config.py` 中默认端口配置

---

## 修复执行路线图

### Phase 1: P0 阻塞问题（立即修复，预估 3h）

| 顺序 | 问题 | 文件 | 操作 |
|------|------|------|------|
| 1 | P0-2 PRD 列表 | `api.ts`, `workspace/page.tsx` | 修改数据结构适配 |
| 2 | P0-1 Skills 页面 | 新建 `skills/page.tsx` | 创建独立技能页面 |

### Phase 2: P1 重要问题（本周修复，预估 3h）

| 顺序 | 问题 | 文件 | 操作 |
|------|------|------|------|
| 3 | P1-4 RAG 路径 | `rag.py` | 添加 `/query` 别名 |
| 4 | P1-5 PRD Editor | `prds.py`, `prd/[id]/page.tsx` | 修复变量名 + 增强错误处理 |
| 5 | P1-3 Stats | 无需修改 | 确认前端已实现 |

### Phase 3: P2 优化项（排期修复，预估 2.5h）

| 顺序 | 问题 | 文件 | 操作 |
|------|------|------|------|
| 6 | P2-7 WebSocket | `main.py` | 统一挂载点 |
| 7 | P2-6 编码 | `main.py` | 添加 charset 中间件 |
| 8 | P2-8 端口清理 | 新建 `kill-server.ps1` | 创建清理脚本 |

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 修改 `prdApi.list` 返回类型可能影响其他调用方 | 中 | 全局搜索所有 `prdApi.list` 调用，一并修改 |
| 新增 Skills 页面需要设计交互 | 低 | 复用现有组件（SkillPanel、skillStore） |
| WebSocket 路由变更影响前端连接 | 中 | 保留旧路由做兼容，渐进迁移 |
| 后端变量名修复影响运行中的生成任务 | 低 | 该 bug 会导致生成失败，修复后只会改善 |

---

## 前置检查清单

- [ ] 确认当前没有任何进行中/未保存的 PRD 编辑
- [ ] 后端服务可正常启动（端口 8002）
- [ ] 前端开发服务器可正常启动（端口 3000）
- [ ] 数据库无未完成的迁移

---

## 修复验证步骤

每修复一个问题后：
1. 重启后端服务
2. 验证前端页面正常渲染
3. 通过浏览器 DevTools Network 面板确认 API 调用成功
4. 对于 UI 改动，截图对比
5. 运行 `python e2e_browser_test.py` 验证对应场景

---

*本计划由代码分析自动生成，基于实际代码状态而非报告假设。*
