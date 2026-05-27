"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);
  return isMobile;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  isStreaming?: boolean;
}

export default function MarkdownEditor({ value, onChange, placeholder, isStreaming }: Props) {
  const isMobile = useIsMobile();
  const [mode, setMode] = useState<"edit" | "preview" | "split">("edit");
  const [showOutline, setShowOutline] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-switch to preview on mobile; disable split
  useEffect(() => {
    if (isMobile && mode === "split") {
      setMode("preview");
    }
  }, [isMobile, mode]);

  // Default to preview on mobile after mount
  useEffect(() => {
    if (isMobile) {
      setMode("preview");
    }
  }, [isMobile]);

  const outline = useMemo(() => {
    const lines = value.split("\n");
    const headings: { level: number; text: string; lineIndex: number }[] = [];
    lines.forEach((line, idx) => {
      const match = line.match(/^(#{1,4})\s+(.+)$/);
      if (match) {
        headings.push({ level: match[1].length, text: match[2].trim(), lineIndex: idx });
      }
    });
    return headings;
  }, [value]);

  const scrollToLine = (lineIndex: number) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const lines = value.split("\n");
    let charPos = 0;
    for (let i = 0; i < lineIndex; i++) {
      charPos += lines[i].length + 1;
    }
    ta.selectionStart = charPos;
    ta.selectionEnd = charPos;
    ta.focus();
    ta.scrollTop = lineIndex * 20;
  };

  const modeButton = (m: "edit" | "preview" | "split", label: string) => (
    <button
      key={m}
      onClick={() => setMode(m)}
      className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
        mode === m
          ? "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200"
          : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2 dark:border-slate-800">
        <div className="flex gap-1">
          {modeButton("edit", "编辑")}
          {modeButton("preview", "预览")}
          {!isMobile && modeButton("split", "分屏")}
          <div className="mx-1 h-4 w-px self-center bg-slate-200 dark:bg-slate-700" />
          <button
            onClick={() => setShowOutline(!showOutline)}
            className={`hidden rounded-md px-2.5 py-1 text-xs font-medium transition-colors md:block ${
              showOutline
                ? "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
            }`}
            title="大纲导航"
          >
            大纲
          </button>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
            <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
            AI 生成中...
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Outline Panel */}
        {showOutline && outline.length > 0 && (
          <div className="w-56 overflow-y-auto border-r border-slate-100 bg-slate-50/80 px-3 py-4 dark:border-slate-800 dark:bg-slate-900/50">
            <div className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              文档大纲
            </div>
            <div className="space-y-0.5">
              {outline.map((heading, idx) => (
                <button
                  key={idx}
                  onClick={() => scrollToLine(heading.lineIndex)}
                  className={`block w-full truncate rounded px-1.5 py-1 text-left text-xs transition-colors hover:bg-slate-200 dark:hover:bg-slate-700 ${
                    heading.level === 1
                      ? "font-medium text-slate-800 dark:text-slate-200"
                      : heading.level === 2
                        ? "pl-3 text-slate-700 dark:text-slate-300"
                        : heading.level === 3
                          ? "pl-5 text-slate-600 dark:text-slate-400"
                          : "pl-7 text-slate-500 dark:text-slate-500"
                  }`}
                  title={heading.text}
                >
                  {heading.text}
                </button>
              ))}
            </div>
          </div>
        )}
        {(mode === "edit" || mode === "split") && (
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={`h-full resize-none overflow-y-auto bg-transparent px-4 py-4 font-mono text-sm leading-relaxed text-slate-800 placeholder:text-slate-400 focus:outline-none md:px-6 md:py-6 dark:text-slate-200 ${
              mode === "split" ? "w-1/2 border-r border-slate-100 dark:border-slate-800" : "w-full md:px-12 md:py-8"
            }`}
            placeholder={placeholder}
          />
        )}
        {(mode === "preview" || mode === "split") && (
          <div
            className={`h-full overflow-y-auto bg-white px-4 py-4 dark:bg-slate-950 md:px-6 md:py-6 ${
              mode === "split" ? "w-1/2" : "w-full md:px-12 md:py-8"
            }`}
          >
            <div className="prose prose-sm max-w-none dark:prose-invert md:prose-base">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{value || "*暂无内容*"}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
