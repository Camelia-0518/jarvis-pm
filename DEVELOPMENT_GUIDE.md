# Jarvis PM 开发规范与流程指南

> 基于 ECC (Everything Claude Code) 开发工作流规范，结合 Jarvis PM 项目特性定制。

---

## 1. 本地开发环境启动

### 1.1 端口约定（强制）

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 (Next.js) | `http://localhost:3000` | 开发服务器 |
| 后端 (FastAPI) | `http://127.0.0.1:8000` | API 服务 + Swagger 文档 |

**⚠️ 历史坑点**：前端 `apps/web/.env.local` 和 `src/lib/api.ts` 曾错误配置为 `8001`，导致全站 API `fail to fetch`。已修正为 `8000`，后续若调整端口必须**前后端同步修改**。

### 1.2 启动步骤

```powershell
# 1. 启动后端
cd apps/api
./venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. 启动前端（新开终端）
cd apps/web
npm run dev
```

首次启动或清理后需重装依赖：
```powershell
# 后端（Python 3.11+）
cd apps/api
python -m venv venv
./venv/Scripts/python -m pip install -r requirements.txt

# 前端（Node 20+）
cd apps/web
npm install
```

---

## 2. 单用户模式说明

Jarvis PM 当前为**单用户本地工具**，认证相关逻辑已简化：
- 登录/注册为 no-op，直接返回空 token
- 所有 API 请求**无需携带 Authorization Header**
- 后端 `/auth/me` 返回固定测试用户

这意味着：
- 不要在前端写 token 刷新逻辑
- 不要在后端为本地开发配置复杂的 JWT 校验
- 若未来改为多用户，需在 PRD 阶段单独设计 Auth 模块

---

## 3. API 变更前的 Test-First 流程

根据 ECC `API Integration Test-First` 规则，**修改任何 API 端点或 URL 配置前，必须先做最小连通性测试**。

### 3.1 修改配置前

```bash
# 测试后端是否存活
curl -s http://127.0.0.1:8000/health | python -m json.tool

# 测试关键端点格式
curl -s http://127.0.0.1:8000/api/v1/projects | python -m json.tool
```

期望返回包含 `"success": true` 的标准包装格式：
```json
{
  "success": true,
  "data": [],
  "error": null,
  "meta": { ... }
}
```

### 3.2 修改配置后

```bash
# 验证前端环境变量生效（需重启前端）
curl -s -I http://localhost:3000

# 浏览器控制台检查 Network 面板，确认请求地址正确
```

---

## 4. 修改后的自动验证清单

根据 ECC `Post-Edit Auto-Validation` 规则，**每修改代码文件后必须执行对应验证**。

### 4.1 前端 (TypeScript / Next.js)

```powershell
cd apps/web
npx tsc --noEmit
```

- **零错误通过**才可继续提交或汇报完成
- 若引入新依赖，额外运行：`npm run build`（验证生产构建）

### 4.2 后端 (Python / FastAPI)

```powershell
cd apps/api
./venv/Scripts/python -m py_compile app/main.py
./venv/Scripts/python -m pytest tests/ -q
```

- `py_compile` 用于快速语法检查
- `pytest` 用于运行单元/集成测试
- 修改路由后，额外检查 Swagger 文档是否正常渲染：`http://127.0.0.1:8000/docs`

### 4.3 修改 API 契约（前后端都改时）

1. 改后端 → `curl` 测试新端点
2. 改前端 `lib/api.ts` → `npx tsc --noEmit`
3. 浏览器端到端验证对应页面功能

---

## 5. API 错误处理规范

### 5.1 前端 (`src/lib/api.ts`)

统一使用 `request<T>()` 辅助函数：
- **超时控制**：默认 30s，AI 接口（`/ai/*`、skills execute、workflow execute）180s ~ 360s
- **错误分类**：
  - `TypeError` / `Failed to fetch` → "网络连接失败：无法连接到后端服务"
  - `AbortError` → "请求超时，请稍后重试"
  - 后端返回 `!response.ok` → 提取 `detail` 或 `error.message`
  - 后端 wrapper `success: false` → 提取 `error.message`
- **导出 `ApiError` 类**：调用方可根据 `status` 和 `code` 做二次处理

### 5.2 后端 (`app/core/exceptions.py`)

所有异常通过 `register_exception_handlers(app)` 统一捕获，返回标准格式：
```json
{
  "success": false,
  "error": {
    "code": "RES_001",
    "message": "Resource not found"
  },
  "meta": { "status_code": 404 }
}
```

新增业务异常时，继承 `AppException` 并注册 handler，**禁止在 endpoint 内直接 `raise HTTPException`**。

---

## 6. Windows 环境特需注意事项

根据 ECC `Windows Compatibility Priority` 规则：

1. **路径分隔符**：项目内使用正斜杠或 Node/Python 自动处理，但 PowerShell/Bash 混用时需注意引号
2. **进程管理**：
   - `npm run dev` 占用 3000 端口，若重启失败检查 `netstat -ano | findstr :3000`
   - 杀进程用 `powershell -Command "Stop-Process -Id <PID> -Force"`
3. **虚拟环境**：Python venv 的激活脚本在 Windows 下为 `venv\Scripts\python`，非 `venv/bin/python`
4. **文件锁**：`.next` / `node_modules` 可能因进程未退出导致 `EPERM`，重启前确保旧进程已终止

---

## 7. 常见故障排查

### 7.1 前端页面报 "Failed to fetch"

排查清单：
1. 后端是否已启动？`curl http://127.0.0.1:8000/health`
2. 前端 `.env.local` 和 `src/lib/api.ts` 的端口是否为 `8000`？
3. 浏览器控制台 Network 面板，确认请求地址不是 `localhost:8001`
4. 是否有其他程序占用了 8000 端口？

### 7.2 `npx tsc --noEmit` 报错

- 若报类型不匹配，检查 `lib/api.ts` 中的 `request<T>` 泛型参数
- 若报模块找不到，运行 `npm install` 后再试

### 7.3 后端启动报数据库错误

- 当前使用 SQLite（零配置），数据库文件 `jarvis_pm.db` 会在 `apps/api` 目录自动创建
- 若迁移失败，可删除 `jarvis_pm.db` 重新启动（**仅开发环境**）

---

## 8. 提交前检查清单

- [ ] 修改文件已做对应验证（tsc / pytest / curl）
- [ ] 前端 `http://localhost:3000` 可正常访问核心页面
- [ ] 后端 `http://127.0.0.1:8000/docs` Swagger 正常
- [ ] 至少一个 API 端点通过浏览器端到端验证
- [ ] 无 `console.log` 或 `print()` 调试残留（本地调试例外，提交前清理）

---

*文档版本: v1.0*  
*生效日期: 2026-04-15*  
*关联规范: `~/.claude/rules/common/development-workflow.md`*
