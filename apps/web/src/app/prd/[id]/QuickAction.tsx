"use client";

interface Props {
  label: string;
  onClick?: () => void;
}

export default function QuickAction({ label, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-md px-2.5 py-1.5 text-left text-sm text-slate-600 transition-colors duration-150 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
    >
      {label}
    </button>
  );
}
