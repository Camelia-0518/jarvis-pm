"use client";

import { useState, useRef, useEffect } from "react";
import { aiApi, prdApi } from "@/lib/api";
import { toast } from "sonner";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const QUICK_ACTIONS = [
  { label: "帮我写PRD", prompt: "我想写一个PRD，请帮我梳理需求结构" },
  { label: "分析需求", prompt: "请帮我分析这个需求的关键点和风险" },
  { label: "合规检查", prompt: "请检查以下内容的医疗合规性" },
  { label: "生成评审Q&A", prompt: "请为以下PRD生成评审预设Q&A" },
];

export function AIChatFAB() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "你好！我是 Jarvis PM 助手。你可以问我关于产品需求、PRD撰写、竞品分析的问题，或使用下方快捷操作。",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await aiApi.chat(userMsg.content, {
        page: typeof window !== "undefined" ? window.location.pathname : "",
      });
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.response || "抱歉，我暂时无法处理这个请求。",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "请求失败，请稍后重试";
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `❌ ${errorMsg}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  const handleQuickAction = (prompt: string) => {
    handleSend(prompt);
  };

  const getCurrentPrdId = (): string | null => {
    if (typeof window === "undefined") return null;
    const match = window.location.pathname.match(/^\/prd\/([^/]+)/);
    return match ? match[1] : null;
  };

  const handleArchiveToPRD = async (msgContent: string) => {
    const prdId = getCurrentPrdId();
    if (!prdId) {
      toast.info("请在 PRD 编辑器页面使用此功能");
      return;
    }
    try {
      const prd = await prdApi.get(prdId);
      const newMarkdown = (prd.markdown || "") + "\n\n---\n\n> 🤖 **AI 助手对话归档**\n\n" + msgContent + "\n";
      await prdApi.update(prdId, { markdown: newMarkdown });
      toast.success("已追加到当前 PRD");
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "归档失败";
      toast.error("归档失败：" + errorMsg);
    }
  };

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-sky-500 text-white shadow-lg transition-transform hover:scale-110 hover:bg-sky-600 active:scale-95"
          title="AI 助手"
        >
          <span className="text-2xl">🤖</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 flex h-[500px] w-[380px] flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span className="text-lg">🤖</span>
              <div>
                <div className="text-sm font-semibold text-slate-900 dark:text-white">
                  Jarvis 助手
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">
                  {isLoading ? "思考中..." : "在线"}
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
              title="关闭"
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3">
            <div className="space-y-3">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
                      msg.role === "user"
                        ? "bg-sky-500 text-white"
                        : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    <div
                      className={`mt-1 text-[10px] ${
                        msg.role === "user"
                          ? "text-sky-100"
                          : "text-slate-400 dark:text-slate-500"
                      }`}
                    >
                      {msg.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      {msg.role === "assistant" && msg.id !== "welcome" && (
                        <button
                          onClick={() => handleArchiveToPRD(msg.content)}
                          className="ml-2 text-sky-500 hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300"
                          title="追加到 PRD"
                        >
                          📎 归档
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-slate-100 px-3.5 py-2.5 dark:bg-slate-800">
                    <div className="flex items-center gap-1.5">
                      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400" />
                      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:0.2s]" />
                      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:0.4s]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Quick Actions */}
          {messages.length <= 1 && (
            <div className="border-t border-slate-100 px-4 py-2 dark:border-slate-800">
              <div className="mb-1.5 text-[10px] font-medium text-slate-400 dark:text-slate-500">
                快捷操作
              </div>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleQuickAction(action.prompt)}
                    disabled={isLoading}
                    className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 transition-colors hover:border-sky-300 hover:text-sky-600 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:border-sky-700 dark:hover:text-sky-400"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="border-t border-slate-100 px-4 py-3 dark:border-slate-800">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={isLoading}
                className="max-h-24 flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-400 focus:outline-none disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                placeholder="输入问题，Shift+Enter 换行..."
              />
              <button
                onClick={() => handleSend(input)}
                disabled={isLoading || !input.trim()}
                className="mb-0.5 rounded-xl bg-sky-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                发送
              </button>
            </div>
            <div className="mt-1 text-center text-[10px] text-slate-400 dark:text-slate-500">
              Enter 发送 · Shift+Enter 换行
            </div>
          </div>
        </div>
      )}
    </>
  );
}
