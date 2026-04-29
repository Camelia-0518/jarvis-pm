# Jarvis PM 系统分析报告

> 基于 product-analyst / ux-designer / tech-architect / qa-engineer 四重视角的深度审查
> 模拟用户旅程：首页 → 仪表盘 → 创建项目 → 工作台 → 生成 PRD → 工具分析 → 评审材料

---

## 一、Product Analyst 视角：产品流程断点

### 🔴 P0：技能链（Skill Chain）是"假功能"
```
用户路径：仪表盘点击"从 0 开发新功能" → 期望：自动执行 头脑风暴→PRD→评审准备
实际结果：只是跳转到 /workspace，没有任何链式执行逻辑
```
**影响**：产品核心卖点（"10 分钟完成 PRD"）无法兑现，用户会感知到功能不完整。
**建议**：在后端新增 `/workflows/execute-chain` 端点，前端传入 chain_id 后轮询执行状态。

### 🔴 P0：工作台工具箱严重缩水
后端支持 7+ 个工具（user-research, stakeholder, data-analysis, competitor, review, prototype, memory），前端只展示了 3 个（competitor, review, prototype）。
**影响**：用户看不到产品的完整能力，付费转化率受影响。
**建议**：工具箱改为可配置/可折叠的面板，完整展示所有工具。

### 🟡 P1：PRD 生成没有"草稿"概念
用户在 PRD Wizard 中填写信息后，如果中途刷新页面，所有输入丢失。
**建议**：使用 localStorage 自动保存表单状态，或后端支持 draft PRD。

### 🟡 P1：首页缺乏信任要素
首页是纯静态文案，没有：用户案例、生成示例、可信背书、实时 Demo。
**建议**：增加"查看示例 PRD"入口，嵌入一个只读 PRD 预览作为信任锚点。

---

## 二、UX Designer 视角：交互体验摩擦

### 🔴 P0：错误处理使用 `alert()`
代码位置：`workspace/page.tsx:53`, `dashboard/page.tsx:473`, `dashboard/page.tsx:516`
```typescript
alert("删除失败: " + (err instanceof Error ? err.message : "未知错误"));
alert("反馈已提交，感谢你的建议！");
alert("提交失败，请重试");
```
**影响**：alert 会阻塞整个页面交互，移动端体验极差，且无法展示详细错误信息。
**建议**：统一使用 toast/notification 组件（如 sonner），所有 API 错误走统一错误边界。

### 🔴 P0：超长页面组件，职责混乱
| 文件 | 行数 | 问题 |
|------|------|------|
| `dashboard/page.tsx` | 773 | 混合了项目列表、统计面板、反馈弹窗、新建项目弹窗、技能面板 |
| `workspace/page.tsx` | 795 | ToolPanel 内嵌了 7 个工具的 UI + 逻辑 + 状态 |
| `prd/[id]/page.tsx` | 预估 500+ | （未读，但从路由结构推断） |

**影响**：代码难以维护，一个 bug 可能牵一发而动全身；新功能开发成本高。
**建议**：按功能拆分为独立组件（FeedbackModal、ProjectCard、ToolPanel 等）。

### 🟡 P1：工具结果展示体验差
```typescript
// workspace/page.tsx:716
<div className="... overflow-auto max-h-96">
```
竞品分析生成的 Markdown 报告被限制在 384px 高度内，用户需要在小窗口内滚动阅读长文档。
**建议**：工具结果支持"全屏查看"、"导出 Markdown"、"追加到 PRD"（已有但隐藏过深）。

### 🟡 P1：没有骨架屏（Skeleton）
所有加载状态都是文字"加载中..."，在慢网络下用户无法感知内容结构。
**建议**：为 ProjectCard、PRD 列表、统计面板增加骨架屏占位。

### 🟡 P1：删除操作没有撤销
项目和 PRD 删除使用 `window.confirm`，删除后立即从 UI 移除，没有撤销机会。
**建议**：使用"软删除 + Toast 撤销按钮"模式，或至少增加 5 秒延迟删除动画。

### 🟢 P2：反馈评分交互不直观
评分使用 ★ 按钮，但没有 hover 预览效果，用户不知道当前悬停在几颗星上。

---

## 三、Tech Architect 视角：架构与稳定性风险

### 🔴 P0：内存泄漏风险 — 执行记录永不清理
```python
# workflows.py:20
execution_records: Dict[str, dict] = {}
```
每次执行工作流都会追加记录，无 TTL、无容量上限。长期运行会导致内存 OOM。
**建议**：引入 `cachetools.TTLCache(maxsize=1000, ttl=3600)` 或 Redis 存储。

### 🔴 P0：AI 服务调用无熔断/重试
```python
# tools.py 多处
content = await ai_service.chat(prompt, {"max_tokens": 2000})
```
如果 Kimi/OpenAI 服务超时或 5xx，整个端点直接 500 报错，用户等待 120s 后失败。
**建议**：封装 `ai_service.chat_with_retry()`，配置指数退避（最多 3 次，每次 2s 退避），超时降至 30s。

### 🟡 P1：前端 API 超时 120s 过长
```typescript
// api.ts:47
const timeoutMs = options.timeoutMs ?? 120000;
```
用户等待 2 分钟没有反馈会觉得系统卡死。实际上大多数 AI 调用应在 30-60s 内完成。
**建议**：按端点配置超时（列表查询 5s，AI 生成 60s，流式 SSE 不设超时）。

### 🟡 P1：分页缺失导致大数据查询性能下降
- `/templates` 默认 limit=50，但没有上限校验（虽然 Pydantic 有 le=100）
- `/projects` 的 PRD count 使用 N+1 查询（每个项目单独 count PRD）
**建议**：Projects 列表使用 JOIN + COUNT 子查询优化。

### 🟡 P1：WebSocket 心跳间隔 30s 过长
```python
# websocket.py:162
ping_interval = 30
```
协作场景中，30s 心跳意味着用户掉线后最多 60s 才能检测到（2 个周期）。
**建议**：降至 10s，配合 3 次超时判定（30s 总超时）。

### 🟢 P2：前端状态管理混合
同时使用 useState（局部）和 Zustand（全局），部分数据在两者之间同步（如 projectPRDs 既在 workspace 的 useState 中，又依赖 fetchProject）。
**建议**：将项目相关的 CRUD 操作统一收拢到 ProjectStore。

---

## 四、QA Engineer 视角：质量与测试缺口

### 🔴 P0：核心业务 PRD 模块仅 15% 覆盖率
`prds.py` 604 行代码，511 行未测试。包含：生成、流式生成、导出、版本管理、差异对比。
**风险**：PRD 是产品核心，任何改动都可能导致生产事故。

### 🟡 P1：缺少端到端用户旅程测试
现有测试覆盖了独立端点，但没有覆盖完整流程：
```
创建项目 → 进入工作台 → 生成 PRD → 追加竞品分析 → 导出 PDF
```
**建议**：添加 Playwright E2E 测试覆盖 golden path。

### 🟡 P1：竞态条件风险
```typescript
// dashboard/page.tsx:70-72
useEffect(() => { fetchProjects(); }, [fetchProjects]);
useEffect(() => { fetchSkillData(); }, [projects]); // 依赖 projects
```
如果 fetchProjects 失败，fetchSkillData 仍会执行（projects 为空数组，不触发重试）。

### 🟢 P2：没有前端单元测试覆盖交互逻辑
- ToolPanel 的候选竞品确认流程
- PRD Wizard 的表单验证
- Dashboard 的模态框打开/关闭
这些交互逻辑目前仅通过 E2E 覆盖，缺乏快速反馈的单元测试。

---

## 五、优化优先级矩阵

| 优先级 | 问题 | 影响 | 工作量 |
|--------|------|------|--------|
| P0 | 技能链假功能 | 核心卖点无法兑现 | 中 |
| P0 | alert 错误处理 | 用户体验极差 | 小 |
| P0 | 内存泄漏 | 生产环境稳定性 | 小 |
| P0 | AI 调用无熔断 | 服务雪崩风险 | 中 |
| P1 | 工作台工具箱缩水 | 产品价值感知不足 | 小 |
| P1 | 组件拆分 | 维护成本 | 中 |
| P1 | PRD 覆盖率 15% | 核心功能风险 | 大 |
| P2 | 骨架屏 | 体验打磨 | 小 |
| P2 | WebSocket 心跳 | 协作实时性 | 小 |

---

## 六、建议的下一步

**立即执行（本周）**：
1. 替换所有 `alert()` 为 toast 通知
2. 为 `execution_records` 添加 TTL 清理
3. 为 AI 服务添加重试包装器

**短期（2 周内）**：
4. 补齐 PRD 核心路径测试（提升至 60%+ 覆盖率）
5. 工作台工具箱补全所有工具入口
6. 技能链后端实现 + 前端状态轮询

**中期（1 个月内）**：
7. 拆分 Dashboard / Workspace 超大组件
8. 添加 E2E 覆盖核心用户旅程
9. 首页增加信任要素和示例 PRD
