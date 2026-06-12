"use client";

import { useState } from "react";

// 技术词汇库
interface TechTerm {
  term: string;
  type: "frontend" | "backend" | "database" | "api" | "general";
  severity: "error" | "warning";
  suggestion: string;
  explanation: string;
}

const TECH_TERMS: TechTerm[] = [
  // 前端技术
  {
    term: "Vue",
    type: "frontend",
    severity: "error",
    suggestion: "用户界面",
    explanation: "PRD中不应出现具体前端框架名称",
  },
  {
    term: "React",
    type: "frontend",
    severity: "error",
    suggestion: "用户界面",
    explanation: "PRD中不应出现具体前端框架名称",
  },
  {
    term: "组件",
    type: "frontend",
    severity: "warning",
    suggestion: "功能模块",
    explanation: "技术术语建议改为业务语言",
  },
  {
    term: "页面",
    type: "frontend",
    severity: "warning",
    suggestion: "界面/视图",
    explanation: "建议使用更中性的表达",
  },

  // 后端技术
  {
    term: "API",
    type: "api",
    severity: "error",
    suggestion: "数据接口/服务",
    explanation: "PRD中应使用业务语言描述数据交互",
  },
  {
    term: "接口",
    type: "api",
    severity: "warning",
    suggestion: "数据交互",
    explanation: "建议使用更业务化的表达",
  },
  {
    term: "后端",
    type: "backend",
    severity: "warning",
    suggestion: "服务端/系统后台",
    explanation: "建议使用更正式的称谓",
  },
  {
    term: "服务器",
    type: "backend",
    severity: "warning",
    suggestion: "服务端",
    explanation: "建议统一用词",
  },

  // 数据库
  {
    term: "数据库表",
    type: "database",
    severity: "error",
    suggestion: "数据实体",
    explanation: "PRD中应使用数据实体而非技术表名",
  },
  {
    term: "字段",
    type: "database",
    severity: "warning",
    suggestion: "属性/信息项",
    explanation: "建议使用业务语言",
  },
  {
    term: "SQL",
    type: "database",
    severity: "error",
    suggestion: "数据查询",
    explanation: "PRD中不应出现具体技术实现",
  },
  {
    term: "主键",
    type: "database",
    severity: "error",
    suggestion: "唯一标识",
    explanation: "使用业务语言描述",
  },
  {
    term: "外键",
    type: "database",
    severity: "error",
    suggestion: "关联关系",
    explanation: "描述业务关联而非技术实现",
  },

  // 通用技术
  {
    term: "缓存",
    type: "general",
    severity: "warning",
    suggestion: "数据暂存",
    explanation: "技术术语建议业务化",
  },
  {
    term: "异步",
    type: "general",
    severity: "warning",
    suggestion: "后台处理",
    explanation: "使用用户可理解的表达",
  },
  {
    term: "同步",
    type: "general",
    severity: "warning",
    suggestion: "实时处理",
    explanation: "使用用户可理解的表达",
  },
  {
    term: "JSON",
    type: "general",
    severity: "error",
    suggestion: "数据格式",
    explanation: "PRD中不应涉及具体数据格式",
  },
  {
    term: "HTTP",
    type: "general",
    severity: "error",
    suggestion: "网络请求",
    explanation: "技术细节不应出现在PRD中",
  },
  {
    term: "回调",
    type: "general",
    severity: "error",
    suggestion: "响应通知",
    explanation: "使用业务语言",
  },
  {
    term: "轮询",
    type: "general",
    severity: "error",
    suggestion: "定时查询",
    explanation: "使用业务语言",
  },
];

// 产品思维检查项
interface ProductThinkingCheck {
  id: string;
  category: string;
  item: string;
  checked: boolean;
}

const PRODUCT_THINKING_CHECKS: ProductThinkingCheck[] = [
  {
    id: "pt-1",
    category: "用户视角",
    item: "PRD中是否描述了'用户能获得什么价值'而非'系统能做什么'",
    checked: false,
  },
  {
    id: "pt-2",
    category: "用户视角",
    item: "用户故事是否使用了'作为[角色]，我希望[功能]，以便[价值]'格式",
    checked: false,
  },
  {
    id: "pt-3",
    category: "业务语言",
    item: "是否避免了技术实现细节（框架、数据库、API等）",
    checked: false,
  },
  {
    id: "pt-4",
    category: "业务语言",
    item: "功能描述是否使用了业务人员能理解的术语",
    checked: false,
  },
  {
    id: "pt-5",
    category: "完整度",
    item: "是否定义了明确的验收标准（可测试、可验证）",
    checked: false,
  },
  {
    id: "pt-6",
    category: "完整度",
    item: "成功指标是否可量化、可追踪",
    checked: false,
  },
  {
    id: "pt-7",
    category: "风险意识",
    item: "是否考虑了异常情况和错误处理",
    checked: false,
  },
  {
    id: "pt-8",
    category: "风险意识",
    item: "医疗合规和数据隐私是否得到充分考虑",
    checked: false,
  },
];

export default function TechLanguageDetector() {
  const [inputText, setInputText] = useState("");
  const [issues, setIssues] = useState<Array<{ term: TechTerm; index: number }>>([]);
  const [checks, setChecks] = useState(PRODUCT_THINKING_CHECKS);

  const detectTechTerms = (text: string) => {
    const found: Array<{ term: TechTerm; index: number }> = [];

    TECH_TERMS.forEach((tech) => {
      const regex = new RegExp(tech.term, "gi");
      let match;
      while ((match = regex.exec(text)) !== null) {
        found.push({ term: tech, index: match.index });
      }
    });

    return found.sort((a, b) => a.index - b.index);
  };

  const handleTextChange = (text: string) => {
    setInputText(text);
    setIssues(detectTechTerms(text));
  };

  const toggleCheck = (id: string) => {
    setChecks(checks.map((c) => (c.id === id ? { ...c, checked: !c.checked } : c)));
  };

  const checkedCount = checks.filter((c) => c.checked).length;
  const errorCount = issues.filter((i) => i.term.severity === "error").length;
  const warningCount = issues.filter((i) => i.term.severity === "warning").length;

  return (
    <div className="space-y-6">
      {/* 统计 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-rose-50 p-3 text-center dark:bg-rose-900/20">
          <div className="text-2xl font-bold text-rose-600">{errorCount}</div>
          <div className="text-xs text-rose-700">错误（必须修改）</div>
        </div>
        <div className="rounded-lg bg-amber-50 p-3 text-center dark:bg-amber-900/20">
          <div className="text-2xl font-bold text-amber-600">{warningCount}</div>
          <div className="text-xs text-amber-700">警告（建议优化）</div>
        </div>
        <div className="rounded-lg bg-emerald-50 p-3 text-center dark:bg-emerald-900/20">
          <div className="text-2xl font-bold text-emerald-600">{checkedCount}/{checks.length}</div>
          <div className="text-xs text-emerald-700">产品思维检查</div>
        </div>
      </div>

      {/* 文本检测区 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-3 font-semibold text-slate-900 dark:text-white">📝 技术语言检测</h3>

        <textarea
          value={inputText}
          onChange={(e) => handleTextChange(e.target.value)}
          placeholder="粘贴PRD内容到这里，自动检测技术语言..."
          className="h-32 w-full rounded-lg border border-slate-300 p-3 text-sm dark:border-slate-600 dark:bg-slate-700"
        />

        {/* 检测结果 */}
        {issues.length > 0 && (
          <div className="mt-3 space-y-2">
            {issues.map((issue, idx) => (
              <div
                key={idx}
                className={`rounded-lg p-2 text-sm ${
                  issue.term.severity === "error"
                    ? "bg-rose-50 text-rose-800 dark:bg-rose-900/20"
                    : "bg-amber-50 text-amber-800 dark:bg-amber-900/20"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">检测到: &ldquo;{issue.term.term}&rdquo;</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs ${
                      issue.term.severity === "error"
                        ? "bg-rose-200 text-rose-800"
                        : "bg-amber-200 text-amber-800"
                    }`}
                  >
                    {issue.term.severity === "error" ? "错误" : "警告"}
                  </span>
                </div>
                <div className="mt-1">
                  💡 建议改为:
                  <span className="font-medium">&ldquo;{issue.term.suggestion}&rdquo;</span>
                </div>
                <div className="mt-0.5 text-xs opacity-80">{issue.term.explanation}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 技术词汇表 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h3 className="mb-3 font-semibold text-slate-900 dark:text-white">📚 技术词汇转换表</h3>

        <div className="grid grid-cols-2 gap-2 text-sm">
          {TECH_TERMS.slice(0, 8).map((term) => (
            <div
              key={term.term}
              className="flex items-center justify-between rounded bg-slate-50 p-2 dark:bg-slate-700/50"
            >
              <span className="text-slate-600 line-through">{term.term}</span>
              <span className="text-emerald-600">→ {term.suggestion}</span>
            </div>
          ))}
        </div>

        <button className="mt-3 text-xs text-sky-600 hover:text-sky-700">
          查看全部 {TECH_TERMS.length} 个词汇
        </button>
      </div>

      {/* 产品思维检查清单 */}
      <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-900 dark:text-white">✅ 产品思维检查</h3>
          <span className="text-xs text-slate-500">
            {checkedCount}/{checks.length} 项
          </span>
        </div>

        <div className="space-y-3">
          {Array.from(new Set(checks.map((c) => c.category))).map((category) => (
            <div key={category}>
              <div className="mb-2 text-xs font-medium text-slate-500">{category}</div>
              <div className="space-y-1">
                {checks
                  .filter((c) => c.category === category)
                  .map((check) => (
                    <label
                      key={check.id}
                      className="flex cursor-pointer items-start gap-2 rounded p-1 hover:bg-slate-50 dark:hover:bg-slate-700/50"
                    >
                      <input
                        type="checkbox"
                        checked={check.checked}
                        onChange={() => toggleCheck(check.id)}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300"
                      />
                      <span className="text-sm text-slate-700 dark:text-slate-300">{check.item}</span>
                    </label>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
