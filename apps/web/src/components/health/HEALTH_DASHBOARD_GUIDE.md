# jarvis-pm 健康度仪表盘 — 安装验证指南

## 一、已创建的文件清单

```
apps/web/src/
├── components/health/
│   ├── HealthGauge.tsx      # Gauge 仪表盘（交付/风险健康度）
│   ├── RiskHeatmap.tsx      # 5×5 概率×影响风险热力图
│   ├── TaskBarChart.tsx     # 阶段任务进度并列柱状图
│   └── index.ts             # 组件统一导出
├── app/
│   └── health/
│       └── page.tsx         # 健康度仪表盘主页面
└── components/global/
    └── NavHeader.tsx        # ← 已添加"健康度"导航入口
```

## 二、安装依赖（必须做）

在项目根目录下打开终端（PowerShell / Git Bash）：

```bash
cd apps/web
npm install echarts@5.5.0
```

> 不需要 `echarts-for-react`，三个组件都使用原生 `echarts.init()` + `useRef` + `useEffect` 初始化，更轻量，面试也能讲清楚生命周期管理。

## 三、启动验证

```bash
cd apps/web
npm run dev
```

浏览器打开 `http://localhost:3000/health`，你应该看到：

1. **顶部导航栏**有"健康度"入口
2. **四张统计卡片**（交付计划、任务完成率、高风险项、逾期阶段）
3. **两个 Gauge 仪表盘**（交付健康度 + 风险健康度，0-100 分，带绿/黄/红分段）
4. **5×5 风险热力图**（概率 × 影响矩阵，颜色从绿到红）
5. **阶段任务柱状图**（8 个 HIS 标准阶段，总任务/已完成/进行中三组对比）

## 四、面试时的讲解要点（重点）

### 1. 为什么做这个页面？

> "交付中心已经有数据了，但 PM 和项目总监需要一张一眼看懂全局健康状况的仪表盘。我用 ECharts 做了三个维度的可视化：评分（Gauge）、风险密度（Heatmap）、阶段瓶颈（Bar Chart）。"

### 2. HealthGauge（技术细节）

- **分段颜色**：0-60 绿、60-80 黄、80-100 红，对应 `axisLine.lineStyle.color` 的分段数组
- **指针动画**：`valueAnimation: true` 实现分数从 0 滚动到目标值
- **内存安全**：`useEffect` 返回清理函数中调 `chart.dispose()`，防止路由切换后内存泄漏
- **Dark Mode**：用 `MutationObserver` 监听 `document.documentElement.classList` 变化，自动切换 ECharts 主题

### 3. RiskHeatmap（业务逻辑）

- 数据来自后端 risk API，按 `probability × impact` 二维聚合
- 为什么不用散点图？——**热力图能展示密度聚类**，一格里的风险项数量越多颜色越红，PM 一眼就知道哪里最危险
- `visualMap` 自动映射颜色，从绿到红，不需要手动写每个格子的颜色

### 4. TaskBarChart（设计思路）

- 为什么用**并列柱状图**而不是堆叠？——对比总任务数和完成数，一眼看出哪些阶段"拖后腿"
- `markLine` 标注了平均完成率，方便横向对比各阶段是否低于平均线
- 数据从 WBS 按 `phase_id` 聚合，前端只做展示，不做业务计算
- Tooltip 自定义了 formatter，加入了医疗项目专属阶段名（如"互联互通测评"）

### 5. 整体架构（展示你对全栈的理解）

```
后端 FastAPI                  前端 Next.js
    │                             │
    ▼                             ▼
deliveryApi.getDashboard()  →  health/page.tsx
    (返回 JSON)                  (useState + useEffect 获取)
                                     │
                                     ▼
                              ┌──────────────┐
                              │ 数据二次聚合 │  ← 你面试可以讲这里
                              │ (mock → 真实API) │
                              └──────────────┘
                                     │
              ┌──────────┬──────────┴──────────┐
              ▼          ▼                     ▼
         HealthGauge   RiskHeatmap        TaskBarChart
         (score)       (risk matrix)      (phase progress)
```

### 6. 如果面试官问"真实数据怎么来的"

> "当前热力图和柱状图用的是 mock 数据，但接口和数据结构已经定义好了。后端 risk API 和 WBS API 返回的是原始 risk 项和 task 列表，前端按 `probability × impact` 和 `phase_id` 做聚合。后续只需要把 `MOCK_RISK_DATA` 和 `MOCK_PHASE_DATA` 替换为真实 API 调用即可。"

## 五、简历关键词（按方案一写）

在 jarvis-pm 项目描述中加入：

```
- 独立开发项目健康度仪表盘（ECharts Gauge + Heatmap + Bar Chart），
  支持 dark mode 自适应、响应式布局、内存安全销毁
- 后端 API 数据 → 前端二次聚合（风险 5×5 矩阵、WBS 阶段统计）
- 医疗 IT 专属：HIS 标准阶段（互联互通测评、医保对接）可视化呈现
```

## 六、文件修改摘要

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web/src/components/health/HealthGauge.tsx` | 新建 | Gauge 图表组件 |
| `apps/web/src/components/health/RiskHeatmap.tsx` | 新建 | 热力图组件 |
| `apps/web/src/components/health/TaskBarChart.tsx` | 新建 | 柱状图组件 |
| `apps/web/src/components/health/index.ts` | 新建 | 统一导出 |
| `apps/web/src/app/health/page.tsx` | 新建 | 仪表盘主页面 |
| `apps/web/src/components/global/NavHeader.tsx` | 修改 | 添加"健康度"导航 |

全部代码已就位，你只需要本地跑 `npm install echarts@5.5.0` + `npm run dev` 就能看效果。
