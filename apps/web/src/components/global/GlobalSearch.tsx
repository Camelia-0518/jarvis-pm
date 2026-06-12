"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { projectApi, prdApi, skillsApi } from "@/lib/api";

interface SearchResult {
  id: string;
  type: "project" | "prd" | "skill";
  title: string;
  subtitle?: string;
  href: string;
}

export function GlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Load all searchable data on open
  const [allData, setAllData] = useState<SearchResult[]>([]);

  const loadAllData = useCallback(async () => {
    try {
      const [projects, prds, skills] = await Promise.all([
        projectApi.list().then((res) => res.items || []).catch(() => [] as { id: string; name: string; description?: string }[]),
        prdApi.list().catch(() => ({ items: [] as { id: string; title: string; status?: string }[] })),
        skillsApi.getAll().catch(() => ({ skills: [] as { id: string; name: string; description?: string; category?: string }[] })),
      ]);

      const items: SearchResult[] = [
        ...projects.map((p) => ({
          id: `project-${p.id}`,
          type: "project" as const,
          title: p.name,
          subtitle: p.description || "项目",
          href: `/workspace?id=${p.id}`,
        })),
        ...prds.items.map((p) => ({
          id: `prd-${p.id}`,
          type: "prd" as const,
          title: p.title,
          subtitle: p.status === "published" ? "已发布" : "草稿",
          href: `/prd/${p.id}`,
        })),
        ...skills.skills.map((s) => ({
          id: `skill-${s.id}`,
          type: "skill" as const,
          title: s.name,
          subtitle: s.category || "技能",
          href: `/skills?skill=${s.id}`,
        })),
      ];
      setAllData(items);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadAllData();
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen, loadAllData]);

  // Filter results by query
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSelectedIndex(0);
      return;
    }
    setIsLoading(true);
    const q = query.toLowerCase();
    const filtered = allData.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        (item.subtitle?.toLowerCase().includes(q) ?? false)
    );
    setResults(filtered.slice(0, 20));
    setSelectedIndex(0);
    setIsLoading(false);
  }, [query, allData]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSelect = (result: SearchResult) => {
    setIsOpen(false);
    setQuery("");
    router.push(result.href);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[selectedIndex]) {
        handleSelect(results[selectedIndex]);
      }
    }
  };

  const typeIcon = (type: string) => {
    switch (type) {
      case "project":
        return "📁";
      case "prd":
        return "📝";
      case "skill":
        return "⚡";
      default:
        return "📄";
    }
  };

  const typeLabel = (type: string) => {
    switch (type) {
      case "project":
        return "项目";
      case "prd":
        return "PRD";
      case "skill":
        return "技能";
      default:
        return "";
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center bg-black/40 pt-[15vh] backdrop-blur-sm"
      onClick={() => setIsOpen(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
          <span className="text-slate-400">🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleInputKeyDown}
            className="flex-1 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400 dark:text-slate-200"
            placeholder="搜索项目、PRD、技能..."
          />
          <div className="flex items-center gap-1">
            <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              Esc
            </kbd>
            <kbd className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
              ↓↑
            </kbd>
          </div>
        </div>

        {/* Results */}
        <div className="max-h-[320px] overflow-y-auto py-2">
          {query.trim() && results.length === 0 && !isLoading && (
            <div className="px-4 py-8 text-center text-sm text-slate-400 dark:text-slate-500">
              未找到与 &ldquo;{query}&rdquo; 相关的结果
            </div>
          )}

          {results.map((result, index) => (
            <button
              key={result.id}
              onClick={() => handleSelect(result)}
              onMouseEnter={() => setSelectedIndex(index)}
              className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                index === selectedIndex
                  ? "bg-sky-50 dark:bg-sky-900/20"
                  : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
              }`}
            >
              <span className="text-lg">{typeIcon(result.type)}</span>
              <div className="flex-1 min-w-0">
                <div className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
                  {result.title}
                </div>
                {result.subtitle && (
                  <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {result.subtitle}
                  </div>
                )}
              </div>
              <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                {typeLabel(result.type)}
              </span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-[10px] text-slate-400 dark:border-slate-800 dark:text-slate-500">
          <div className="flex items-center gap-3">
            <span>
              {results.length}
              个结果
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 font-medium dark:border-slate-700 dark:bg-slate-800">↵</kbd>
              打开
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-slate-200 bg-slate-50 px-1 py-0.5 font-medium dark:border-slate-700 dark:bg-slate-800">⌘K</kbd>
              唤起
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
