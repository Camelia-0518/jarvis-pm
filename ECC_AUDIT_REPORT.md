# Jarvis PM ECC 合规检查报告

> 检查日期: 2026-04-15  
> 依据规范: `~/.claude/rules/common/`, `~/.claude/rules/typescript/`, `~/.claude/rules/python/`, `~/.claude/rules/web/`  
> 检查范围: `apps/web/` (Next.js/TS), `apps/api/` (FastAPI/Python), 项目基础设施

---

## 执行摘要

| 维度 | 得分 | 关键问题 |
|------|------|----------|
| 前端代码规范 | ⚠️ 55/100 | `any` 泛滥、console.log 残留、0 前端测试、超大文件 |
| 后端代码规范 | ⚠️ 60/100 | 19 个文件含 `print()`、超大模块、类型注解不完整 |
| 安全合规 | 🔴 40/100 | `.env` 硬编码真实 API Key、`dangerouslySetInnerHTML`、无 CSP |
| 基础设施 | 🔴 35/100 | 无 CI/CD、无 E2E 测试、无前端单元测试框架 |
| **综合** | **⚠️ 48/100** | **需立即修复安全问题，分阶段补测试和规范** |

---

## 1. 严重问题 (Critical) — 需立即修复

### 🔴 C1. `.env` 文件硬编码真实 API Key

**问题描述**: `apps/api/.env` 中明文存储了有效的 Kimi API Key。
```
KIMI_API_KEY=sk-kimi-bC5CRVbaxjfZwE37epUKMNFxTzpwgd3cQGmqXpKj5d04dqQPktfiuPDxD8VugoAV
```

**违反规则**:
- `common/security.md`: "NEVER hardcode secrets in source code"
- `typescript/security.md`: "NEVER: Hardcoded secrets"
- `python/security.md`: "ALWAYS use environment variables or a secret manager"

**整改方案**:
1. **立即轮换密钥**（到 Kimi 控制台吊销该 key，生成新 key）
2. 将 `.env`、`.env.local`、`.env.test` 加入 `.gitignore`（若尚未加入）
3. 提供 `.env.example` 作为模板（仅含空值/占位符）
4. 在 `app/core/config.py` 增加启动时必填校验，缺失则抛错

---

### 🔴 C2. 前端存在 `dangerouslySetInnerHTML`

**问题描述**: 发现 2 处未经验证的 HTML 注入：
- `apps/web/src/app/workspace/page.tsx:424`
- `apps/web/src/components/skills/SkillPanel.tsx`

内容直接来自后端返回的 markdown，未经过本地 sanitizer 处理。

**违反规则**:
- `web/security.md`: "Avoid `innerHTML` / `dangerouslySetInnerHTML` unless sanitized first"
- `common/security.md`: "XSS prevention (sanitized HTML)"

**整改方案**:
1. 安装 `dompurify` + `@types/dompurify`
2. 所有 `dangerouslySetInnerHTML` 必须通过 `DOMPurify.sanitize()` 处理
3. 或改用 `react-markdown` 等安全渲染方案（项目中已依赖 `react-markdown`，优先使用）

---

### 🔴 C3. 后端大量 `print()` 语句

**问题描述**: 排除 `venv` 后，仍有 **19 个 Python 文件** 包含 `print()` 语句，严重违反 ECC Python 规范。

**主要分布**:
- `app/main.py` (4 处启动/关闭打印)
- `app/services/ai_service.py` (2 处)
- `app/services/prd_generator.py` (9 处)
- `app/core/cache.py` (5 处)
- `app/agents/**/*.py` (多处错误打印)

**违反规则**:
- `python/hooks.md`: "Warn about `print()` statements in edited files (use `logging` module instead)"
- `common/coding-style.md`: 未使用 proper logging libraries

**整改方案**:
1. 全部替换为 `logging.getLogger(__name__)`
2. `main.py` 的启动信息改用 `logging.info()`
3. 错误处理中的 `print(f"Error: {e}")` 改用 `logger.exception()` 或 `logger.error()`
4. 配置 `~/.claude/settings.json` 的 stop hook 拦截 `print()`

---

## 2. 高优先级问题 (High)

### 🟠 H1. TypeScript `any` 类型泛滥

**问题描述**: 扫描到 **25+ 处** 显式 `any`，主要分布在：
- `catch (err: any)` 块（`battle/page.tsx`, `prd/[id]/page.tsx`, `workspace/page.tsx` 等）
- API 响应变量（`let res: any`, `const inputs: any = {}`）
- Store 定义（`[key: string]: any`, `data: any`）
- 组件 props（`...props}: any` in `ChatInterface.tsx`）

**违反规则**:
- `typescript/coding-style.md`: "Avoid `any` in application code. Use `unknown` for external or untrusted input, then narrow it safely."

**整改方案**:
1. **Catch 块统一改为 `unknown`**:
   ```typescript
   } catch (err: unknown) {
     const message = err instanceof Error ? err.message : 'Unknown error';
   }
   ```
2. API 层定义明确的 DTO 类型，移除 `res: any`
3. `ChatInterface.tsx` 的 markdown code block props 定义具体类型
4. Store 中的动态字段使用 `Record<string, unknown>` 或明确联合类型

---

### 🟠 H2. 生产代码中存在 `console.log`

**问题描述**: 7 处 `console.log` / `console.error` 残留：
- `workspace/page.tsx:47`
- `chat/ChatInterface.tsx:188`
- `ExportPanel.tsx:86, 90`
- `useWebSocket.ts:67, 81`
- `versionStore.ts:51`

**违反规则**:
- `typescript/hooks.md`: "console.log audit: Check all modified files for `console.log` before session ends"
- `common/coding-style.md`: "No `console.log` statements in production code"

**整改方案**:
1. 全部移除或替换为 `ApiError` 的用户友好提示
2. WebSocket 连接日志仅在 `DEBUG=true` 时输出
3. 在 `eslint.config.mjs` 增加 `no-console` 规则（允许 `console.error` 仅在 `*.test.*` 中）

---

### 🟠 H3. 超大文件（严重超出 ECC 800 行上限）

**违反规则**:
- `common/coding-style.md`: "Files are focused (<800 lines)"

**后端 Monster Files**:
| 文件 | 行数 | 拆分建议 |
|------|------|----------|
| `app/services/api_generator.py` | 1,529 | 拆分为 `parser.py`, `generator.py`, `writer.py` |
| `app/services/component_generator.py` | 1,498 | 按组件类型拆分 |
| `app/services/prototype_generator.py` | 1,296 | 拆分为 `layout.py`, `component.py`, `exporter.py` |
| `app/services/skill_processor.py` | 950 | 拆分为 `loader.py`, `executor.py`, `formatter.py` |
| `app/services/skill_processor_enhanced.py` | 779 | 与 `skill_processor.py` 合并或功能拆分 |
| `app/agents/templates.py` | 635 | 按 skill 类别拆分为多个 JSON/YAML 文件 |

**前端超大文件**:
| 文件 | 字节 | 拆分建议 |
|------|------|----------|
| `src/services/skills/registry.ts` | 33,664 | 拆分为 `registry.ts`, `metadata.ts`, `validators.ts` |
| `src/components/skills/SkillPanel.tsx` | 25,590 | 拆分为 `SkillCard.tsx`, `SkillForm.tsx`, `SkillResult.tsx` |
| `src/lib/api.ts` | 20,117 | 按领域拆分为 `api/projects.ts`, `api/prds.ts`, `api/tools.ts` 等 |
| `src/app/dashboard/page.tsx` | 22,787 | 提取 `ProjectCard.tsx`, `StatCard.tsx`, `SkillPanel.tsx` |

**整改方案**:
1. 对 >800 行的文件建立拆分计划
2. 优先拆分 `api.ts`（影响面最广）和 `api_generator.py`（最难维护）
3. 新功能开发时严格遵循 <400 行目标

---

### 🟠 H4. 测试覆盖率严重不足

**问题描述**:
- **前端**: **0 个**单元测试文件（`.test.ts` / `.spec.ts`）
- **后端**: 16 个测试文件，但无法确认覆盖率是否达到 80%
- **E2E**: 无 Playwright 配置

**违反规则**:
- `common/testing.md`: "Minimum Test Coverage: 80%"
- `common/development-workflow.md`: "TDD Approach — Write tests first (RED), Implement to pass tests (GREEN)"
- `web/testing.md`: "Use Playwright as the E2E testing framework"

**整改方案**:
1. **前端**: 安装 `vitest` + `@testing-library/react` + `@testing-library/jest-dom`
   - 优先覆盖: `lib/api.ts`（网络层）、`stores/projectStore.ts`（状态层）、`lib/utils.ts`（工具函数）
2. **后端**: 运行 `pytest --cov=app --cov-report=term-missing` 获取基线
   - 对覆盖率 <80% 的模块补测试
3. **E2E**: 安装 `@playwright/test`
   - 优先覆盖: 首页 → Dashboard → 新建项目 → 新建 PRD → 工具调用

---

## 3. 中优先级问题 (Medium)

### 🟡 M1. 前端服务端状态管理不当

**问题描述**: Zustand store（`projectStore`, `skillStore` 等）直接缓存了 API 返回的服务端状态，未使用 TanStack Query / SWR。

**违反规则**:
- `web/patterns.md`: "Do not duplicate server state into client stores"
- `web/patterns.md` State Management 表格: "Server state → TanStack Query, SWR, tRPC"

**整改方案**:
1. 引入 `@tanstack/react-query`
2. 将 `projectApi.list()`、`projectApi.get()` 等读取操作迁移到 React Query
3. Zustand 仅保留真正的客户端状态（如 modal 开关、当前选中 tab）

---

### 🟡 M2. React.FC 使用

**问题描述**: 发现 2 个文件仍使用 `React.FC`。

**违反规则**:
- `typescript/coding-style.md`: "Do not use `React.FC` unless there is a specific reason to do so"

**整改方案**: 改为常规函数组件 + 显式 Props interface。

---

### 🟡 M3. 缺少 CI/CD 和自动化检查

**问题描述**: 项目根目录无 `.github/workflows/`，无 pre-commit hooks。

**违反规则**:
- `common/development-workflow.md`: "Pre-Review Checks — Verify all automated checks (CI/CD) are passing"
- `common/hooks.md`: PostToolUse hooks（auto-format, type check, lint）

**整改方案**:
1. 创建 `.github/workflows/ci.yml`，包含：
   - `apps/web`: `npm install`, `npx tsc --noEmit`, `npm run lint`
   - `apps/api`: `pip install -r requirements.txt`, `pytest`, `python -m py_compile` 批量检查
2. 配置 `.pre-commit-config.yaml` 或 husky（前端用 `lint-staged`）

---

### 🟡 M4. 缺少安全响应头与 CSP

**问题描述**: FastAPI 未配置 `Strict-Transport-Security`、`X-Content-Type-Options`、`CSP` 等安全头。

**违反规则**:
- `web/security.md`: HTTPS and Headers 配置清单
- `web/security.md`: "Always configure a production CSP"

**整改方案**:
1. 使用 `fastapi.middleware.trustedhost` + 自定义 middleware 添加安全响应头
2. 生产环境配置 CSP（本地开发可宽松）

---

### 🟡 M5. 代码中存在注释掉的死代码

**问题描述**: 扫描发现多处大段被注释掉的代码（如 `skill_processor_enhanced.py`、旧版 `start.py` 等）。

**违反规则**:
- `common/coding-style.md`: "Files are focused", "No copy-paste implementation drift"

**整改方案**:
1. 删除所有超过 10 行的注释块
2. 若需保留历史版本，通过 Git 历史回溯，不要留在代码中

---

## 4. 当前做得好的地方

| 实践 | 说明 |
|------|------|
| ✅ API 响应标准化 | 后端统一返回 `{success, data, error, meta}` |
| ✅ 异常处理框架 | `app/core/exceptions.py` 已建立完善的异常分层 |
| ✅ Zustand 不可变更新 | Store 中使用 spread 而非 mutation |
| ✅ 后端 pytest 配置 | `pytest.ini` 已配置 asyncio_mode 和 markers |
| ✅ 端口和 CORS 已修复 | 前后端端口统一为 8000，请求不再 fail to fetch |

---

## 5. 分阶段整改计划

### 阶段 1: 安全与可运行性（本周内）
- [ ] 轮换 `.env` 中的 KIMI_API_KEY，并将 `.env` 移出版本控制
- [ ] 移除/替换所有 `dangerouslySetInnerHTML`，改用 `react-markdown`
- [ ] 将所有 `print()` 替换为 `logging`
- [ ] 移除所有 `console.log`
- [ ] 修复 `any` 类型的 catch 块（约 15 处，批量替换）

### 阶段 2: 测试与基础设施（2 周内）
- [ ] 前端安装 `vitest` + `@testing-library/react`，覆盖 `lib/api.ts`
- [ ] 后端运行覆盖率基线测试，补齐 <80% 的模块
- [ ] 安装 `playwright`，编写 3 条核心 E2E 用例
- [ ] 建立 GitHub Actions CI

### 阶段 3: 架构优化（1 个月内）
- [ ] 拆分超大文件（`api.ts`, `api_generator.py`, `skill_processor.py`）
- [ ] 引入 TanStack Query 管理服务端状态
- [ ] 添加安全响应头 middleware
- [ ] 配置 pre-commit hooks

---

## 6. 关键检查命令速查

```bash
# 前端类型检查
cd apps/web && npx tsc --noEmit

# 后端语法检查
cd apps/api
find app -name "*.py" ! -path "*/venv/*" -exec ./venv/Scripts/python -m py_compile {} +

# 后端覆盖率
cd apps/api && ./venv/Scripts/python -m pytest --cov=app --cov-report=term-missing

# 查找 console.log
find apps/web/src -name "*.ts" -o -name "*.tsx" | xargs grep -n "console\."

# 查找 print()
find apps/api/app -name "*.py" | xargs grep -n "print("

# 查找 any
find apps/web/src -name "*.ts" -o -name "*.tsx" | xargs grep -n ": any"
```

---

*报告版本: v1.0*  
*检查人: Claude (ECC 规范引擎)*
