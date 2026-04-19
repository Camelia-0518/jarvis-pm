# Jarvis PM 项目整合记录

## 整合时间
2026-04-10

## 整合来源
- `ai-pm-assistant` (Next.js 13) - 提取精华组件
- `ai-pm-assistant-vue` (Vue 3) - 空壳项目，直接删除

## 整合到主干项目
- `jarvis-pm` (Next.js 14 + FastAPI)

---

## 迁移的组件

### 新增组件目录
```
apps/web/src/components/
├── chat/
│   └── ChatInterface.tsx          # AI对话界面
├── agent/
│   ├── AgentProgressBar.tsx       # Agent执行进度
│   └── AgentReasoningLog.tsx      # Agent思考过程日志
├── collaboration/
│   └── CollaborationPanel.tsx     # 实时协作面板
├── review/
│   └── ReviewWorkflow.tsx         # 评审工作流
├── version/
│   ├── BranchComparison.tsx       # 分支对比
│   └── BranchMerge.tsx            # 分支合并
├── knowledge/
│   └── KnowledgeBase.tsx          # 知识库组件
└── ExportPanel.tsx                # 导出功能面板
```

### 迁移的 Stores
```
apps/web/src/stores/
├── branchStore.ts                 # 分支管理状态
├── chatStore.ts                   # 聊天状态
├── reviewWorkflowStore.ts         # 评审工作流状态
└── versionStore.ts                # 版本控制状态
```

### 迁移的 Types
```
apps/web/src/types/
└── version.ts                     # 版本控制类型定义
```

### 迁移的文档
```
docs-from-ai-pm-assistant/         # 17个设计文档
```

### 迁移的 UI 组件
```
apps/web/src/components/ui-from-ai-pm/  # shadcn/ui 组件
```

---

## 更新的依赖

### package.json 新增依赖
- @radix-ui/react-* (Dialog, ScrollArea, Select, Separator, Slot, Tabs)
- @tailwindcss/typography
- class-variance-authority
- clsx
- diff
- file-saver
- lucide-react
- react-markdown
- remark-gfm
- tailwind-merge
- tailwindcss-animate

### devDependencies 新增
- @types/diff
- @types/file-saver

---

## 整合说明

### 保留的精华（从 ai-pm-assistant）
1. **协作功能** - CollaborationPanel, CollaborativeCursor
2. **版本控制** - BranchComparison, BranchMerge, VersionControl
3. **评审工作流** - ReviewWorkflow
4. **AI对话界面** - ChatInterface
5. **知识库** - KnowledgeBase
6. **导出功能** - ExportPanel
7. **Agent日志** - AgentReasoningLog, AgentProgressBar

### 保留的精华（原有 jarvis-pm）
1. **PRD框架** - prdFramework.ts (医疗信息化8章结构)
2. **AI话术** - aiPrompts.ts (方法论感表达)
3. **技术栈** - Next.js 14 + Tailwind 4
4. **后端服务** - FastAPI + Kimi/Claude/OpenAI 多Provider支持
5. **医疗组件** - MedicalComplianceChecker, PM工具包

### 舍弃的内容
1. ai-pm-assistant 的 .next/ 构建输出
2. ai-pm-assistant 的 node_modules/
3. ai-pm-assistant-vue 全部内容（空壳项目）
4. 重复的 UI 组件（与 shadcn/ui 冲突的）

---

## 后续步骤

1. [ ] 运行 `npm install` 安装新依赖
2. [ ] 修复组件中的导入路径
3. [ ] 统一 UI 组件库（shadcn/ui）
4. [ ] 测试关键功能
5. [ ] 删除备份文件夹

---

*整合完成时间: 2026-04-10*
*版本: jarvis-pm v2.1*
