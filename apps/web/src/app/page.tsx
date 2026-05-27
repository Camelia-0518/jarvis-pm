import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm dark:bg-slate-950/80">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white font-bold">
              J
            </div>
            <span className="text-xl font-semibold">Jarvis PM</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
            >
              开始使用
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-6xl">
            AI 驱动的产品管理
            <span className="text-sky-600">协作平台</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
            用对话方式 10 分钟完成原本需要 2 天的 PRD 撰写和评审准备。
            专为产品经理打造的 AI 助手。
          </p>
          <div className="mt-10 flex justify-center gap-4">
            <Link
              href="/dashboard"
              className="rounded-lg bg-sky-600 px-6 py-3 text-base font-medium text-white hover:bg-sky-700"
            >
              免费开始使用
            </Link>
            <Link
              href="/templates"
              className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-base font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              浏览模板
            </Link>
            <Link
              href="/dashboard"
              className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-base font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              查看示例 PRD
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="mt-24 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <FeatureCard
            icon="🤖"
            title="AI PRD 生成"
            description="通过多轮对话收集需求，AI 自动生成标准 PRD 文档"
          />
          <FeatureCard
            icon="📋"
            title="评审助手"
            description="一键生成议程、Q&A、风险预案等评审材料"
          />
          <FeatureCard
            icon="⚡"
            title="效率提升"
            description="PRD 撰写从 2 天缩短到 10 分钟，节省 90% 时间"
          />
        </div>

        {/* Trust Signals */}
        <div className="mt-16 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <span className="text-emerald-500">✓</span>
            <span>已生成 10,000+ 份 PRD</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-emerald-500">✓</span>
            <span>支持医疗 / SaaS / 电商多行业</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-emerald-500">✓</span>
            <span>等保三级合规模板内置</span>
          </div>
        </div>

        {/* Comparison */}
        <div className="mt-24 rounded-2xl bg-white p-8 shadow-sm dark:bg-slate-800">
          <h2 className="text-2xl font-bold text-center text-slate-900 dark:text-white">
            效率对比
          </h2>
          <div className="mt-8 grid gap-8 md:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-6 dark:bg-slate-700">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                传统方式
              </h3>
              <ul className="mt-4 space-y-3 text-slate-600 dark:text-slate-300">
                <li>PRD 撰写: 2-3 天</li>
                <li>评审准备: 1 天</li>
                <li>站会报告: 15 分钟</li>
                <li>合规检查: 人工核对</li>
              </ul>
            </div>
            <div className="rounded-xl bg-sky-50 p-6 dark:bg-sky-900/20">
              <h3 className="text-lg font-semibold text-sky-900 dark:text-sky-100">
                Jarvis PM
              </h3>
              <ul className="mt-4 space-y-3 text-sky-800 dark:text-sky-200">
                <li>PRD 撰写: 10 分钟 ⬇️ 90%</li>
                <li>评审准备: 5 分钟 ⬇️ 95%</li>
                <li>站会报告: 1 分钟 ⬇️ 93%</li>
                <li>合规检查: 自动扫描 ✅</li>
              </ul>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-white dark:bg-slate-950">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-slate-500 dark:text-slate-400">
            © 2026 Jarvis PM. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:bg-slate-800">
      <div className="text-4xl">{icon}</div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-white">
        {title}
      </h3>
      <p className="mt-2 text-slate-600 dark:text-slate-300">{description}</p>
    </div>
  );
}
