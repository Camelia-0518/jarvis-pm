"use client";

import { useState, useCallback } from "react";

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: "danger" | "warning" | "info";
}

let globalConfirm: ((opts: ConfirmOptions) => Promise<boolean>) | null = null;

export function setGlobalConfirm(fn: (opts: ConfirmOptions) => Promise<boolean>) {
  globalConfirm = fn;
}

export async function confirm(opts: ConfirmOptions): Promise<boolean> {
  if (!globalConfirm) {
    // Fallback to native confirm if not initialized
    return window.confirm(opts.message);
  }
  return globalConfirm(opts);
}

export default function ConfirmDialogProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [resolveRef, setResolveRef] = useState<((value: boolean) => void) | null>(null);

  const openConfirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions(opts);
      setResolveRef(() => resolve);
      setIsOpen(true);
    });
  }, []);

  setGlobalConfirm(openConfirm);

  const handleConfirm = () => {
    setIsOpen(false);
    resolveRef?.(true);
    setResolveRef(null);
  };

  const handleCancel = () => {
    setIsOpen(false);
    resolveRef?.(false);
    setResolveRef(null);
  };

  const btnColors =
    options?.type === "danger"
      ? "bg-rose-600 hover:bg-rose-700"
      : options?.type === "warning"
      ? "bg-amber-600 hover:bg-amber-700"
      : "bg-sky-600 hover:bg-sky-700";

  return (
    <>
      {children}
      {isOpen && options && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm">
            {options.title && (
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                {options.title}
              </h3>
            )}
            <p className="text-sm text-slate-600 dark:text-slate-300 mb-6">
              {options.message}
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleCancel}
                className="flex-1 px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                {options.cancelText || "取消"}
              </button>
              <button
                onClick={handleConfirm}
                className={`flex-1 px-4 py-2 rounded-lg text-white ${btnColors}`}
              >
                {options.confirmText || "确定"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
