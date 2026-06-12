"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useWorkspaceStore } from "@/stores/workspaceStore";

export default function WorkspaceSwitcher() {
  const {
    workspaces,
    activeWorkspaceId,
    fetchWorkspaces,
    setActiveWorkspace,
    isLoading,
  } = useWorkspaceStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchWorkspaces();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const active = workspaces.find(
    (w) => w.workspace_id === activeWorkspaceId
  );

  if (workspaces.length === 0) {
    return (
      <Link
        href="/settings/workspace"
        className="rounded-lg border border-dashed border-gray-300 px-3 py-1.5 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600 dark:border-gray-600 dark:text-gray-400"
      >
        + 创建工作区
      </Link>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        disabled={isLoading}
        className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-750"
      >
        <span className="max-w-[120px] truncate">
          {active?.name || "选择工作区"}
        </span>
        <span className="text-[10px] text-gray-400">{active?.role}</span>
        <svg
          className={`h-3 w-3 text-gray-400 transition ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800">
          <div className="px-3 py-2 text-[10px] font-semibold uppercase text-gray-400">
            工作区
          </div>
          {workspaces.map((w) => (
            <button
              key={w.workspace_id}
              onClick={() => {
                setActiveWorkspace(w.workspace_id, w.role);
                setOpen(false);
              }}
              className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
                w.workspace_id === activeWorkspaceId
                  ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                  : "text-gray-700 dark:text-gray-300"
              }`}
            >
              <span className="truncate">{w.name}</span>
              <span className="ml-2 shrink-0 text-[10px] text-gray-400">
                {w.role}
              </span>
            </button>
          ))}
          <div className="border-t border-gray-100 dark:border-gray-700">
            <Link
              href="/settings/workspace"
              onClick={() => setOpen(false)}
              className="block px-3 py-2 text-sm text-gray-500 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-700"
            >
              管理工作区 →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
