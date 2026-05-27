"use client";

import Link from "next/link";
import { useState } from "react";
import { confirm } from "@/components/ui/ConfirmDialog";

interface Version {
  id: string;
  version_number: number;
  title: string;
  created_at: string;
}

interface Props {
  prdId: string;
  versions: Version[];
  onRestore: (versionId: string, versionNumber: number) => void;
  onOpen?: () => void;
}

export default function VersionPanel({ prdId, versions, onRestore, onOpen }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = () => {
    const next = !isOpen;
    setIsOpen(next);
    if (next && onOpen) onOpen();
  };

  const handleRestore = async (versionId: string, versionNumber: number) => {
    const confirmed = await confirm({
      title: "恢复版本",
      message: `确定要恢复到版本 ${versionNumber} 吗？当前内容将被备份。`,
      type: "warning",
    });
    if (confirmed) {
      onRestore(versionId, versionNumber);
    }
  };

  return (
    <div className="mt-6">
      <button
        onClick={handleToggle}
        className="mb-1 flex w-full items-center justify-between px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <span>版本历史</span>
        <span>{isOpen ? "▾" : "▸"}</span>
      </button>
      {isOpen && (
        <div className="space-y-1">
          {versions.length === 0 ? (
            <div className="px-2.5 py-2 text-xs text-slate-400">暂无历史版本</div>
          ) : (
            versions.map((v) => (
              <div
                key={v.id}
                className="flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <div className="truncate">
                  <span className="font-medium text-slate-700 dark:text-slate-300">v{v.version_number}</span>
                  <span className="ml-1 text-slate-400">
                    {new Date(v.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-0.5">
                  <Link
                    href={`/prd/${prdId}/diff?versionId=${v.id}&versionNum=${v.version_number}`}
                    className="rounded px-1.5 py-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:text-slate-500 dark:hover:bg-slate-700 dark:hover:text-slate-300"
                    title="对比此版本"
                  >
                    ↔
                  </Link>
                  <button
                    onClick={() => handleRestore(v.id, v.version_number)}
                    className="rounded px-1.5 py-0.5 text-slate-500 hover:bg-slate-200 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
                    title="恢复此版本"
                  >
                    ↩
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
