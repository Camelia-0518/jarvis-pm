# Jarvis PM E2E 测试优化报告

> **测试日期**: 2026-04-18
> **测试范围**: 前端页面渲染 + 后端 API 接口 + WebSocket 实时协作
> **测试方式**: Playwright 浏览器自动化 + Python requests 接口测试
> **测试环境**: Windows 11 / Chrome 147 / FastAPI (port 8002) + Next.js (port 3000)

---

## 一、测试概述

本次端到端测试覆盖 Jarvis PM 的核心用户路径：

```
首页 → Dashboard → Workspace → PRD Editor → Templates → API Docs
        ↓              ↓              ↓
      项目列表      工具箱+PRD     实时协作编辑
```

**总体结论**: 核心链路（项目创建、PRD 生成、AI 技能执行、知识库检索）已跑通，但前端页面路由、API 路径一致性、数据联调存在若干问题，影响用户体验。

---

## 二、问题清单（按优先级排序）

### 🔴 P0 - 阻塞问题（立即修复）

#### 1. `/skills` 路由 404

| 项目 | 内容 |
|------|------|
| **现象** | 访问 `http://localhost:3000/skills` 返回 404 页面 |
| **根因** | `apps/web/src/app/` 下不存在 `skills/` 目录，该页面未实现 |
| **影响** | Dashboard 顶部导航的"技能面板"入口无法使用 |
| **修复建议** | 实现 `app/skills/page.tsx`，复用 `useSkillStore` + `skillsApi.getAll()` 展示技能列表卡片；或移除导航入口改为 `/dashboard/skills` 子路由 |
| **工作量** | 2-4h |

#### 2. Workspace 页面 PRD 列表为空

| 项目 | 内容 |
|------|------|
| **现象** | `/workspace` 页面右侧 PRD 文档区显示"暂无 PRD 文档"，但 Dashboard 显示项目有 PRD |
| **根因** | Workspace 页面未携带 `project_id` 查询参数，调用 `prdApi.list()` 时未过滤项目，或项目切换逻辑未生效 |
| **影响** | 用户进入工作区后无法看到已创建的 PRD，阻断编辑流程 |
| **修复建议** | ① URL 改为 `/workspace?project_id=xxx` 模式；② 页面加载时从 store 或 URL 读取当前项目 ID；③ 调用 `prdApi.list({ project_id })` 而非全量查询 |
| **工作量** | 2-3h |

---

### 🟡 P1 - 重要问题（本周修复）

#### 3. Dashboard Stats 接口 404

| 项目 | 内容 |
|------|------|
| **现象** | 前端 Dashboard 调用 `GET /api/v1/dashboard/stats` 返回 404 |
| **根因** | 后端未实现该端点，Dashboard 页面的"AI 助手使用统计"区域数据为写死或空值 |
| **影响** | 统计卡片（本月节省时间/PRD生成数/评审准备/站会报告）无法展示真实数据 |
| **修复建议** | 后端新增 `GET /api/v1/dashboard/stats` 接口，聚合以下数据：<br>- 本月技能执行次数（按 skill_id 分组）<br>- 生成的 PRD 总数<br>- 节省时间的估算值（执行次数 x 平均节省时长）<br>- 各状态 PRD 数量 |
| **工作量** | 4-6h（前后端各半）|

#### 4. RAG 接口路径不一致

| 项目 | 内容 |
|------|------|
| **现象** | 文档标注为 `/api/v1/rag/query`，实际可用路径为 `/api/v1/rag/search`，`/query` 返回 404 |
| **根因** | API 实现与文档/前端调用不匹配 |
| **影响** | 前端如按文档调用会失败；用户无法使用知识库问答功能 |
| **修复建议** | 方案 A（推荐）: 后端同时支持 `/query` 和 `/search` 两个路径，指向同一 handler；<br>方案 B: 统一修改前端调用路径为 `/search`，并更新 API 文档 |
| **工作量** | 30min |

#### 5. PRD Editor 页面加载失败

| 项目 | 内容 |
|------|------|
| **现象** | `/prd/{id}` 页面无法加载具体 PRD 内容，E2E 测试捕获到错误截图 |
| **根因** | 可能原因：① PRD ID 传递错误；② 页面组件未正确处理异步加载状态；③ API 返回数据结构变更但前端未适配 |
| **影响** | 用户无法编辑已生成的 PRD，核心功能不可用 |
| **修复建议** | ① 确认 `GET /api/v1/prds/{id}` 返回数据结构（当前返回 `content.chapters` 嵌套结构）；<br>② 检查 `app/prd/[id]/page.tsx` 中数据解析逻辑；<br>③ 增加 loading 和 error 边界处理 |
| **工作量** | 2-4h |

---

### 🟢 P2 - 优化项（排期修复）

#### 6. Windows 终端中文编码乱码

| 项目 | 内容 |
|------|------|
| **现象** | API 返回的中文内容在 curl/Windows 终端显示为乱码（如 `\u95c7\udc80\u59f9`）|
| **根因** | Windows 默认使用 GBK 编码，与 UTF-8 输出不兼容；Python 3.11 Windows 版 stdout 编码问题 |
| **影响** | 调试困难，日志可读性差，但不影响实际功能 |
| **修复建议** | ① 后端响应头增加 `charset=utf-8`；<br>② Python 脚本开头添加 `chcp 65001`；<br>③ 使用 PowerShell 7+ 替代 cmd；<br>④ 关键日志输出到文件而非终端 |
| **工作量** | 1-2h |

#### 7. WebSocket URL 配置潜在不一致

| 项目 | 内容 |
|------|------|
| **现象** | 测试中发现两个 WebSocket 路径：<br>- 协作 WebSocket: `/api/v1/ws/collaboration/{room}/{user}`（可用）<br>- 工作流 WebSocket: `/ws/workflow/{id}`（独立 router）|
| **根因** | `websocket.py` 挂载在 `api_router`（prefix=/api/v1），而 `websocket_router` 单独挂载（prefix=/ws），路径前缀不统一 |
| **影响** | 前端配置容易混淆，后期维护成本高 |
| **修复建议** | 统一 WebSocket 前缀为 `/api/v1/ws/*`，将 workflow websocket 合并到同一 router 下；前端 `.env.local` 只配置一个 `NEXT_PUBLIC_WS_URL` |
| **工作量** | 1-2h |

#### 8. 端口 8000 僵尸进程

| 项目 | 内容 |
|------|------|
| **现象** | PID 37660 的 python3.11 进程占用 8000 端口，taskkill / Stop-Process 均无法终止 |
| **根因** | uvicorn reload 模式产生的守护进程在异常退出后成为僵尸进程 |
| **影响** | 开发环境需使用 8002 等替代端口，增加配置复杂度 |
| **修复建议** | ① 编写 `scripts/kill-server.ps1` 脚本，使用 `wmic process where "name='python.exe' and commandline like '%main%app%'" delete` 强制清理；<br>② 推荐：使用 `--port 8002` 作为开发端口，8000 留给生产；<br>③ 长期：使用 Docker Compose 统一管理进程生命周期 |
| **工作量** | 30min |

---

## 三、修复路线图

```
Week 1 (立即)
├── [P0] 移除/修复 skills 导航入口
├── [P0] 修复 Workspace PRD 列表查询逻辑
├── [P1] 统一 RAG 接口路径 (/query 别名)
└── [P2] 编写 kill-server.ps1 端口清理脚本

Week 2
├── [P1] 实现 Dashboard Stats 后端接口
├── [P1] 联调 Dashboard 统计卡片真实数据
├── [P1] 修复 PRD Editor 页面加载逻辑
└── [P2] 统一 WebSocket 路由前缀

Week 3
├── [P2] 解决 Windows 终端 UTF-8 编码问题
├── [P2] 补充 Skills 页面（或确认移除）
└── [P2] E2E 测试脚本纳入 CI（可选）
```

---

## 四、E2E 测试脚本

本次测试使用的 Playwright 脚本已保存至：
- `C:\Users\13400\e2e_browser_test.py`
- 截图输出：`C:\Users\13400\jarvis_pm_e2e_screenshots\`

### 运行方式

```bash
# 1. 确保前后端服务已启动
# 后端: http://127.0.0.1:8002
# 前端: http://localhost:3000

# 2. 运行测试
python C:\Users\13400\e2e_browser_test.py

# 3. 查看截图
start C:\Users\13400\jarvis_pm_e2e_screenshots
```

### 建议纳入的后续 E2E 场景

| 场景 | 步骤 |
|------|------|
| 完整 PRD 创建流 | Dashboard → 新建项目 → 新建 PRD → AI 生成内容 → 导出 Markdown |
| 实时协作流 | 打开 PRD → WebSocket 连接 → 光标同步 → 发送聊天消息 |
| 技能执行流 | 选择技能 → 填写参数 → 异步执行 → 轮询结果 → 查看执行历史 |
| 模板使用流 | Templates → 选择医疗模板 → 预填充表单 → 生成 PRD |

---

## 五、附录：环境信息

| 项目 | 版本/值 |
|------|---------|
| OS | Windows 11 Home China 10.0.26200 |
| Python | 3.11.2544 |
| Node.js | v20.18.0 |
| Next.js | 14.2.5 |
| FastAPI | latest (via requirements.txt) |
| Playwright | 1.51.x |
| Chromium | 147.0.7727.15 |
| 后端端口 | 8002 (因 8000 被占用) |
| 前端端口 | 3000 |
| 数据库 | SQLite (dev) |
| 缓存 | 内存缓存 (Redis 未启动) |
| LLM | Kimi k2.6-code-preview |

---

*报告生成时间: 2026-04-18*
*测试执行: Claude Code + Playwright + Python requests*
